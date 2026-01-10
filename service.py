"""Drone assignment service with priority-based queue and closest-drone assignment"""
from typing import Dict, List, Optional, Tuple
import heapq
import threading
import math
from datetime import datetime, timedelta
from models import Priority, Request, RequestStatus, Drone, Location
from graph import HospitalGraph
from energy import EnergyCalculator
from items import ItemCatalog
from patients import get_patient, get_all_patients, CurrentStatus
from rrt_pathfinding import RRTPathPlanner
class DroneAssignmentService:
    """manages drone requests, assignments, and routing"""
    def __init__(self, hospital_graph: HospitalGraph):
        self.graph = hospital_graph
        self.requests: Dict[int, Request] = {}
        self.drones: Dict[int, Drone] = {}
        self.priority_queue = []  # min-heap for priority queue
        self.next_request_id = 1
        self.next_drone_id = 1
        self.total_energy_saved_kwh = 0.0
        self.total_co2_saved_kg = 0.0
        self.lock = threading.Lock()
        # speed  by priority
        self.EMERGENCY_SPEED_M_PER_SEC = 4.0
        self.NORMAL_SPEED_M_PER_SEC = 2.5
        self.LOW_PRIORITY_SPEED_M_PER_SEC = 1.5
        # battery amounts
        self.MIN_BATTERY_THRESHOLD = 0.0243
        self.CHARGING_STATION_LOCATIONS = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
        self.CHARGE_RATE_KWH_PER_SEC = 0.01
        self.active_flights: Dict[int, dict] = {}
        # RRT path planner for collision avoidance
        search_bounds = [(-5.0, 35.0), (-5.0, 15.0)]
        self.rrt_planner = RRTPathPlanner(graph=self.graph, search_space_bounds=search_bounds,obstacle_radius=1.5  # 1.5m padding radius around drones
        )
    def add_drone(self, location_id: int, emergency_drone: bool = False) -> int:
        """Add a new drone at the specified location"""
        drone = Drone(id=self.next_drone_id,current_location_id=location_id,status="available",emergency_drone=emergency_drone
        )
        self.drones[drone.id] = drone
        self.next_drone_id += 1
        return drone.id
    def create_request(
        self,
        requester_id: str,
        requester_name: str,
        requester_location_id: int,
        priority: Priority,
        description: str,
        emergency: bool = False,
        patient_id: Optional[str] = None, # patient selection (from  database)
        payload_items: Optional[Dict[str, int]] = None, # what the drone will carry
        #prioritization parameters, if patient_id is provided, auto-filled from patient data
        patient_age: Optional[int] = None,
        is_parent: bool = False,
        expected_life_years_gained: Optional[float] = None,
        quality_of_life_score: Optional[float] = None,
        lifestyle_responsibility: Optional[str] = None,
        social_role: Optional[str] = None,
        clinical_severity_score: Optional[float] = None
    ) -> int:
        """
        new drone request and add to priority queue
        nased on Vital Priority System (Pinho & Leal, 2025) and PPT research (Dery et al., 2020).
        
        if patient_id is provided, patient data will be used to auto-fill prioritization fields.
        Reference: Dery et al. (2020) - A systematic review of patient prioritization tools
        
        items define what the drone will carry:
        - if payload > 1.5kg, automatically split into multiple requests
        - critical items are first with available drones
        - items are queued until drones become available
        Reference: Jeong et al. (2019) - Truck-drone hybrid delivery routing
        returns: request_id (first request ID if split, or single request ID)
        raises: ValueError if no items selected or patient not found
        """
        if payload_items:
            is_valid, error_msg, total_weight = ItemCatalog.validate_payload(payload_items)
            if not is_valid:
                raise ValueError(error_msg)
        patient = None
        patient_critical = False
        if patient_id:
            patient = get_patient(patient_id)
            if not patient:
                raise ValueError(f"Patient {patient_id} not found in database")
            # if patient is critical for item prioritization
            from patients import CurrentStatus as PatientCurrentStatus
            status_enum = patient.current_status
            if isinstance(status_enum, PatientCurrentStatus):
                patient_critical = (status_enum == PatientCurrentStatus.CRITICAL) or patient.is_critical_vitals
            elif hasattr(status_enum, 'value'):
                patient_critical = (str(status_enum.value).lower() == 'critical') or patient.is_critical_vitals
            else:
                patient_critical = (str(status_enum).lower() == 'critical') or patient.is_critical_vitals
        # compute ALL prioritization fields from patient data if available
        #computed by the algorithm, not manually input
        if patient:
            patient_age = patient.age
            clinical_severity_score = patient.risk_score
            is_parent = patient.age and 20 <= patient.age <= 60
            # expected life years gained: estimate based on age, e.g. ounger patients have more potential life years to gain
            if patient.age:
                if patient.age < 25:
                    expected_life_years_gained = max(0, 65 - patient.age)  # estimate retirement age
                elif patient.age < 65:
                    expected_life_years_gained = max(0, 75 - patient.age)  # est life expectancy
                else:
                    expected_life_years_gained = max(0, 85 - patient.age)  # est life expectancy for elderly
            else:
                expected_life_years_gained = None
            # qual of life improvement: estimate based on patient status and condition
            # improving patients have higher expected QoL improvement
            from patients import CurrentStatus as PatientCurrentStatus
            status_qol_scores = {PatientCurrentStatus.IMPROVING: 0.8,PatientCurrentStatus.STABLE: 0.6,PatientCurrentStatus.MONITORING: 0.4,PatientCurrentStatus.DETERIORATING: 0.2,PatientCurrentStatus.CRITICAL: 0.1
            }
            # handle both enum and string status values
            patient_status = patient.current_status
            if isinstance(patient_status, PatientCurrentStatus):
                status_enum = patient_status# already enum
            elif hasattr(patient_status, 'value'):
                status_enum = patient_status # enum w value attribute
            else:
                #  string to enum if needed
                status_map = {
                    'improving': PatientCurrentStatus.IMPROVING,
                    'stable': PatientCurrentStatus.STABLE,
                    'monitoring': PatientCurrentStatus.MONITORING,
                    'deteriorating': PatientCurrentStatus.DETERIORATING,
                    'critical': PatientCurrentStatus.CRITICAL
                }
                status_str = patient_status.lower() if isinstance(patient_status, str) else str(patient_status).lower()
                status_enum = status_map.get(status_str, PatientCurrentStatus.MONITORING)
            quality_of_life_score = status_qol_scores.get(status_enum, 0.5)
            # adjust based on age (younger = higher potential improvement)
            if patient.age:
                age_factor = max(0.5, 1.0 - (patient.age / 100.0))
                quality_of_life_score *= age_factor
            # social role: infer from patient data (if available in future, for now use general)
            # COULD be extracted from patient metadata if available
            social_role = "general"  # default, can be enhanced with patient data
            # based on lifestyle risks;Fewer lifestyle risks = more responsible
            if len(patient.lifestyle_risks) == 0:
                lifestyle_responsibility = "responsible"
            elif len(patient.lifestyle_risks) <= 1:
                lifestyle_responsibility = "moderate"
            else:
                lifestyle_responsibility = "irresponsible"
            # if crit status/vitls, make sure emergency flag is set, use the status_enum we already determined above
            if status_enum == PatientCurrentStatus.CRITICAL or patient.is_critical_vitals:
                if priority.value < 4:  # If not already CTAS I or II
                    # don't override CTAS, ensure emergency flag reflects shows condition
                    emergency = emergency or True
        #  if emergency based on CTAS (I and II are emergency) or patient condition
        is_emergency_request = emergency or priority.is_emergency
        #  if payload needs to be split (if > 1.5kg)
        total_weight = ItemCatalog.calculate_total_weight(payload_items or {})
        if total_weight > ItemCatalog.MAX_PAYLOAD_CAPACITY_KG:
            #  payload into multiple prioritized requests
            split_payloads = ItemCatalog.split_payload(payload_items, patient_critical)
            if not split_payloads:
                raise ValueError("Failed to split payload - no valid payloads generated")
            #  parent request ID (first request will be parent)
            parent_request_id = self.next_request_id
            request_ids = []
            #  requests for each split payload, with most critical items first
            for idx, split_payload in enumerate(split_payloads):
                is_first = (idx == 0)
                is_last = (idx == len(split_payloads) - 1)
                request = Request( #very long so i expanded it LOL
                    id=self.next_request_id,
                    requester_id=requester_id,
                    requester_name=requester_name,
                    requester_location_id=requester_location_id,
                    priority=priority,
                    description=f"{description} (Part {idx + 1}/{len(split_payloads)})" if len(split_payloads) > 1 else description,
                    emergency=is_emergency_request,
                    patient_id=patient_id,
                    payload_items=split_payload,
                    # multi-criteria prioritization fields, automatically from patient data
                    patient_age=patient_age,
                    waiting_time_minutes=0.0,
                    is_parent=is_parent,
                    expected_life_years_gained=expected_life_years_gained,
                    quality_of_life_score=quality_of_life_score,
                    lifestyle_responsibility=lifestyle_responsibility,
                    social_role=social_role,
                    clinical_severity_score=clinical_severity_score,
                    # multi-request tracking
                    parent_request_id=parent_request_id if not is_first else None,
                    is_partial_delivery=len(split_payloads) > 1,
                    delivery_sequence=idx + 1,
                    total_deliveries=len(split_payloads)
                )
                self.requests[request.id] = request
                request_ids.append(request.id)
                # all reqs -> priority queue but most critical are first
                # priority queue naturally prioritize based on CTAS and VPS
                heapq.heappush(self.priority_queue, request)
                self.next_request_id += 1
            #  pending req to assign drones,to most critical items first
            self._process_pending_requests()
            #  parent request ID (first request)
            return parent_request_id
        else:
            # single request (payload <= 1.5kg)
            request = Request( # too long LOL
                id=self.next_request_id,
                requester_id=requester_id,
                requester_name=requester_name,
                requester_location_id=requester_location_id,
                priority=priority,
                description=description,
                emergency=is_emergency_request,
                patient_id=patient_id,
                payload_items=payload_items or {},
                patient_age=patient_age,
                waiting_time_minutes=0.0,
                is_parent=is_parent,
                expected_life_years_gained=expected_life_years_gained,
                quality_of_life_score=quality_of_life_score,
                lifestyle_responsibility=lifestyle_responsibility,
                social_role=social_role,
                clinical_severity_score=clinical_severity_score
            )
            self.requests[request.id] = request
            heapq.heappush(self.priority_queue, request)
            self.next_request_id += 1
            self._process_pending_requests() # try to assign a drone
            return request.id
    
    def _get_available_drone_locations(self, for_emergency: bool = False) -> List[int]:
        """Get list of location IDs where available drones are located
        
        Args:
            for_emergency: true - returns only emergency drones, false - returns normal drones.
                           emergency drones handle both, normal drones only handle normal requests.
        
        Returns:
            List of location IDs where available drones are located (at charging stations or other locations)
        """
        available_locations = []
        for drone in self.drones.values():
            # Only include drones that are:
            # 1. Available (not assigned, charging, or returning to charging)
            # 2. Not currently charging
            # 3. Have sufficient battery
            # Note: Drones at charging stations but not charging are available for assignment
            if (drone.status == "available" and 
                not drone.is_charging and
                drone.status != "returning_to_charging" and
                drone.status != "assigned" and
                drone.battery_level_kwh >= self.MIN_BATTERY_THRESHOLD):
                if for_emergency:
                    # Emergency requests can use emergency drones
                    if drone.emergency_drone:
                        available_locations.append(drone.current_location_id)
                else:
                    # Normal requests use normal drones only
                    if not drone.emergency_drone:
                        available_locations.append(drone.current_location_id)
        return available_locations
    
    def _get_speed_for_priority(self, priority: Priority) -> float:
        """Get drone speed based on request priority"""
        if priority == Priority.CTAS_I or priority == Priority.CTAS_II:
            return self.EMERGENCY_SPEED_M_PER_SEC
        elif priority == Priority.CTAS_III:
            return self.NORMAL_SPEED_M_PER_SEC
        else:  # CTAS_IV or CTAS_V
            return self.LOW_PRIORITY_SPEED_M_PER_SEC
    
    def _calculate_path_efficiency(
        self,request: Request,drone_start_location_id: int,destination_location_id: int,chosen_route: List[int], drone_speed_m_per_sec: float
    ):
        """
        path efficiency by comparing chosen RRT-optimized path with alternative paths (e.g., simple Dijkstra shortest path)
        stores efficiency metrics in request:
        - chosen_path_distance_meters: distance of current path
        - alternative_path_distance_meters: distance of alt path
        - path_efficiency_percentage: how much more efficient chosen path is (0-100%)
        - time_saved_vs_alternative_seconds: time saved compared to alternative
        - path_efficiency_ratio: ratio of alternative_time / chosen_time (higher = more efficient)
        """
        if not chosen_route or len(chosen_route) < 2:
            return
        chosen_distance = sum(
            self.graph.find_shortest_path(chosen_route[i], chosen_route[i + 1])[1]
            for i in range(len(chosen_route) - 1)
        )
        chosen_distance_meters = chosen_distance
        _, alternative_distance = self.graph.find_shortest_path(drone_start_location_id,destination_location_id)
        alternative_distance_meters = alternative_distance
        if drone_speed_m_per_sec > 0:
            chosen_time = chosen_distance_meters / drone_speed_m_per_sec
            alternative_time = alternative_distance_meters / drone_speed_m_per_sec
            time_saved_seconds = alternative_time - chosen_time
            path_efficiency_percentage = (time_saved_seconds / alternative_time * 100.0) if alternative_time > 0 else 0.0
            path_efficiency_ratio = (alternative_time / chosen_time) if chosen_time > 0 else 1.0
        else:
            path_efficiency_percentage = ((alternative_distance_meters - chosen_distance_meters) / alternative_distance_meters * 100.0) if alternative_distance_meters > 0 else 0.0
            path_efficiency_ratio = (alternative_distance_meters / chosen_distance_meters) if chosen_distance_meters > 0 else 1.0
            time_saved_seconds = 0.0
        request.chosen_path_distance_meters = chosen_distance_meters
        request.alternative_path_distance_meters = alternative_distance_meters
        request.path_efficiency_percentage = path_efficiency_percentage
        request.time_saved_vs_alternative_seconds = time_saved_seconds
        request.path_efficiency_ratio = path_efficiency_ratio
    
    def _calculate_current_battery_consumption(self, drone: Drone, current_time: datetime) -> Tuple[float, float]:
        """Calculate battery consumed and distance traveled since flight started"""
        # Calculate for drones that are actively moving (assigned, in_transit, or returning to charging)
        if drone.status not in ["assigned", "in_transit", "returning_to_charging"] or not drone.delivery_route or len(drone.delivery_route) < 2:
            return 0.0, 0.0
        flight_info = self.active_flights.get(drone.id)
        if not flight_info or not flight_info.get('start_time'):
            return 0.0, 0.0
        start_time = flight_info['start_time']
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        if elapsed_seconds <= 0:
            return 0.0, 0.0
        speed = flight_info.get('speed', self.NORMAL_SPEED_M_PER_SEC)
        distance_traveled_meters = elapsed_seconds * speed
        flight_info['distance_traveled_meters'] = distance_traveled_meters
        current_payload = flight_info.get('payload_weight', drone.current_payload_weight_kg)
        energy_per_meter = EnergyCalculator.calculate_drone_energy_per_meter(current_payload)
        energy_consumed = distance_traveled_meters * energy_per_meter
        if flight_info.get('is_new_flight', True):
            energy_consumed += EnergyCalculator.DRONE_ENERGY_BASE
            flight_info['is_new_flight'] = False
        flight_info['battery_consumed_kwh'] = energy_consumed
        drone.battery_consumed_this_flight_kwh = energy_consumed
        return energy_consumed, distance_traveled_meters
    
    def _calculate_route_energy(self, route: List[int], payload_weights: List[float], drone_speed: float) -> float:
        """Calculate total energy required for a multi-stop route"""
        if len(route) < 2:
            return 0.0
        total_energy = 0.0
        for i in range(len(route) - 1):
            from_loc = route[i]
            to_loc = route[i + 1]
            # distance
            path, distance = self.graph.find_shortest_path(from_loc, to_loc)
            distance_meters = distance * 1.0  #  to meters if needed
            #  payload weight for this leg (default to 0.5 if not saod)
            leg_payload = 0.5  # default
            if i < len(payload_weights):
                leg_payload = payload_weights[i]
            elif i > 0 and (i - 1) < len(payload_weights):
                #  previous weight if current not available
                leg_payload = payload_weights[i - 1]
            #  energy for this leg
            leg_energy = EnergyCalculator.calculate_drone_energy(
                distance_meters=distance_meters,
                payload_weight_kg=leg_payload
            )
            total_energy += leg_energy
        return total_energy
    
    def _evaluate_multi_stop_efficiency(self, drone: Drone, current_destination: int, secondary_request: Request, secondary_pickup_location: Optional[int] = None) -> Dict:
        """Check if drone should pick up secondary request during flight (energy efficiency and battery)"""
        #  current flight info
        flight_info = self.active_flights.get(drone.id, {})
        current_route = flight_info.get('route', [drone.current_location_id, current_destination])
        current_payload = flight_info.get('payload_weight', 0.0)
         # get pickup and delivery locations
        pickup_loc = secondary_pickup_location if secondary_pickup_location else secondary_request.requester_location_id
        delivery_loc = secondary_request.requester_location_id
        #  two scenarios: 1.  current route, assign separate drone for secondary (baseline), 2: reroute to pick up secondary request (combined)
        baseline_route = current_route.copy()
        baseline_weights = [current_payload, 0.0]  # Drop off first, then empty
        # energy for sep drone to do 2nd request
        separate_secondary_energy = EnergyCalculator.calculate_drone_energy(
            distance_meters=self.graph.find_shortest_path(pickup_loc, delivery_loc)[1] * 1.0,
            payload_weight_kg=secondary_request.payload_weight_kg or 0.5
        )
        baseline_energy = self._calculate_route_energy(
            baseline_route, baseline_weights, drone.current_speed_m_per_sec
        ) + separate_secondary_energy
        # 2. combined route (pick up secondary, then deliver both)
        combined_route = current_route.copy()
        # insert pickup location before current destination if on the way, else  after current destination
        if pickup_loc not in combined_route:
            # check if pickup closer to current position or destination
            current_pos = combined_route[0]  # assume drone starts at first location
            dist_to_pickup_from_current = self.graph.find_shortest_path(current_pos, pickup_loc)[1]
            dist_to_pickup_from_dest = self.graph.find_shortest_path(current_destination, pickup_loc)[1]
            if dist_to_pickup_from_current < dist_to_pickup_from_dest:
                combined_route.insert(1, pickup_loc)# pick up on way
            else:
                combined_route.insert(2, pickup_loc)# pick up after 1st delivery
         # add 2nd delivery location
        if delivery_loc not in combined_route:
            combined_route.append(delivery_loc)
        # re-plan combined route w RRT to avoid collissions
        if combined_route and len(combined_route) >= 2:
            start_loc = self.graph.nodes[combined_route[0]]
            goal_loc = self.graph.nodes[combined_route[-1]]
            #  other active drones (excluding current)
            other_flights = {
                did: info for did, info in self.active_flights.items()
                if did != drone.id
            }
            # get RRT path for combined route (collision avoidance)
            # ref: RRT* algorithm for dynamic obstacle avoidance (see rrt_pathfinding.py)
            rrt_path = self.rrt_planner.plan_path_with_traffic_rules(
                start_loc=start_loc,
                goal_loc=goal_loc,
                current_drone_id=drone.id,
                is_emergency=drone.emergency_drone,
                active_drone_flights=other_flights,
                all_drones=self.drones
            )
            #  RRT path if available, otherwise use original combined route
            if rrt_path and len(rrt_path) >= 2:
                # need key waypoints (pickup, delivery)  in path
                if pickup_loc not in rrt_path:
                    #  best insertion point
                    min_dist = float('inf')
                    insert_idx = 1
                    pickup_node = self.graph.nodes[pickup_loc]
                    for i, loc_id in enumerate(rrt_path):
                        node = self.graph.nodes[loc_id]
                        dist = self.graph.euclidean_distance(node, pickup_node)
                        if dist < min_dist:
                            min_dist = dist
                            insert_idx = i + 1
                    rrt_path.insert(insert_idx, pickup_loc)
                if delivery_loc not in rrt_path:
                    rrt_path.append(delivery_loc)
                combined_route = rrt_path
        #  cumulative payload weights
        combined_weights = []
        for i, loc in enumerate(combined_route):
            if loc == pickup_loc:
                combined_weights.append(current_payload + (secondary_request.payload_weight_kg or 0.5))
            elif loc == current_destination:
                combined_weights.append((secondary_request.payload_weight_kg or 0.5))  # After first delivery
            else:
                combined_weights.append(0.0)  # Empty
        #  priority speed for combined route
        combined_speed = self._get_speed_for_priority(secondary_request.priority)
        combined_energy = self._calculate_route_energy(combined_route, combined_weights, combined_speed)
        #  energy savings (negative = more energy, positive = less energy)
        energy_difference = baseline_energy - combined_energy
        #  battery 
        required_energy = combined_energy
        battery_sufficient = drone.battery_level_kwh >= required_energy + self.MIN_BATTERY_THRESHOLD
        # decision logic:1. enough battery 2. energy better or at most 10% worse
        should_accept = battery_sufficient and (energy_difference > -0.1 * baseline_energy or energy_difference > 0)
        reason = ""
        if not battery_sufficient:
            reason = f"Insufficient battery ({drone.battery_level_kwh:.3f} kWh < {required_energy:.3f} kWh required)"
        elif energy_difference < -0.1 * baseline_energy:
            reason = f"Less energy efficient ({energy_difference:.4f} kWh worse)"
        else:
            reason = f"Energy efficient ({energy_difference:.4f} kWh saved)"
        return {
            'should_accept': should_accept,
            'energy_difference': energy_difference,
            'battery_sufficient': battery_sufficient,
            'required_battery': required_energy,
            'reason': reason,
            'combined_route': combined_route if should_accept else None
        }
    
    def _check_and_intercept_request(self, new_request: Request) -> bool:
        """check if any in-flight drone should intercept this non-urgent request"""
        if new_request.priority.is_emergency:
            return False
        best_evaluation = None
        best_drone = None
        # check all in-flight drones
        for drone_id, flight_info in self.active_flights.items():
            if drone_id not in self.drones:
                continue
            drone = self.drones[drone_id]
            #  normal drones can intercept non-urgent requests
            if drone.emergency_drone:
                continue
            # drone must be in flight
            if drone.status != "assigned" and drone.status != "in_transit":
                continue
            #  current destination
            current_route = flight_info.get('route', [])
            if len(current_route) < 2:
                continue
            current_destination = current_route[1]  # next stop
            #  if this drone should pick up the request
            evaluation = self._evaluate_multi_stop_efficiency(drone=drone,current_destination=current_destination,secondary_request=new_request
            ) # eval if drone should pick up req, returns dict with decision and metrics (energy savings, battery sufficiency, etc.)        
            if evaluation['should_accept']:
                if best_evaluation is None or evaluation['energy_difference'] > best_evaluation['energy_difference']:
                    best_evaluation = evaluation
                    best_drone = drone # best drone found
        # if suitable drone, assign the request to it
        if best_drone and best_evaluation:
            # re-plan route w RRT to avoid collissions
            current_route = flight_info.get('route', [])
            if current_route:
                current_loc = self.graph.nodes[current_route[0]]  # current location
            else:
                current_loc = self.graph.nodes[best_drone.current_location_id]
            # goal location (last in combined route)
            combined_route_ids = best_evaluation['combined_route']
            goal_loc_id = combined_route_ids[-1] if combined_route_ids else new_request.requester_location_id
            goal_loc = self.graph.nodes[goal_loc_id]
            # re-plan w RRT considering all active drones 
            rrt_path = self.rrt_planner.plan_path_with_traffic_rules(
                start_loc=current_loc,
                goal_loc=goal_loc,
                current_drone_id=best_drone.id,
                is_emergency=best_drone.emergency_drone,
                active_drone_flights=self.active_flights,
                all_drones=self.drones
            )
            #  include the new pickup and delivery (using RRT path)
            flight_info = self.active_flights[best_drone.id]
            flight_info['route'] = rrt_path if rrt_path else combined_route_ids
            #  payload weight 
            flight_info['payload_weight'] = (flight_info.get('payload_weight', 0.0) + 
                                            (new_request.payload_weight_kg or 0.5))
            #  request ID to flight's request list
            if 'request_ids' not in flight_info:
                flight_info['request_ids'] = []
            flight_info['request_ids'].append(new_request.id)
            #  request to drone
            new_request.status = RequestStatus.ASSIGNED
            new_request.assigned_drone_id = best_drone.id
            #  drone speed based on priority (slower for low priority)
            # low priority requests = slower speed to allow more time for multi-stop decisions
            best_drone.current_speed_m_per_sec = self._get_speed_for_priority(new_request.priority)
            flight_info['speed'] = best_drone.current_speed_m_per_sec
            # update drone's delivery route
            best_drone.delivery_route = rrt_path if rrt_path else combined_route_ids
            best_drone.current_payload_weight_kg = flight_info['payload_weight']
            return True
        return False
    
    def _assign_drone_to_request(self, request: Request) -> bool:
        """Assign closest available drone to request using RRT path planning"""
        is_emergency = request.emergency or request.priority.is_emergency
        available_locations = self._get_available_drone_locations(for_emergency=is_emergency)
        if not available_locations:
            return False
        closest_loc_id = self.graph.find_closest_drone_location(request.requester_location_id, available_locations)
        if closest_loc_id is None:
            return False
        assigned_drone = None
        for drone in self.drones.values():
            if (drone.status == "available" and 
                drone.current_location_id == closest_loc_id and
                drone.emergency_drone == is_emergency and
                not drone.is_charging and
                drone.battery_level_kwh >= self.MIN_BATTERY_THRESHOLD):
                assigned_drone = drone
                break
        if assigned_drone is None:
            return False
        start_loc = self.graph.nodes[closest_loc_id]
        goal_loc = self.graph.nodes[request.requester_location_id]
        path = self.rrt_planner.plan_path_with_traffic_rules(start_loc=start_loc,goal_loc=goal_loc,current_drone_id=assigned_drone.id,is_emergency=is_emergency,active_drone_flights=self.active_flights,all_drones=self.drones
        )
        distance = sum(
            self.graph.find_shortest_path(path[i], path[i + 1])[1]
            for i in range(len(path) - 1)
        ) if len(path) >= 2 else self.graph.find_shortest_path(closest_loc_id, request.requester_location_id)[1]
        if len(path) < 2:# fallback to simple path
            path, _ = self.graph.find_shortest_path(closest_loc_id, request.requester_location_id)
        payload_weight = request.payload_weight_kg or 0.5
        required_energy = EnergyCalculator.calculate_drone_energy(distance, payload_weight)
        if assigned_drone.battery_level_kwh < required_energy + self.MIN_BATTERY_THRESHOLD:
            self._send_drone_to_charging(assigned_drone.id)
            return False
        priority_speed = self._get_speed_for_priority(request.priority)
        assigned_drone.current_speed_m_per_sec = priority_speed
        assigned_drone.status = "assigned"
        assigned_drone.assigned_request_id = request.id
        assigned_drone.current_payload_weight_kg = payload_weight
        assigned_drone.delivery_route = path
        assigned_drone.flight_start_time = datetime.now()
        assigned_drone.battery_consumed_this_flight_kwh = 0.0
        request.status = RequestStatus.ASSIGNED
        request.assigned_drone_id = assigned_drone.id
        self.active_flights[assigned_drone.id] = {
            'route': path,
            'payload_weight': payload_weight,
            'start_time': datetime.now(),
            'request_ids': [request.id],
            'speed': priority_speed,
            'is_emergency': is_emergency,
            'initial_battery_kwh': assigned_drone.battery_level_kwh,
            'distance_traveled_meters': 0.0,
            'is_new_flight': True
        }
        travel_time_seconds = (distance / priority_speed) + 5
        timer = threading.Timer(travel_time_seconds, self._auto_complete_request, args=[request.id])
        timer.daemon = True
        timer.start()
        return True
    
    def _update_waiting_times(self):
        """Update waiting time for all pending requests (used in prioritization)"""
        now = datetime.now()
        for req in self.requests.values():
            if req.status == RequestStatus.PENDING:
                elapsed = now - req.timestamp
                req.waiting_time_minutes = elapsed.total_seconds() / 60.0
    
    def _process_pending_requests(self):
        """
        process all pending requests in priority order
        assign drones to highest priority requests first
        checks if in-flight drones can intercept them
        uses CTAS for primary sorting, then Vital Priority Score for tie-breaking
        """
        # update wait times before processing (affects priority score)
        self._update_waiting_times()
        # remake priority queue with pending requests only
        pending_requests = [req for req in self.priority_queue if req.status == RequestStatus.PENDING]
        self.priority_queue = pending_requests
        heapq.heapify(self.priority_queue)
        #  requests in priority order
        temp_queue = []
        while self.priority_queue:
            request = heapq.heappop(self.priority_queue)
            if request.status != RequestStatus.PENDING:
                continue
            #  non-urgent requests (CTAS IV and V), try to stop with in-flight drones first
            if not request.priority.is_emergency:
                if self._check_and_intercept_request(request):
                    # req was intercepted by an in-flight drone
                    continue
            #   assign to available drone
            if self._assign_drone_to_request(request):
                #  successful
                pass
            else:
                # no available drones
                temp_queue.append(request)
        # restore unassigned requests
        for req in temp_queue:
            heapq.heappush(self.priority_queue, req)
    
    def complete_request(
        self,request_id: int,drone_final_location_id: int,traditional_method: str = "vehicle",
        payload_weight_kg: Optional[float] = None
    ):
        """
        mark a req as completed and return drone to available status
        get energy savings for the trip
        
        Args:
            request_id: ID of req to complete
            drone_final_location_id: place where drone ends up after delivery
            payload_weight_kg: Weight of payload in kg
        """
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")
        request = self.requests[request_id]
        request.status = RequestStatus.COMPLETED
        request.completed_at = datetime.now()  # Track when request was completed
        #  drone back to available status
        if request.assigned_drone_id:
            drone = self.drones[request.assigned_drone_id]
            #  total distance traveled using flight route if available
            flight_info = self.active_flights.get(request.assigned_drone_id, {})
            route = flight_info.get('route', [])
            
            # Get original start location from route if available, otherwise from drone's delivery_route
            # or fall back to current location (shouldn't happen, but safe fallback)
            if route and len(route) >= 2:
                # Use first node in route as the original start location
                drone_start_location = route[0]
            elif drone.delivery_route and len(drone.delivery_route) >= 2:
                # Fallback to drone's delivery route
                drone_start_location = drone.delivery_route[0]
                route = drone.delivery_route
            else:
                # Last resort: use current location (but this means route tracking is missing)
                drone_start_location = drone.current_location_id
                route = [drone_start_location, request.requester_location_id]
            #  total distance from route
            total_distance = 0.0
            if len(route) >= 2:
                for i in range(len(route) - 1):
                    path, dist = self.graph.find_shortest_path(route[i], route[i + 1])
                    total_distance += dist
                # if final location is diff from last route location, add return trip
                if drone_final_location_id != route[-1]:
                    path_from_last, dist_from_last = self.graph.find_shortest_path(
                        route[-1],
                        drone_final_location_id
                    )
                    total_distance += dist_from_last
            else:
                # fall back to simple path calculation
                path_to_requester, dist_to_requester = self.graph.find_shortest_path(
                    drone_start_location,
                    request.requester_location_id
                )
                # If final location is diff from requester location, add return trip
                if drone_final_location_id != request.requester_location_id:
                    path_from_requester, dist_from_requester = self.graph.find_shortest_path(
                        request.requester_location_id,
                        drone_final_location_id
                    )
                    total_distance = dist_to_requester + dist_from_requester
                else:
                    total_distance = dist_to_requester
            #  distance (in graph units) to meters
            # if graph weights are in meters, if not, adjust conversion factor
            distance_meters = total_distance * 1.0  # Adjust if your weights are in different units
            #  actual payload weight from items, or provided weight, or default
            actual_payload_weight = payload_weight_kg
            if actual_payload_weight is None:
                #  weight calculated from payload items
                actual_payload_weight = request.payload_weight_kg
                if actual_payload_weight <= 0:
                    # default weight if no items specified
                    actual_payload_weight = 0.5
            # get energy consumption and savings
            drone_energy, traditional_energy, energy_saved = EnergyCalculator.calculate_energy_savings(
                distance_meters=distance_meters,
                payload_weight_kg=actual_payload_weight,
                traditional_method=traditional_method
            )
             #  CO2 savings
            co2_saved = EnergyCalculator.calculate_co2_equivalent(energy_saved, energy_source="grid")
            # update request with energy data
            request.distance_traveled_meters = distance_meters
            request.drone_energy_kwh = drone_energy
            request.traditional_energy_kwh = traditional_energy
            request.energy_saved_kwh = energy_saved
            request.co2_saved_kg = co2_saved
            request.traditional_method = traditional_method
            request.payload_weight_kg = payload_weight_kg
            # get path efficiency compared to alternative paths
            # compare w a Dijkstra shortest path (no collision avoidance)
            # Only calculate if we have a valid route with at least 2 nodes
            if route and len(route) >= 2 and drone_start_location != request.requester_location_id:
                # Get speed from flight info if available, otherwise use current speed
                flight_speed = flight_info.get('speed', drone.current_speed_m_per_sec)
                if flight_speed <= 0:
                    flight_speed = self.NORMAL_SPEED_M_PER_SEC
                self._calculate_path_efficiency(request, drone_start_location, request.requester_location_id, route, flight_speed)
            # after done request process pending requests again so queued parts of split orders to be assigned when drones become available
            self._process_pending_requests()
            self.total_energy_saved_kwh += energy_saved
            self.total_co2_saved_kg += co2_saved
            # Update drone battery (deplete energy used)
            # Use the route we already retrieved earlier - don't overwrite it
            # flight_info and route are already set above (lines 670-685)
            # Only get request_ids from active_flights if needed
            if not flight_info:
                flight_info = self.active_flights.get(drone.id, {})
            # get payload weights for each leg of the route
            payloads = []
            #  all reqs in this flight (if multi-stop)
            request_ids = flight_info.get('request_ids', [request.id])
            all_requests = [self.requests.get(rid) for rid in request_ids if self.requests.get(rid)]
            all_requests = [r for r in all_requests if r]  # Remove None values
            #  payload weights for each leg
            current_payload = 0.0
            delivered_requests = set()
            for i in range(len(route) - 1):
                #  payload at the start of this leg, check if we're picking up at current location
                current_loc = route[i]
                next_loc = route[i + 1]
                #  if any request's pickup is at current location
                for req in all_requests:
                    if req.requester_location_id == current_loc and req.id not in delivered_requests:
                        current_payload += (req.payload_weight_kg or 0.5)
                #  weight for this leg (before delivery at next location)
                payloads.append(current_payload)
                #  if we're delivering at next location
                for req in all_requests:
                    if req.requester_location_id == next_loc and req.id not in delivered_requests:
                        current_payload = max(0.0, current_payload - (req.payload_weight_kg or 0.5))
                        delivered_requests.add(req.id)
            #  no payloads calculated, use simple calculation
            if not payloads:
                payloads = [request.payload_weight_kg or 0.5] if len(route) >= 2 else [0.0]
            #  actual energy consumed for the route, real-time battery consumption if available (from flight tracking), otherwise calculate from route
            flight_info = self.active_flights.get(drone.id, {})
            if flight_info.get('battery_consumed_kwh') is not None:
                #  tracked real-time battery consumption
                actual_energy = flight_info['battery_consumed_kwh']
                drone.battery_consumed_this_flight_kwh = actual_energy
            else:
                # calculate energy from route
                actual_energy = self._calculate_route_energy(route, payloads, drone.current_speed_m_per_sec)
            #  battery level (deplete energy used during flight)
            drone.battery_level_kwh = max(0.0, drone.battery_level_kwh - actual_energy)
            
            # Remove delivery trip from active_flights tracking (before adding return trip)
            # This ensures we don't track both delivery and return trips simultaneously
            if drone.id in self.active_flights:
                flight_info = self.active_flights[drone.id]
                # Only remove if it's not already a return trip (shouldn't happen, but be safe)
                if not flight_info.get('is_return_trip', False):
                    del self.active_flights[drone.id]
            
            # After delivery, ALWAYS return drone to nearest charging station
            # This ensures drones are always ready for next assignment from a charging station
            drone.current_location_id = drone_final_location_id
            drone.assigned_request_id = None
            drone.current_payload_weight_kg = 0.0
            drone.delivery_route = []  # Clear delivery route before setting return route
            
            # Send drone to nearest charging station (will add return trip to active_flights)
            # This handles routing, battery consumption during return, and charging
            self._send_drone_to_charging(drone.id)
        #  pending req
        self._process_pending_requests()
    
    def _auto_complete_request(self, request_id: int):
        """
         complete a request when the drone arrives at destination
          called after the simulated travel time
        """
        with self.lock:
            if request_id not in self.requests:
                return  # req DNE
            request = self.requests[request_id]
            #  auto-complete if still assigned (not manually  or cancelled)
            if request.status != RequestStatus.ASSIGNED:
                return
            # Auto-complete: drone  at requester location and stays there(Final location = requester location)
            self.complete_request(
                request_id=request_id,
                drone_final_location_id=request.requester_location_id,
                traditional_method="vehicle",  # Default comparison method
                payload_weight_kg=None  # Use actual payload weight from request
            )
    
    def _send_drone_to_charging(self, drone_id: int):
        """Send drone to nearest charging station and route it there"""
        if drone_id not in self.drones:
            return
        drone = self.drones[drone_id]
        # if already at a charging station, just start charging
        if drone.current_location_id in self.CHARGING_STATION_LOCATIONS:
            drone.status = "charging"
            drone.is_charging = True
            drone.assigned_request_id = None
            drone.current_payload_weight_kg = 0.0
            drone.delivery_route = []
            drone.current_speed_m_per_sec = 0.0
            # calc time to charge (assume charging to 80% for efficiency)
            energy_needed = (drone.battery_capacity_kwh * 0.8) - drone.battery_level_kwh
            if energy_needed > 0:
                charge_time_seconds = energy_needed / self.CHARGE_RATE_KWH_PER_SEC
                # schedule charging completion
                timer = threading.Timer(charge_time_seconds, self._complete_charging, args=[drone_id])
                timer.daemon = True
                timer.start()
            return
        # get nearest charging station and route to it
        nearest_charging = None
        min_distance = float('inf')
        return_route = []
        
        for charging_loc in self.CHARGING_STATION_LOCATIONS:
            path, distance = self.graph.find_shortest_path(drone.current_location_id, charging_loc)
            if distance < min_distance:
                min_distance = distance
                nearest_charging = charging_loc
                return_route = path if path else [drone.current_location_id, charging_loc]

        if nearest_charging is None:
            # no charging station available, set to first one
            nearest_charging = self.CHARGING_STATION_LOCATIONS[0]
            return_route = [drone.current_location_id, nearest_charging]
        
        # if drone needs to travel to charging station, simulate the return trip
        if len(return_route) >= 2 and drone.current_location_id != nearest_charging:
            # Calculate return trip distance and time
            return_distance = sum(
                self.graph.find_shortest_path(return_route[i], return_route[i + 1])[1]
                for i in range(len(return_route) - 1)
            ) if len(return_route) >= 2 else min_distance
            # use normal speed for return trip (no payload)
            return_speed = self.NORMAL_SPEED_M_PER_SEC
            return_time_seconds = (return_distance / return_speed) + 2  # Add 2 seconds for arrival
            # update drone status for transit to charging station
            drone.status = "returning_to_charging"
            drone.assigned_request_id = None
            drone.current_payload_weight_kg = 0.0
            drone.delivery_route = return_route
            drone.current_speed_m_per_sec = return_speed
            
            # Store return trip info in active_flights for tracking (similar to delivery trips)
            # This allows the API/frontend to track the drone's return journey even if map doesn't render
            self.active_flights[drone.id] = {
                'route': return_route,
                'payload_weight': 0.0,  # No payload on return trip
                'start_time': datetime.now(),
                'request_ids': [],
                'speed': return_speed,
                'is_emergency': False,
                'initial_battery_kwh': drone.battery_level_kwh,
                'distance_traveled_meters': 0.0,
                'is_new_flight': True,
                'is_return_trip': True  # Mark this as a return trip (not a delivery)
            }
            
            # Schedule arrival at charging station
            def arrive_at_charging_station():
                with self.lock:
                    if drone_id in self.drones:
                        drone = self.drones[drone_id]
                        # Update battery based on return trip
                        return_distance_meters = return_distance * 1.0  # Convert to meters
                        return_energy = EnergyCalculator.calculate_drone_energy(return_distance_meters, 0.0)  # No payload on return
                        drone.battery_level_kwh = max(0.0, drone.battery_level_kwh - return_energy)
                        
                        # Arrive at charging station
                        drone.current_location_id = nearest_charging
                        drone.status = "charging"
                        drone.is_charging = True
                        drone.delivery_route = []  # Clear route
                        drone.current_speed_m_per_sec = 0.0
                        
                        # Remove from active flights tracking (return trip complete)
                        if drone.id in self.active_flights:
                            del self.active_flights[drone.id]
                        
                        # Start charging
                        energy_needed = (drone.battery_capacity_kwh * 0.8) - drone.battery_level_kwh
                        if energy_needed > 0:
                            charge_time_seconds = energy_needed / self.CHARGE_RATE_KWH_PER_SEC
                            timer = threading.Timer(charge_time_seconds, self._complete_charging, args=[drone_id])
                            timer.daemon = True
                            timer.start()
                        else:
                            # Already charged enough, make available immediately
                            self._complete_charging(drone_id)
            
            timer = threading.Timer(return_time_seconds, arrive_at_charging_station)
            timer.daemon = True
            timer.start()
        else:
            # Already at charging station or route is invalid, start charging immediately
            drone.current_location_id = nearest_charging
            drone.status = "charging"
            drone.is_charging = True
            drone.assigned_request_id = None
            drone.current_payload_weight_kg = 0.0
            drone.delivery_route = []
            drone.current_speed_m_per_sec = 0.0
            
            # Calculate time to charge
            energy_needed = (drone.battery_capacity_kwh * 0.8) - drone.battery_level_kwh
            if energy_needed > 0:
                charge_time_seconds = energy_needed / self.CHARGE_RATE_KWH_PER_SEC
                timer = threading.Timer(charge_time_seconds, self._complete_charging, args=[drone_id])
                timer.daemon = True
                timer.start()
            else:
                # Already charged enough
                self._complete_charging(drone_id)
    
    def _complete_charging(self, drone_id: int):
        """Complete drone charging"""
        with self.lock:
            if drone_id not in self.drones:
                return
            
            drone = self.drones[drone_id]
            drone.battery_level_kwh = drone.battery_capacity_kwh * 0.8  # Charge to 80%
            drone.is_charging = False
            drone.status = "available"
            
            # Process pending requests now that drone is available
        self._process_pending_requests()
    
    def cancel_request(self, request_id: int):
        """Cancel pending request"""
        if request_id not in self.requests:
            raise ValueError(f"Request {request_id} not found")
        
        request = self.requests[request_id]
        if request.status == RequestStatus.PENDING:
            request.status = RequestStatus.CANCELLED
            # Remove from priority queue (lazy deletion - handled in _process_pending_requests)
    
    def get_request_status(self, request_id: int) -> Optional[Request]:
        """Get current status of a request"""
        return self.requests.get(request_id)
    
    def get_all_pending_requests(self) -> List[Request]:
        """Get all pending requests sorted by priority"""
        pending = [req for req in self.requests.values() if req.status == RequestStatus.PENDING]
        return sorted(pending, key=lambda x: (-x.priority.value, x.timestamp))
    
    def get_drone_status(self, drone_id: int) -> Optional[Drone]:
        """Get current status of a drone"""
        return self.drones.get(drone_id)
    
    def get_statistics(self) -> Dict:
        """Get system statistics for monitoring including energy savings"""
        completed_with_energy = [
            r for r in self.requests.values()
            if r.status == RequestStatus.COMPLETED and r.energy_saved_kwh is not None
        ]
        
        avg_energy_saved = (
            sum(r.energy_saved_kwh for r in completed_with_energy) / len(completed_with_energy)
            if completed_with_energy else 0.0
        )
        
        # Calculate emergency and normal drone counts
        emergency_drones = [d for d in self.drones.values() if d.emergency_drone]
        normal_drones = [d for d in self.drones.values() if not d.emergency_drone]
        
        return {
            "total_drones": len(self.drones),
            "emergency_drones": len(emergency_drones),
            "normal_drones": len(normal_drones),
            "available_drones": sum(1 for d in self.drones.values() if d.status == "available"),
            "available_emergency_drones": sum(1 for d in emergency_drones if d.status == "available"),
            "available_normal_drones": sum(1 for d in normal_drones if d.status == "available"),
            "assigned_drones": sum(1 for d in self.drones.values() if d.status == "assigned"),
            "assigned_emergency_drones": sum(1 for d in emergency_drones if d.status == "assigned"),
            "assigned_normal_drones": sum(1 for d in normal_drones if d.status == "assigned"),
            "total_requests": len(self.requests),
            "pending_requests": sum(1 for r in self.requests.values() if r.status == RequestStatus.PENDING),
            "completed_requests": sum(1 for r in self.requests.values() if r.status == RequestStatus.COMPLETED),
            "emergency_requests": sum(1 for r in self.requests.values() if r.emergency),
            # Energy statistics
            "total_energy_saved_kwh": round(self.total_energy_saved_kwh, 4),
            "total_co2_saved_kg": round(self.total_co2_saved_kg, 4),
            "average_energy_saved_per_trip_kwh": round(avg_energy_saved, 4),
            "trips_with_energy_data": len(completed_with_energy)
        }
    
    def get_energy_report(self, request_id: int) -> Optional[Dict]:
        """
        Get detailed energy report for a completed request
        Includes time comparison with walking (3 mph = 4.828 km/h = 1.341 m/s)
        Returns None if request not found or not completed
        """
        request = self.requests.get(request_id)
        if not request or request.status != RequestStatus.COMPLETED:
            return None
        
        if request.energy_saved_kwh is None:
            return None
        
        # Get drone speed for time comparison
        # Try to get speed from drone if available, otherwise use priority-based speed
        drone_speed = None
        if request.assigned_drone_id and request.assigned_drone_id in self.drones:
            drone = self.drones[request.assigned_drone_id]
            # Use actual speed if available, otherwise estimate from priority
            drone_speed = drone.current_speed_m_per_sec if drone.current_speed_m_per_sec > 0 else None
        
        # If speed not available from drone, estimate from priority
        if drone_speed is None or drone_speed <= 0:
            drone_speed = self._get_speed_for_priority(request.priority)
        
        return EnergyCalculator.format_energy_report(
            drone_energy=request.drone_energy_kwh,
            traditional_energy=request.traditional_energy_kwh,
            energy_saved=request.energy_saved_kwh,
            distance_meters=request.distance_traveled_meters,
            co2_saved=request.co2_saved_kg,
            drone_speed_m_per_sec=drone_speed
        )