"""
RRT-based path planning with collision avoidance for drone navigation.
 RRT* (RRT-Star) algorithm for dynamic obstacle avoidance.

ref:
1. LaValle, S. M. (2014). Planning Algorithms. Cambridge University Press, pp. 228-237.
   https://lavalle.pl/planning/
2. LaValle, S. M. (1998). Rapidly-exploring random trees: A new tool for path planning.
   Research Report 9811. Department of Computer Science, Iowa State University.
3. Karaman, S., & Frazzoli, E. (2011). Sampling-based algorithms for optimal motion planning.
   The International Journal of Robotics Research, 30(7), 846-894.
   https://doi.org/10.1177/0278364911406761
   (RRT* algorithm)
4. motion-planning/rrt-algorithms: https://github.com/motion-planning/rrt-algorithms
   MIT License. Implementations of n-dimensional RRT and RRT* algorithms.
5. Aggorjefferson (2024). Exploring Path Planning with RRT* and Visualization in Python.
   Medium Article. https://medium.com/@aggorjefferson/exploring-path-planning-with-rrt-and-visualization-in-python-cf5bd80a6cd6

emergency vehicle algo:
6. Nayak, A., Rathinam, S., & Gopalswamy, S. (2020). Response of Autonomous Vehicles 
   to Emergency Response Vehicles (RAVEV). SAFE-D: Safety Through Disruption National 
   University Transportation Center. https://trid.trb.org/View/1717034
   (Emergency vehicle detection and yielding protocols)
7. Garg, A. (Self-Driving-Car). Obstacle prevention and ambulance detection modules.
   https://github.com/Aparajit-Garg/Self-Driving-Car
   (Ultrasonic sensor obstacle avoidance and emergency vehicle detection)
8. Gaochengzhi (Emergency_Traffic_Simulation). Emergency vehicle traffic simulation 
   with SUMO (Simulation of Urban Mobility). https://github.com/Gaochengzhi/Emergency_Traffic_Simulation
   (Traffic simulation with emergency vehicle priority and lane-changing behavior)
"""
from typing import Dict, List, Optional, Tuple, Set, TYPE_CHECKING
import random
import math
from dataclasses import dataclass
from models import Location
from graph import HospitalGraph
if TYPE_CHECKING:
    from models import Drone
@dataclass
class DronePosition:
    """shows a drone's current or future position for collision avoidance"""
    drone_id: int
    location_id: int
    x: float
    y: float
    z: float = 0.0  # height/altitude for 3D avoidance
    timestamp: float = 0.0  # when drone will be at this position
    is_emergency: bool = False
    speed: float = 2.5  # curr speed
    lane: int = 1  # lane assignment: 0=left, 1=middle, 2=right (default middle for emergency)
    priority_level: int = 3  # CTAS priority level (1-5, higher = more urgent)
class RRTPathPlanner:
    """
    RRT* (RRT-Star) path planner for collision-free drone navigation.
    handles dynamic obstacles (other drones) and priority-based right-of-way.
    emergency drones always have right of way - normal drones must yield.
    """
    def __init__(
        self,
        graph: HospitalGraph,
        search_space_bounds: List[Tuple[float, float]],
        obstacle_radius: float = 1.5,  # safety radius around drones/locations (meters)
        lane_width: float = 1.0  # width of each lane (meters) - 3 lanes = 3m total hallway width
    ):
        """
         RRT path planner with 3-lane system
        Args:
            graph: hospital graph for node-based path planning
            search_space_bounds: bounds for each dimension [(x_min, x_max), (y_min, y_max), ...]
            obstacle_radius: safety radius around obstacles (default 1.5m)
            lane_width: width of each lane (default 1.0m) - 3 lanes allow 3 drones side-by-side
        """
        self.graph = graph
        self.search_space_bounds = search_space_bounds
        self.obstacle_radius = obstacle_radius
        self.lane_width = lane_width  # 1m per lane, 3 lanes = 3m total hallway width
        # dynamic obstacles (other drones in flight)
        self.dynamic_obstacles: Dict[int, List[DronePosition]] = {}  # drone_id -> trajectory
        
    def update_drone_positions(self, drone_positions: Dict[int, DronePosition]):
        """
        update known drone positions for collision avoidance.
         before planning paths to ensure awareness of other drones.
        Args:drone_positions: Dictionary mapping drone_id to current position
        """
        self.dynamic_obstacles = {}
        for drone_id, position in drone_positions.items():
            if drone_id not in self.dynamic_obstacles:
                self.dynamic_obstacles[drone_id] = []
            self.dynamic_obstacles[drone_id].append(position)
    def _distance(self, p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
        """calc Euclidean distance between two 3D points"""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dz = p1[2] - p2[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    def _point_from_location(self, loc: Location, z: float = 0.0) -> Tuple[float, float, float]:
        """conv Location to 3D point"""
        return (loc.x, loc.y, z)
    
    def _assign_lane_for_drone(self, is_emergency: bool, priority_level: int = 3, other_drones_in_pathway: List[DronePosition] = None) -> int:
        """
        Assign lane based on priority for 3-lane system
        
        Rules:
        - Emergency/high priority (CTAS I/II, priority_level >= 4): Get middle lane (1) or any available lane
        - Normal/low priority (CTAS III/IV/V, priority_level <= 3): Get left (0) or right (2) lane, avoid middle
        - Lower priority drones must yield to higher priority ones
        
        Args:
            is_emergency: True if emergency drone
            priority_level: CTAS priority level (1-5, higher = more urgent)
            other_drones_in_pathway: Other drones in the same pathway segment (for lane conflict checking)
        
        Returns:
            Lane assignment: 0=left, 1=middle, 2=right
        """
        if other_drones_in_pathway is None:
            other_drones_in_pathway = []
        
        is_high_priority = is_emergency or priority_level >= 4
        
        if is_high_priority:
            # Emergency/high priority: Prefer middle lane (1), but can use any lane
            occupied_lanes = {pos.lane for pos in other_drones_in_pathway if hasattr(pos, 'lane') and pos.lane is not None}
            # If middle lane available, use it
            if 1 not in occupied_lanes:
                return 1
            # Otherwise use any available lane
            available_lanes = {0, 1, 2} - occupied_lanes
            if available_lanes:
                return min(available_lanes)  # Prefer left if multiple available
            # All lanes occupied by lower priority - emergency gets priority (will yield others)
            return 1  # Force middle lane (lower priority drones must yield)
        else:
            # Normal/low priority: Use left (0) or right (2), avoid middle
            occupied_lanes = {pos.lane for pos in other_drones_in_pathway if hasattr(pos, 'lane') and pos.lane is not None}
            # Check if any high-priority drones are in middle lane
            high_priority_in_middle = any(
                hasattr(pos, 'lane') and pos.lane == 1 and (pos.is_emergency or (hasattr(pos, 'priority_level') and pos.priority_level >= 4))
                for pos in other_drones_in_pathway
            )
            # Prefer left lane, then right lane
            if 0 not in occupied_lanes:
                return 0
            elif 2 not in occupied_lanes:
                return 2
            # Both side lanes occupied - check if we can use middle (only if no high-priority)
            if not high_priority_in_middle and 1 not in occupied_lanes:
                return 1
            # All lanes have conflicts - use left as default (lower priority must yield)
            return 0
    
    def _get_lane_offset(self, lane: int) -> Tuple[float, float]:
        """
        Get x,y offset for a given lane relative to pathway center
        
        Args:
            lane: Lane number (0=left, 1=middle, 2=right)
        
        Returns:
            (dx, dy) offset in meters (perpendicular to pathway direction)
        """
        # For simplicity, offset perpendicular to pathway
        # Left lane: -lane_width, Middle: 0, Right: +lane_width
        offset = (lane - 1) * self.lane_width  # -1.0, 0.0, +1.0
        # This will be applied perpendicular to the pathway direction
        return (offset, 0.0)  # Simplified - would need pathway direction for proper offset
    
    def _is_collision_free(
        self,
        point: Tuple[float, float, float], other_drones: Dict[int, List[DronePosition]],
        current_drone_id: int, is_emergency: bool, timestamp: float = 0.0, current_speed: float = 2.5,
        current_lane: int = 1, current_priority_level: int = 3
    ) -> bool:
        """
        Check collision with 3-lane system support
        
        Uses algorithms from:
        - Nayak, A., Rathinam, S., & Gopalswamy, S. (2020). Response of Autonomous Vehicles 
          to Emergency Response Vehicles (RAVEV). SAFE-D: Safety Through Disruption National 
          University Transportation Center. https://trid.trb.org/View/1717034
        - Garg, A. (Self-Driving-Car). Obstacle prevention and ambulance detection modules.
          https://github.com/Aparajit-Garg/Self-Driving-Car
        - Gaochengzhi (Emergency_Traffic_Simulation). Emergency vehicle traffic simulation.
          https://github.com/Gaochengzhi/Emergency_Traffic_Simulation
        
        Args:
            point: 3D point to check
            other_drones: Dictionary of other drones' positions
            current_drone_id: ID of drone planning this path
            is_emergency: True if current drone is emergency (has right of way)
            timestamp: Time at which point will be reached
            current_speed: Current speed of the planning drone (m/s)
            current_lane: Lane assignment for current drone (0=left, 1=middle, 2=right)
            current_priority_level: CTAS priority level for current drone (1-5)
        
        Returns:
            True if point is safe, False if collision detected
        """
        # Check collisions with other drones in 3-lane system
        for drone_id, trajectory in other_drones.items():
            if drone_id == current_drone_id:
                continue
            for i, other_pos in enumerate(trajectory):
                # Calculate time-to-collision for predictive avoidance
                time_to_point = timestamp
                time_delta = abs(time_to_point - other_pos.timestamp)
                # Estimate future position based on speed and direction
                predicted_pos = (other_pos.x, other_pos.y, other_pos.z)
                if len(trajectory) > i + 1:
                    next_pos = trajectory[i + 1]
                    # Estimate future position based on velocity
                    if time_delta > 0:
                        progress = min(1.0, time_delta / max(0.1, abs(next_pos.timestamp - other_pos.timestamp)))
                        predicted_pos = (
                            other_pos.x + (next_pos.x - other_pos.x) * progress,
                            other_pos.y + (next_pos.y - other_pos.y) * progress,
                            other_pos.z + (next_pos.z - other_pos.z) * progress
                        )
                
                # 3-lane system: Check if drones are in the same or conflicting lanes
                other_lane = getattr(other_pos, 'lane', 1)  # Default to middle if not set
                other_priority = getattr(other_pos, 'priority_level', 3)
                other_is_emergency = other_pos.is_emergency
                
                # Same lane: stricter collision check
                if current_lane == other_lane:
                    dist = self._distance(point, predicted_pos)
                    # In same lane, need more separation (at least 1 lane width)
                    if dist < self.lane_width * 1.5:  # 1.5× lane width for same-lane safety
                        # Lower priority must yield to higher priority
                        if (not is_emergency and current_priority_level < 4) and \
                           (other_is_emergency or other_priority >= 4):
                            return False  # Lower priority must yield
                        elif (is_emergency or current_priority_level >= 4) and \
                             (not other_is_emergency and other_priority < 4):
                            # Higher priority can pass, but still need minimum separation
                            if dist < self.lane_width * 0.8:
                                return False
                        else:
                            # Same priority level - both must maintain distance
                            if dist < self.lane_width * 1.5:
                                return False
                else:
                    # Different lanes: standard collision check (still need some separation)
                    dist = self._distance(point, predicted_pos)
                    if dist < self.obstacle_radius:
                        return False
                
                # Emergency vehicle yielding protocol (RAVEV-inspired)
                if other_is_emergency and not is_emergency and current_priority_level < 4:
                    # Emergency vehicles get larger safety margin and priority
                    # Normal drones must yield by maintaining larger distance
                    dist = self._distance(point, predicted_pos)
                    emergency_safety_radius = self.obstacle_radius * 3.0  # 3x safety margin for emergency
                    # Collision avoidance: check if we'll be in emergency vehicle's path
                    if dist < emergency_safety_radius:
                        return False
                    # Predictive check: if emergency vehicle is moving towards us
                    if other_pos.speed > current_speed and dist < emergency_safety_radius * 1.5:
                        return False
                    # Time-to-collision check: yield if collision predicted within safety time
                    relative_speed = abs(other_pos.speed - current_speed)
                    if relative_speed > 0:
                        time_to_collision = dist / relative_speed
                        if 0 < time_to_collision < 5.0:  # Yield if collision within 5 seconds
                            return False
                # Additional safety check: avoid path segments that cross emergency vehicle trajectories
                if other_is_emergency and not is_emergency and current_priority_level < 4:
                    dist = self._distance(point, predicted_pos)
                    # If emergency vehicle is ahead and moving in similar direction, maintain distance
                    if dist < self.obstacle_radius * 2.5:
                        return False
        return True
    def _steer(
        self,
        from_point: Tuple[float, float, float],
        to_point: Tuple[float, float, float],
        step_size: float
    ) -> Tuple[float, float, float]:
        """
        steer from one point towards another with maximum step size
        """
        distance = self._distance(from_point, to_point)
        if distance <= step_size:
            return to_point
        
        # Interpolate along the direction
        ratio = step_size / distance
        return (
            from_point[0] + (to_point[0] - from_point[0]) * ratio,
            from_point[1] + (to_point[1] - from_point[1]) * ratio,
            from_point[2] + (to_point[2] - from_point[2]) * ratio
        )
    
    def _nearest_node(
        self,
        nodes: List[Tuple[Tuple[float, float, float], int]],  # [(point, location_id), ...]
        point: Tuple[float, float, float]
    ) -> Tuple[Tuple[float, float, float], int]:
        """get nearest node in RRT tree to given point"""
        min_dist = float('inf')
        nearest = None
        for node_point, loc_id in nodes:
            dist = self._distance(node_point, point)
            if dist < min_dist:
                min_dist = dist
                nearest = (node_point, loc_id)
        return nearest
    def _near_nodes(
        self,
        nodes: List[Tuple[Tuple[float, float, float], int]],
        point: Tuple[float, float, float],
        radius: float
    ) -> List[Tuple[Tuple[float, float, float], int]]:
        """get all nodes within radius (for RRT* rewiring)"""
        near = []
        for node_point, loc_id in nodes:
            if self._distance(node_point, point) <= radius:
                near.append((node_point, loc_id))
        return near
    
    def plan_path_with_avoidance(
        self,
        start_loc: Location,
        goal_loc: Location,
        current_drone_id: int,
        is_emergency: bool,
        other_drones: Dict[int, List[DronePosition]],
        max_iterations: int = 500,
        step_size: float = 2.0,
        goal_radius: float = 3.0,
        current_priority_level: int = 3  # CTAS priority level (1-5)
    ) -> Optional[List[int]]:
        """
        algo based on:
        - LaValle, S. M. (2014). Planning Algorithms. Cambridge University Press, pp. 228-237.
        - Karaman, S., & Frazzoli, E. (2011). Sampling-based algorithms for optimal motion planning.
          The International Journal of Robotics Research, 30(7), 846-894. (RRT*)
        - motion-planning/rrt-algorithms: https://github.com/motion-planning/rrt-algorithms
        uses:- Nayak, A., Rathinam, S., & Gopalswamy, S. (2020). Response of Autonomous Vehicles 
          to Emergency Response Vehicles (RAVEV). SAFE-D: Safety Through Disruption National 
          University Transportation Center. https://trid.trb.org/View/1717034
        - Garg, A. (Self-Driving-Car). Obstacle prevention and ambulance detection modules.
          https://github.com/Aparajit-Garg/Self-Driving-Car
        - Gaochengzhi (Emergency_Traffic_Simulation). Emergency vehicle traffic simulation.
          https://github.com/Gaochengzhi/Emergency_Traffic_Simulation
        Args:
            start_loc: Starting location
            goal_loc: Goal location
            current_drone_id: ID of drone planning this path
            is_emergency: True if emergency drone (has right of way)
            other_drones: Positions of other drones to avoid
            max_iterations: Maximum RRT iterations
            step_size: Step size for RRT expansion
            goal_radius: Radius within which goal is considered reached
        Returns:Path as list of location IDs, or None if no path found
        """
        start_point = self._point_from_location(start_loc)
        goal_point = self._point_from_location(goal_loc)
        #  RRT tree with start node
        tree: List[Tuple[Tuple[float, float, float], int]] = [(start_point, start_loc.id)]
        parent: Dict[Tuple[float, float, float], Tuple[float, float, float]] = {}
        cost: Dict[Tuple[float, float, float], float] = {start_point: 0.0}
        location_map: Dict[Tuple[float, float, float], int] = {start_point: start_loc.id}
        goal_reached = False
        goal_node = None
        for i in range(max_iterations):
            # sample random point
            if random.random() < 0.1:  # 10% bias towards goal
                rand_point = goal_point
            else:
                rand_point = (
                    random.uniform(self.search_space_bounds[0][0], self.search_space_bounds[0][1]),
                    random.uniform(self.search_space_bounds[1][0], self.search_space_bounds[1][1]),
                    random.uniform(0.0, 5.0)  # Allow altitude variation for avoidance
                )
            #  nearest node
            nearest_point, nearest_loc_id = self._nearest_node(tree, rand_point)
            #  towards random point
            new_point = self._steer(nearest_point, rand_point, step_size)
            #  if collision-free (with enhanced emergency vehicle handling)
            #  current speed from trajectory estimation if available
            current_speed = 2.5  # def speed
            if other_drones:
                # est average speed from other drones for relative speed calculation
                for traj in other_drones.values():
                    if len(traj) > 1:
                        avg_speed = traj[0].speed if traj else 2.5
                        break
            if not self._is_collision_free(
                new_point, other_drones, current_drone_id, is_emergency, 
                timestamp=i * 0.1, current_speed=current_speed
            ):
                continue
            #  nearby nodes for rewiring (RRT*)
            near_nodes = self._near_nodes(tree, new_point, step_size * 2.0)
            #  best parent (RRT* optimization)
            best_parent = nearest_point
            min_cost = cost[nearest_point] + self._distance(nearest_point, new_point)
            for near_point, _ in near_nodes:
                if self._is_collision_free(
                    new_point, other_drones, current_drone_id, is_emergency, 
                    timestamp=i * 0.1, current_speed=current_speed
                ):
                    candidate_cost = cost[near_point] + self._distance(near_point, new_point)
                    if candidate_cost < min_cost:
                        min_cost = candidate_cost
                        best_parent = near_point
        #  new node to tree
            tree.append((new_point, nearest_loc_id))
            parent[new_point] = best_parent
            cost[new_point] = min_cost
            # rewire nearby nodes (RRT*)
            for near_point, _ in near_nodes:
                if near_point == best_parent:
                    continue
                new_cost = cost[new_point] + self._distance(near_point, new_point)
                if cost.get(near_point, float('inf')) > new_cost:
                    # check if rewiring creates collision-free path (with emergency vehicle awareness)
                    # Use same lane assignment logic for rewiring
                    rewiring_lane = 1 if (is_emergency or current_priority_level >= 4) else 0
                    if self._is_collision_free(
                        near_point, other_drones, current_drone_id, is_emergency, 
                        timestamp=i * 0.1, current_speed=current_speed,
                        current_lane=rewiring_lane, current_priority_level=current_priority_level
                    ):
                        parent[near_point] = new_point
                        cost[near_point] = new_cost
            # check if goal reached
            if self._distance(new_point, goal_point) <= goal_radius:
                goal_reached = True
                goal_node = new_point
                break
        if not goal_reached:
            # fallback: Use simple graph-based path if RRT fails
            path, _ = self.graph.find_shortest_path(start_loc.id, goal_loc.id)
            return path
        # reconstruct path
        path_points = []
        current = goal_node
        while current is not None:
            path_points.append(current)
            current = parent.get(current)
        path_points.reverse()
        # convert path points to location IDs
        # map 3D points back to graph locations
        path_locations = [start_loc.id]
        for point in path_points[1:]:  # Skip start (already added)
            # find closest location in graph
            closest_loc_id = None
            min_dist = float('inf')
            for loc_id, loc in self.graph.nodes.items():
                loc_point = self._point_from_location(loc)
                dist = self._distance(point, loc_point)
                if dist < min_dist:
                    min_dist = dist
                    closest_loc_id = loc_id
            if closest_loc_id and closest_loc_id != path_locations[-1]:
                path_locations.append(closest_loc_id)
        # ensure goal is in path
        if path_locations[-1] != goal_loc.id:
            path_locations.append(goal_loc.id)
        return path_locations
    
    def plan_path_with_traffic_rules(
        self,start_loc: Location, goal_loc: Location,
        current_drone_id: int, is_emergency: bool,active_drone_flights: Dict[int, dict], all_drones: Dict[int, 'Drone'],  # type: ignore
        current_priority_level: int = 3  # CTAS priority level (1-5, higher = more urgent)
    ) -> List[int]:
        """
         path with traffic rules and collision avoidance.
        
         with emergency vehicle algorithms from:
        - Nayak, A., Rathinam, S., & Gopalswamy, S. (2020). Response of Autonomous Vehicles 
          to Emergency Response Vehicles (RAVEV). SAFE-D: Safety Through Disruption National 
          University Transportation Center. https://trid.trb.org/View/1717034
          
        - Garg, A. (Self-Driving-Car). Obstacle prevention and ambulance detection modules.
          https://github.com/Aparajit-Garg/Self-Driving-Car
          
        - Gaochengzhi (Emergency_Traffic_Simulation). Emergency vehicle traffic simulation 
          with SUMO. https://github.com/Gaochengzhi/Emergency_Traffic_Simulation
        
         Rules:
        1. Emergency drones always have right of way
        2. Normal drones must yield to emergency drones (3x safety radius)
        3. Predictive avoidance: normal drones yield when emergency vehicles approach
        4. Time-to-collision prediction prevents collisions
        5. Normal drones negotiate paths to avoid collisions
        
        Args:
            start_loc: Starting location
            goal_loc: Goal location
            current_drone_id: ID of drone planning path
            is_emergency: True if emergency drone
            active_drone_flights: Active flight information for all drones
            all_drones: Dictionary of all drone objects
        
        Returns:path as list of location IDs
        """
        #  positions of other drones
        other_drone_positions: Dict[int, List[DronePosition]] = {}
        for drone_id, flight_info in active_drone_flights.items():
            if drone_id == current_drone_id:
                continue
            drone = all_drones.get(drone_id)
            if not drone or drone.status not in ["assigned", "in_transit"]:
                continue
            
            # Ggt drone's planned route
            route = flight_info.get('route', [])
            if not route:
                continue
            # estimate positions along route
            positions = []
            current_time = 0.0
            for i, loc_id in enumerate(route):
                if loc_id in self.graph.nodes:
                    loc = self.graph.nodes[loc_id]
                    speed = drone.current_speed_m_per_sec if drone else 2.5
                    # est time to reach this location
                    if i > 0:
                        prev_loc = self.graph.nodes[route[i-1]]
                        dist = self.graph.euclidean_distance(prev_loc, loc)
                        current_time += dist / speed
                    is_emerg = drone.emergency_drone if drone else False
                    # Get priority level from flight info or default based on emergency status
                    other_priority_level = flight_info.get('priority_level', 5 if is_emerg else 3)
                    # Assign lane based on priority (3-lane system)
                    # Collect other drones in same pathway segment for lane assignment
                    other_drones_in_segment = [p for traj in other_drone_positions.values() for p in traj if p.location_id == loc_id]
                    assigned_lane = self._assign_lane_for_drone(is_emerg, other_priority_level, other_drones_in_segment)
                    positions.append(DronePosition(
                        drone_id=drone_id,
                        location_id=loc_id,
                        x=loc.x,
                        y=loc.y,
                        z=0.0,
                        timestamp=current_time,
                        is_emergency=is_emerg,
                        speed=speed,
                        lane=assigned_lane,
                        priority_level=other_priority_level
                    ))
            if positions:
                other_drone_positions[drone_id] = positions
        
        #  RRT to plan collision-free path
        path = self.plan_path_with_avoidance(
            start_loc=start_loc,
            goal_loc=goal_loc,
            current_drone_id=current_drone_id,
            is_emergency=is_emergency,
            other_drones=other_drone_positions,
            max_iterations=300 if is_emergency else 500  # emergency drones get faster planning
        )
        if path is None or len(path) < 2:
            #  to simple shortest path
            path, _ = self.graph.find_shortest_path(start_loc.id, goal_loc.id)
        return path
