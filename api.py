"""REST API for hospital drone logistics system"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from typing import Optional
from datetime import datetime, timedelta
from models import Priority, RequestStatus, Request
from items import ItemCatalog
from patients import get_patient, get_all_patients
from main import initialize_hospital_system
from service import DroneAssignmentService
from energy import EnergyCalculator
app = Flask(__name__)
CORS(app)
service: Optional[DroneAssignmentService] = None
def serialize_request(req: Request, include_energy: bool = False) -> dict:
    """Convert Request to dict for API response"""
    if service and req.status == RequestStatus.PENDING:
        now = datetime.now()
        elapsed = now - req.timestamp
        req.waiting_time_minutes = elapsed.total_seconds() / 60.0
    req_data = {
        "id": req.id,"requester_id": req.requester_id,"requester_name": req.requester_name,"requester_location_id": req.requester_location_id,
        "status": req.status.value, "priority": req.priority.name, "priority_value": req.priority.value,
        "assigned_drone_id": req.assigned_drone_id,"description": req.description, "emergency": req.emergency,
        "timestamp": req.timestamp.isoformat(),"completed_at": req.completed_at.isoformat() if req.completed_at else None,
        # patient info
        "patient_id": req.patient_id,
        # payload info
        "payload_items": req.payload_items, "payload_weight_kg": round(req.payload_weight_kg, 3),
        "payload_description": req.payload_description, "max_payload_capacity_kg": ItemCatalog.MAX_PAYLOAD_CAPACITY_KG,
        # multi-request tracking (for split orders)
        "parent_request_id": req.parent_request_id,"is_partial_delivery": req.is_partial_delivery,
        "delivery_sequence": req.delivery_sequence,"total_deliveries": req.total_deliveries,
        # multi-criteria prioritization fields
        "vital_priority_score": round(req.calculate_vital_priority_score(), 2),"patient_age": req.patient_age,
        "waiting_time_minutes": round(req.waiting_time_minutes, 2),"is_parent": req.is_parent,
        "expected_life_years_gained": req.expected_life_years_gained, "quality_of_life_score": req.quality_of_life_score,
        "lifestyle_responsibility": req.lifestyle_responsibility,"social_role": req.social_role,"clinical_severity_score": req.clinical_severity_score
    }
    # incl patient data if patient_id is provided
    if req.patient_id:
        patient = req.get_patient_data()
        if patient:
            vitals_data = None
            if patient.current_vitals:
                v = patient.current_vitals
                vitals_data = {
                    "heart_rate": v.heart_rate,"blood_pressure_systolic": v.blood_pressure_systolic,
                    "blood_pressure_diastolic": v.blood_pressure_diastolic,"temperature": v.temperature,
                    "oxygen_saturation": v.oxygen_saturation,"respiratory_rate": v.respiratory_rate,
                    "pain_level": v.pain_level
                }
            req_data["patient"] = {
                "patient_id": patient.patient_id,"name": patient.name,"age": patient.age,"current_status": patient.current_status.value,"symptoms": patient.symptoms,"current_vitals": vitals_data,
                "risk_score": round(patient.risk_score, 3),"health_risks": patient.health_risks, "days_in_hospital": patient.days_in_hospital
            }
    # incl energy data if requested and available
    if include_energy and req.status == RequestStatus.COMPLETED and req.energy_saved_kwh is not None:
        energy_report = service.get_energy_report(req.id) if service else None
        if energy_report:
            req_data["energy"] = energy_report
    # incl path efficiency data if available (for completed requests)
    if req.status == RequestStatus.COMPLETED and req.path_efficiency_percentage is not None:
        req_data["path_efficiency"] = {
            "chosen_path_distance_meters": round(req.chosen_path_distance_meters, 2) if req.chosen_path_distance_meters else None,
            "alternative_path_distance_meters": round(req.alternative_path_distance_meters, 2) if req.alternative_path_distance_meters else None,
            "path_efficiency_percentage": round(req.path_efficiency_percentage, 2),
            "time_saved_vs_alternative_seconds": round(req.time_saved_vs_alternative_seconds, 2) if req.time_saved_vs_alternative_seconds else None,
            "path_efficiency_ratio": round(req.path_efficiency_ratio, 2) if req.path_efficiency_ratio else None
        }
    return req_data
@app.route('/')
def index():
    """Serve the main dashboard UI"""
    return render_template('index.html')
@app.route('/map.js')
def serve_map_js():
    """Serve the map.js file"""
    from flask import send_from_directory
    import os
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'map.js', mimetype='application/javascript')
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service_initialized": service is not None})
@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Initialize the hospital system"""
    global service
    service = initialize_hospital_system()
    return jsonify({
        "status": "initialized",
        "statistics": service.get_statistics()
    })
@app.route('/api/request/create', methods=['POST'])
def create_request():
    """Create a new drone request"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    
    # Get JSON data from request
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON data or Content-Type not application/json"}), 400
    
    required_fields = ['requester_id', 'requester_name', 'requester_location_id', 'priority']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    # map priority string to CTAS enum
    priority_map = {
        "ctas_i": Priority.CTAS_I, "ctas_ii": Priority.CTAS_II,"ctas_iii": Priority.CTAS_III,
        "ctas_iv": Priority.CTAS_IV,"ctas_v": Priority.CTAS_V,
        # backward compatibility aliases
        "emergency_critical": Priority.CTAS_I,"emergency_urgent": Priority.CTAS_II,"normal_high": Priority.CTAS_III,
        "normal_low": Priority.CTAS_IV
    }
    priority_str = data.get('priority', 'normal_low').lower()
    priority = priority_map.get(priority_str)
    if priority is None:
        return jsonify({"error": f"Invalid priority: {priority_str}"}), 400
    try:
        # get patient ID (f provided, algo gets all prioritization factors automatically)
        patient_id = data.get('patient_id')
        # get payload items
        payload_items = data.get('payload_items', {})
        # filter  items w zero quantity
        if payload_items:
            payload_items = {k: v for k, v in payload_items.items() if v and v > 0}
            if not payload_items:
                payload_items = None
       # no manual input needed, all values  from patient record when patient_id is provided
        request_id = service.create_request(
            requester_id=data['requester_id'],
            requester_name=data['requester_name'],
            requester_location_id=data['requester_location_id'],
            priority=priority,
            description=data.get('description', ''),
            emergency=data.get('emergency', False),
            patient_id=patient_id,
            payload_items=payload_items
        )
        req_status = service.get_request_status(request_id)
        return jsonify({
            "request_id": request_id,
            "status": "created",
            "request_status": req_status.status.value,
            "assigned_drone_id": req_status.assigned_drone_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/request/<int:request_id>', methods=['GET'])
def get_request(request_id):
    """Get request details including energy data if completed"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    req = service.get_request_status(request_id)
    if not req:
        return jsonify({"error": "Request not found"}), 404
    return jsonify(serialize_request(req, include_energy=True))
@app.route('/api/request/<int:request_id>/complete', methods=['POST'])
def complete_request(request_id):
    """Mark request as completed and calculate energy savings"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    data = request.json or {}
    if 'final_location_id' not in data:
        return jsonify({"error": "Missing required field: final_location_id"}), 400
    # optional parameters for energy calculation
    traditional_method = data.get('traditional_method', 'vehicle')
    payload_weight_kg = data.get('payload_weight_kg', 0.5)
    try:
        service.complete_request(
            request_id,data['final_location_id'],traditional_method=traditional_method,payload_weight_kg=payload_weight_kg
        )
        #  energy report for the completed request
        req = service.get_request_status(request_id)
        energy_report = service.get_energy_report(request_id) if req else None
        response = { "status": "completed", "request_id": request_id
        }
        if energy_report:
            response["energy_report"] = energy_report
            response["message"] = f"Request completed. Energy saved: {energy_report['energy_saved_kwh']:.4f} kWh ({energy_report['energy_savings_percentage']:.2f}%)"
        return jsonify(response)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/request/<int:request_id>/cancel', methods=['POST'])
def cancel_request(request_id):
    """Cancel a pending request"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    try:
        service.cancel_request(request_id)
        return jsonify({"status": "cancelled", "request_id": request_id
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/requests/pending', methods=['GET'])
def get_pending_requests():
    """Get all pending requests"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    pending = service.get_all_pending_requests()
    return jsonify({
        "count": len(pending),
        "requests": [
            {"id": req.id, "requester_id": req.requester_id,"requester_name": req.requester_name, "requester_location_id": req.requester_location_id,
                "priority": req.priority.name,"description": req.description,"timestamp": req.timestamp.isoformat(),
                "status": req.status.value
            }
            for req in pending
        ]
    })

@app.route('/api/requests/completed', methods=['GET'])
def get_completed_requests():
    """Get all completed requests with energy data"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    completed = [
        req for req in service.requests.values()
        if req.status == RequestStatus.COMPLETED
    ]
    requests_data = [serialize_request(req, include_energy=True) for req in completed]
    # sort by ID (most recent first if IDs are sequential)
    requests_data.sort(key=lambda x: x["id"], reverse=True)
    return jsonify({"count": len(requests_data), "requests": requests_data
    })
@app.route('/api/requests/all', methods=['GET'])
def get_all_requests():
    """Get all requests (pending, assigned, completed)"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    all_requests = list(service.requests.values())
    requests_data = [serialize_request(req, include_energy=True) for req in all_requests]
    # sort by ID (most recent first)
    requests_data.sort(key=lambda x: x["id"], reverse=True)
    return jsonify({"count": len(requests_data),"requests": requests_data
    })

@app.route('/api/drone/<int:drone_id>', methods=['GET'])
def get_drone(drone_id):
    """Get drone details"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    drone = service.get_drone_status(drone_id)
    if not drone:
        return jsonify({"error": "Drone not found"}), 404
    return jsonify({
        "id": drone.id, "current_location_id": drone.current_location_id,"status": drone.status,"assigned_request_id": drone.assigned_request_id,"emergency_drone": drone.emergency_drone
    })

@app.route('/api/drones/all', methods=['GET'])
def get_all_drones():
    """Get all drones with their current status, locations, request info, and energy/carbon data"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    drones_data = []
    for drone in service.drones.values():
        # get location info
        location = service.graph.nodes.get(drone.current_location_id)
        location_name = location.name if location else f"Location {drone.current_location_id}"
        location_x = location.x if location else 0.0
        location_y = location.y if location else 0.0
        location_floor = location.floor if location else 1
        # get assigned req info if available
        request_info = None
        current_energy_saved = 0.0
        current_carbon_saved = 0.0
        if drone.assigned_request_id:
            req = service.requests.get(drone.assigned_request_id)
            if req:
                request_info = {
                    "id": req.id,"priority": req.priority.name,"priority_display": req.priority.display_name,
                    "description": req.description,"requester_name": req.requester_name,
                    "destination_location_id": req.requester_location_id,"destination_location_name": service.graph.nodes.get(req.requester_location_id).name if service.graph.nodes.get(req.requester_location_id) else f"Location {req.requester_location_id}",
                    "status": req.status.value,"payload_items": req.payload_items,"payload_weight_kg": req.payload_weight_kg
                }
                # get energy data if request is completed
                if req.status == RequestStatus.COMPLETED and req.energy_saved_kwh:
                    current_energy_saved = req.energy_saved_kwh
                    current_carbon_saved = req.co2_saved_kg if hasattr(req, 'co2_saved_kg') and req.co2_saved_kg else 0.0
        # Get flight info if in transit (includes delivery trips and return trips to charging)
        flight_info = service.active_flights.get(drone.id, {})
        # Get route from flight_info first (most accurate), fallback to drone's delivery_route
        # This handles both delivery trips (in active_flights) and return trips (also in active_flights)
        route = []
        if flight_info and flight_info.get('route'):
            route = flight_info.get('route', [])
        elif hasattr(drone, 'delivery_route') and drone.delivery_route:
            route = drone.delivery_route
        
        flight_start_time = flight_info.get('start_time') if flight_info else drone.flight_start_time
        battery_consumed_this_flight = 0.0
        distance_traveled_meters = 0.0
        
        # Calculate battery consumption for drones that are actively moving
        # This includes: assigned (delivery), in_transit (delivery), and returning_to_charging (return trip)
        if drone.status in ["assigned", "in_transit", "returning_to_charging"]:
            try:
                # Use the service method to calculate current battery consumption
                # This works for all statuses: assigned, in_transit, and returning_to_charging
                battery_consumed_this_flight, distance_traveled_meters = service._calculate_current_battery_consumption(drone, datetime.now())
            except Exception as e:
                # Fallback: calculate from route if available
                if route and len(route) >= 2:
                    total_distance = 0.0
                    for i in range(len(route) - 1):
                        try:
                            _, segment_dist = service.graph.find_shortest_path(route[i], route[i + 1])
                            total_distance += segment_dist
                        except Exception:
                            pass
                    distance_traveled_meters = total_distance * 1.0  # Convert graph units to meters
                    # Use appropriate payload weight based on trip type
                    if flight_info.get('is_return_trip', False):
                        payload = 0.0  # No payload on return trip
                    else:
                        payload = flight_info.get('payload_weight', getattr(drone, 'current_payload_weight_kg', 0.5))
                    battery_consumed_this_flight = EnergyCalculator.calculate_drone_energy(distance_traveled_meters, payload)
                else:
                    battery_consumed_this_flight = 0.0
                    distance_traveled_meters = 0.0
         #  start_time to ISO string if it exists
        flight_start_time_iso = None
        if flight_start_time:
            if isinstance(flight_start_time, datetime):
                flight_start_time_iso = flight_start_time.isoformat()
            elif isinstance(flight_start_time, str):
                flight_start_time_iso = flight_start_time
        drone_data = {
            "id": drone.id,"name": f"{'Emergency' if drone.emergency_drone else 'Normal'} Drone {drone.id}",
            "current_location_id": drone.current_location_id,"location_name": location_name,
            "location_x": location_x,"location_y": location_y,
            "location_z": 0.0,  # alt
            "floor": location_floor,"status": drone.status, "assigned_request_id": drone.assigned_request_id,
            "emergency_drone": drone.emergency_drone,"battery_level_kwh": getattr(drone, 'battery_level_kwh', 0.5),
            "battery_capacity_kwh": getattr(drone, 'battery_capacity_kwh', 0.5),
            "battery_percent": round((getattr(drone, 'battery_level_kwh', 0.5) / getattr(drone, 'battery_capacity_kwh', 0.5)) * 100, 1),
            "is_charging": getattr(drone, 'is_charging', False),
            "current_payload_weight_kg": getattr(drone, 'current_payload_weight_kg', 0.0),
            "current_speed_m_per_sec": getattr(drone, 'current_speed_m_per_sec', 2.5),
            "delivery_route": route,"flight_start_time": flight_start_time_iso,  # ISO string for frontend
            "request_info": request_info,
            "current_energy_saved_kwh": round(current_energy_saved, 4),
            "current_carbon_saved_kg": round(current_carbon_saved, 4),
            # battery consumption tracking (Matternet M2: 1.08 Wh/m with 1 kg payload)
            "battery_consumed_this_flight_kwh": round(battery_consumed_this_flight, 4),
            "distance_traveled_this_flight_meters": round(distance_traveled_meters, 2),
            "flight_start_time_datetime": flight_start_time_iso  #  for backwards compatibility
        }
        drones_data.append(drone_data)
    return jsonify({
        "count": len(drones_data),
        "drones": drones_data
    })

@app.route('/api/items', methods=['GET'])
def get_items():
    """ catalog of available items for drone delivery"""
    items_by_category = {}
    for category, items in ItemCatalog.ITEMS.items():
        items_by_category[category] = [
            {"id": item.id,"name": item.name,"weight_kg": item.weight_kg, "description": item.description
            }
            for item in items
        ]
    return jsonify({
        "max_payload_capacity_kg": ItemCatalog.MAX_PAYLOAD_CAPACITY_KG, "categories": items_by_category
    })

@app.route('/api/patients', methods=['GET'])
def get_patients():
    """Get list of all patients in database"""
    patients = get_all_patients()
    patients_data = []
    for patient in patients:
        vitals_data = None
        if patient.current_vitals:
            v = patient.current_vitals
            vitals_data = {
                "heart_rate": v.heart_rate,"blood_pressure_systolic": v.blood_pressure_systolic,
                "blood_pressure_diastolic": v.blood_pressure_diastolic,"temperature": v.temperature,
                "oxygen_saturation": v.oxygen_saturation, "respiratory_rate": v.respiratory_rate,"pain_level": v.pain_level
            }
        patient_data = {
            "patient_id": patient.patient_id,"name": patient.name, "age": patient.age,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "gender": patient.gender, "symptoms": patient.symptoms,"current_vitals": vitals_data,
            "current_status": patient.current_status.value,"reason_for_hospitalization": patient.reason_for_hospitalization,
            "date_of_admission": patient.date_of_admission.isoformat() if patient.date_of_admission else None,
            "expected_discharge_date": patient.expected_discharge_date.isoformat() if patient.expected_discharge_date else None,
            "days_in_hospital": patient.days_in_hospital,"risk_score": round(patient.risk_score, 3),
            "is_critical_vitals": patient.is_critical_vitals,"health_risks": patient.health_risks,
            "lifestyle_risks": patient.lifestyle_risks,"allergies": patient.allergies,
            "family_doctor": patient.family_doctor,"emergency_contact": patient.emergency_contact
        }
        patients_data.append(patient_data)
    return jsonify({"count": len(patients_data),"patients": patients_data
    })

@app.route('/api/patient/<string:patient_id>', methods=['GET'])
def get_patient_detail(patient_id):
    """Get detailed information about a specific patient"""
    patient = get_patient(patient_id)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404
    #  vitals to current time (simulate real-time changes)
    if patient.date_of_admission:
        admission_time = datetime.combine(patient.date_of_admission, datetime.min.time())
        hours_since_admission = (datetime.now() - admission_time).total_seconds() / 3600.0
        if hours_since_admission > 0:
            patient.update_vitals_over_time(hours_since_admission)
    vitals_data = None
    if patient.current_vitals:
        v = patient.current_vitals
        vitals_data = {
            "timestamp": v.timestamp.isoformat(),"heart_rate": v.heart_rate,"blood_pressure_systolic": v.blood_pressure_systolic,"blood_pressure_diastolic": v.blood_pressure_diastolic,
            "temperature": v.temperature,"oxygen_saturation": v.oxygen_saturation,"respiratory_rate": v.respiratory_rate,
            "pain_level": v.pain_level
        }
    patient_data = {
        "patient_id": patient.patient_id, "name": patient.name,"age": patient.age,
        "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        "gender": patient.gender, "address": patient.address, "emergency_contact": patient.emergency_contact,
        "date_of_admission": patient.date_of_admission.isoformat() if patient.date_of_admission else None,
        "expected_discharge_date": patient.expected_discharge_date.isoformat() if patient.expected_discharge_date else None,
        "family_doctor": patient.family_doctor, "insurance_details": patient.insurance_details,
        "symptoms": patient.symptoms, "current_vitals": vitals_data,"current_status": patient.current_status.value,
        "reason_for_hospitalization": patient.reason_for_hospitalization,"days_in_hospital": patient.days_in_hospital,
        "risk_score": round(patient.risk_score, 3), "is_critical_vitals": patient.is_critical_vitals,
        "needs_urgency": patient.needs_urgency,"health_risks": patient.health_risks,"lifestyle_risks": patient.lifestyle_risks,
        "allergies": patient.allergies,"medical_history": patient.medical_history,"past_diagnostics": patient.past_diagnostics,
        "past_medications": patient.past_medications, "immunization_history": patient.immunization_history,
        "treatment_plans": patient.treatment_plans
    }
    return jsonify(patient_data)

@app.route('/api/patient/<string:patient_id>/vitals', methods=['GET'])
def get_patient_vitals_history(patient_id):
    """Get vitals history for a specific patient with live updates"""
    patient = get_patient(patient_id)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404
    #  if we should generate a new vitals reading (every 2 minutes for live updates)
    should_add_new_reading = request.args.get('live', 'false').lower() == 'true'
    last_reading_time = None
    if patient.vitals_history:
        # get the most recent reading
        last_reading = max(patient.vitals_history, key=lambda v: v.timestamp)
        last_reading_time = last_reading.timestamp
    elif patient.current_vitals:
        last_reading_time = patient.current_vitals.timestamp if hasattr(patient.current_vitals, 'timestamp') else None
    #  new reading if requested and enough time has passed (every 2 minutes)
    if should_add_new_reading and patient.date_of_admission:
        now = datetime.now()
        time_since_last = None
        if last_reading_time:
            # last_reading_time should already be a datetime object from Patient class
            if isinstance(last_reading_time, str):
                #  parsing if it's a string (shouldn't happen, but handle it)
                try:
                    last_reading_time = datetime.fromisoformat(last_reading_time.replace('Z', '+00:00').split('.')[0])
                except:
                    last_reading_time = None
            if last_reading_time:
                time_since_last = (now - last_reading_time).total_seconds() / 60.0  # minutes
            else:
                time_since_last = float('inf')
        else:
            time_since_last = float('inf')  # No prev reading, generate one
        #  new reading if more than 2 minutes have passed
        if time_since_last >= 2.0:
            admission_time = datetime.combine(patient.date_of_admission, datetime.min.time())
            hours_since_admission = (now - admission_time).total_seconds() / 3600.0
            if hours_since_admission > 0:
                #  vitals to reflect current time
                patient.update_vitals_over_time(hours_since_admission)
                #  the timestamp is set to now for the latest reading
                if patient.current_vitals and patient.vitals_history:
                    latest = patient.vitals_history[-1] if patient.vitals_history else patient.current_vitals
                    if hasattr(latest, 'timestamp'):
                        latest.timestamp = now
    #  vitals if no history exists but we have current vitals
    if not patient.vitals_history and patient.current_vitals and patient.date_of_admission:
        admission_time = datetime.combine(patient.date_of_admission, datetime.min.time())
        hours_since_admission = (datetime.now() - admission_time).total_seconds() / 3600.0
        if hours_since_admission > 0:
            patient.update_vitals_over_time(hours_since_admission)
    #  history limit from query params (default: last 24 hours)
    hours_back = int(request.args.get('hours', 24))
    #  vitals history to requested time range
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    filtered_history = [
        v for v in patient.vitals_history 
        if v.timestamp >= cutoff_time
    ]
    #  to JSON format
    vitals_history = []
    for v in filtered_history:
        vitals_history.append({
            "timestamp": v.timestamp.isoformat() if hasattr(v.timestamp, 'isoformat') else v.timestamp,
            "heart_rate": v.heart_rate,"blood_pressure_systolic": v.blood_pressure_systolic,
            "blood_pressure_diastolic": v.blood_pressure_diastolic,"temperature": v.temperature,
            "oxygen_saturation": v.oxygen_saturation,"respiratory_rate": v.respiratory_rate, "pain_level": v.pain_level
        })
    #  by timestamp (oldest first for charts)
    vitals_history.sort(key=lambda x: x['timestamp'])
    
    return jsonify({
        "patient_id": patient_id,"patient_name": patient.name, "current_status": patient.current_status.value,
        "vitals_count": len(vitals_history),"hours_back": hours_back,"vitals": vitals_history, "last_update": datetime.now().isoformat()
    })
@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get system statistics including energy savings"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    
    return jsonify(service.get_statistics())
@app.route('/api/request/<int:request_id>/energy', methods=['GET'])
def get_energy_report(request_id):
    """Get detailed energy report for a completed request"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    req = service.get_request_status(request_id)
    if not req:
        return jsonify({"error": "Request not found"}), 404
    if req.status.value != "completed":
        return jsonify({"error": "Request is not completed yet. Energy data available only for completed requests."}), 400
    energy_report = service.get_energy_report(request_id)
    if not energy_report:
        return jsonify({"error": "Energy data not available for this request"}), 404
    return jsonify(energy_report)

@app.route('/api/statistics/path-efficiency', methods=['GET'])
def get_path_efficiency_statistics():
    """Get path efficiency statistics for graphing"""
    if service is None:
        return jsonify({"error": "Service not initialized"}), 400
    #  all completed requests with path efficiency data
    completed_requests = [
        r for r in service.requests.values()
        if r.status == RequestStatus.COMPLETED and r.path_efficiency_percentage is not None
    ]
    #  by completion time (oldest first)
    completed_requests.sort(key=lambda x: x.completed_at if x.completed_at else x.timestamp)
    #  time series data
    efficiency_data = []
    for req in completed_requests:
        efficiency_data.append({
            "request_id": req.id,
            "timestamp": (req.completed_at if req.completed_at else req.timestamp).isoformat(),
            "path_efficiency_percentage": round(req.path_efficiency_percentage, 2),
            "path_efficiency_ratio": round(req.path_efficiency_ratio, 2) if req.path_efficiency_ratio else None,
            "time_saved_seconds": round(req.time_saved_vs_alternative_seconds, 2) if req.time_saved_vs_alternative_seconds else None,
            "chosen_path_distance_meters": round(req.chosen_path_distance_meters, 2) if req.chosen_path_distance_meters else None,
            "alternative_path_distance_meters": round(req.alternative_path_distance_meters, 2) if req.alternative_path_distance_meters else None
        })
    #  statistics
    if efficiency_data:
        avg_efficiency = sum(d["path_efficiency_percentage"] for d in efficiency_data) / len(efficiency_data)
        max_efficiency = max(d["path_efficiency_percentage"] for d in efficiency_data)
        min_efficiency = min(d["path_efficiency_percentage"] for d in efficiency_data)
        total_time_saved = sum(d["time_saved_seconds"] or 0 for d in efficiency_data)
    else:
        avg_efficiency = 0.0
        max_efficiency = 0.0
        min_efficiency = 0.0
        total_time_saved = 0.0
    return jsonify({
        "trips_count": len(efficiency_data), "average_efficiency_percentage": round(avg_efficiency, 2),
        "max_efficiency_percentage": round(max_efficiency, 2), "min_efficiency_percentage": round(min_efficiency, 2),
        "total_time_saved_seconds": round(total_time_saved, 2),"data": efficiency_data
    })

if __name__ == '__main__':
    print("Starting Hospital Drone Logistics API Server...")
    print("" * 60)
    print("Dashboard UI: http://localhost:5001/")
    print("API Documentation:")
    print("  GET  /                      - Main dashboard UI")
    print("  POST /api/initialize        - Initialize the system")
    print("  POST /api/request/create    - Create a new request")
    print("  GET  /api/request/<id>      - Get request details")
    print("  POST /api/request/<id>/complete - Complete a request")
    print("  GET  /api/requests/pending  - Get pending requests")
    print("  GET  /api/requests/completed - Get completed requests with energy data")
    print("  GET  /api/requests/all      - Get all requests")
    print("  GET  /api/statistics        - Get system statistics")
    print("  GET  /api/request/<id>/energy - Get energy report for a request")
    print("=" * 60)
    print("\nMake sure to initialize the service first with POST /api/initialize")
    print("Or visit http://localhost:5001/ to use the dashboard UI")
    app.run(debug=True, port=5001, host='0.0.0.0')
