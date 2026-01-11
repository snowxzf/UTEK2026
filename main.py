"""
Main entry point and initialization for the hospital drone logistics system
"""
from models import Location, Priority
from graph import HospitalGraph
from service import DroneAssignmentService
def initialize_hospital_system() -> DroneAssignmentService:
    """
    initalize the hospital system with sample locations and drones
    demonstrates shows the system setup
    """
    graph = HospitalGraph()
    # add hospital locations (example floor plan)
    # Scaled to 186m width (scale factor 186/180 = 1.0333...) - hallways represented by pathways
    locations = [
        Location(1, "Emergency Room", 0, 0, 1),
        Location(2, "ICU", 62, 0, 1),
        Location(3, "Pharmacy", 124, 0, 1),
        Location(4, "Lab", 186, 0, 1),
        Location(5, "Cafeteria", 0, 60, 1),
        Location(6, "Ward A", 62, 60, 1),
        Location(7, "Ward B", 124, 60, 1),
        Location(8, "Surgery", 186, 60, 1),
        # Additional locations for more complex routing
        Location(19, "Radiology", 31, 30, 1),
        Location(20, "Physical Therapy", 93, 30, 1),
        Location(21, "Cardiology", 155, 30, 1),
        Location(22, "Oncology", 31, 90, 1),
        Location(23, "Orthopedics", 93, 90, 1),
        Location(24, "Neurology", 155, 90, 1),
    ]
    # add charging stations between each room (in hallways)
    # chargings stations are placed at midpoints between adjacent rooms in hallways
    charging_stations = [
        Location(9, "Charging Station 1-2", 31, 0, 1),      #  ER and ICU (hallway)
        Location(10, "Charging Station 2-3", 93, 0, 1),    #  ICU and Pharmacy (hallway)
        Location(11, "Charging Station 3-4", 155, 0, 1),    #  Pharmacy and Lab (hallway)
        Location(12, "Charging Station 1-5", 0, 30, 1),     #  ER and Cafeteria (hallway)
        Location(13, "Charging Station 2-6", 62, 30, 1),    #  ICU and Ward A (hallway)
        Location(14, "Charging Station 3-7", 124, 30, 1),    #  Pharmacy and Ward B (hallway)
        Location(15, "Charging Station 4-8", 186, 30, 1),    #  Lab and Surgery (hallway)
        Location(16, "Charging Station 5-6", 31, 60, 1),    # Cafeteria and Ward A (hallway)
        Location(17, "Charging Station 6-7", 93, 60, 1),   #  Ward A and Ward B (hallway)
        Location(18, "Charging Station 7-8", 155, 60, 1),   #  Ward B and Surgery (hallway)
        # Additional charging stations for new locations
        Location(25, "Charging Station 19-20", 62, 30, 1),   # Radiology and Physical Therapy
        Location(26, "Charging Station 20-21", 124, 30, 1),  # Physical Therapy and Cardiology
        Location(27, "Charging Station 22-23", 62, 90, 1),   # Oncology and Orthopedics
        Location(28, "Charging Station 23-24", 124, 90, 1),  # Orthopedics and Neurology
    ]
    all_locations = locations + charging_stations
    for loc in all_locations:
        graph.add_location(loc)
    # add pathways between rooms (hallways - pathways represent hallways/corridors)
    # Scaled to 186m width (scale factor 186/180 = 1.0333...)
    pathways = [
        (1, 2, 62.0),  # ER to ICU (via hallway)
        (2, 3, 62.0),  # ICU to Pharmacy (via hallway)
        (3, 4, 62.0),  # Pharmacy to Lab (via hallway)
        (1, 5, 84.9),  # ER to Cafeteria (diagonal hallway)
        (2, 6, 62.0),  # ICU to Ward A (via hallway)
        (3, 7, 62.0),  # Pharmacy to Ward B (via hallway)
        (4, 8, 62.0),  # Lab to Surgery (via hallway)
        (5, 6, 62.0),  # Cafeteria to Ward A (via hallway)
        (6, 7, 62.0),  # Ward A to Ward B (via hallway)
        (7, 8, 62.0),  # Ward B to Surgery (via hallway)
        # Additional pathways connecting new locations
        (1, 19, 31.0),  # ER to Radiology
        (19, 2, 31.0),  # Radiology to ICU
        (2, 20, 31.0),  # ICU to Physical Therapy
        (20, 3, 31.0),  # Physical Therapy to Pharmacy
        (3, 21, 31.0),  # Pharmacy to Cardiology
        (21, 4, 31.0),  # Cardiology to Lab
        (5, 22, 31.0),  # Cafeteria to Oncology
        (22, 6, 31.0),  # Oncology to Ward A
        (6, 23, 31.0),  # Ward A to Orthopedics
        (23, 7, 31.0),  # Orthopedics to Ward B
        (7, 24, 31.0),  # Ward B to Neurology
        (24, 8, 31.0),  # Neurology to Surgery
        # Cross-connections for more routing options
        (19, 22, 31.0),  # Radiology to Oncology
        (20, 23, 31.0),  # Physical Therapy to Orthopedics
        (21, 24, 31.0),  # Cardiology to Neurology
    ]
    charging_pathways = [
        # Horizontal pathways with charging stations (hallways)
        (1, 9, 31.0), (9, 2, 31.0),    # ER -> CS1-2 -> ICU (hallway)
        (2, 10, 31.0), (10, 3, 31.0),  # ICU -> CS2-3 -> Pharmacy (hallway)
        (3, 11, 31.0), (11, 4, 31.0),  # pharmancy -> CS3-4 -> Lab (hallway)
        # vertical pathways with charging stations (hallways)
        (1, 12, 30.0), (12, 5, 30.0),  # ER -> CS1-5 -> Cafeteria (hallway)
        (2, 13, 31.0), (13, 6, 31.0),  # ICU -> CS2-6 -> Ward A (hallway)
        (3, 14, 31.0), (14, 7, 31.0),  # Pharmacy -> CS3-7 -> Ward B (hallway)
        (4, 15, 30.0), (15, 8, 30.0),  # Lab -> CS4-8 -> Surgery (hallway)
        # bottom row pathways with charging stations (hallways)
        (5, 16, 31.0), (16, 6, 31.0),  # Cafeteria -> CS5-6 -> Ward A (hallway)
        (6, 17, 31.0), (17, 7, 31.0),  # Ward A -> CS6-7 -> Ward B (hallway)
        (7, 18, 31.0), (18, 8, 31.0),  # Ward B -> CS7-8 -> Surgery (hallway)
    ]
    # add all pathways (original + charging station pathways)
    for from_id, to_id, weight in pathways:
        graph.add_pathway(from_id, to_id, weight)
    for from_id, to_id, weight in charging_pathways:
        graph.add_pathway(from_id, to_id, weight)
    # create service
    service = DroneAssignmentService(graph)
    # set charging station locations (all charging station IDs)
    charging_station_ids = [loc.id for loc in charging_stations]
    service.CHARGING_STATION_LOCATIONS = charging_station_ids
    # Find leftmost and rightmost nodes (for drone starting positions)
    # Leftmost: Location 1 (ER) at x=0, y=0
    # Rightmost: Location 4 (Lab) at x=186, y=0
    leftmost_location_id = 1  # Emergency Room (x=0)
    rightmost_location_id = 4  # Lab (x=186)
    
    # emergency drones: Half at leftmost node, half at rightmost node
    emergency_drone_count = 6
    for i in range(emergency_drone_count):
        # First half at leftmost, second half at rightmost
        if i < emergency_drone_count // 2:
            start_location_id = leftmost_location_id
        else:
            start_location_id = rightmost_location_id
        service.add_drone(start_location_id, emergency_drone=True)
        # mark drone as available
        drone = service.drones[service.next_drone_id - 1]
        drone.status = "available"
        drone.is_charging = False  # Not at charging station, just available
        drone.battery_level_kwh = drone.battery_capacity_kwh * 0.8  # Start at 80% charge
    # normal drones: Half at leftmost node, half at rightmost node
    normal_drone_count = 14
    for i in range(normal_drone_count):
        # First half at leftmost, second half at rightmost
        if i < normal_drone_count // 2:
            start_location_id = leftmost_location_id
        else:
            start_location_id = rightmost_location_id
        service.add_drone(start_location_id, emergency_drone=False)
        # mark drone as available
        drone = service.drones[service.next_drone_id - 1]
        drone.status = "available"
        drone.is_charging = False  # Not at charging station, just available
        drone.battery_level_kwh = drone.battery_capacity_kwh * 0.8  # Start at 80% charge
    # total: 6 emergency drones + 14 normal drones = 20 drones
    return service

def example_usage():
    """ex usage of the system"""
    # initalize system
    service = initialize_hospital_system()
    print("hospital Drone log syst \n")
    # ex 1: CTAS I - Resuscitation (cardiac arrest)
    print("ex 1: CTAS I - Resuscitation")
    request1 = service.create_request(
        requester_id="DR001",requester_name="Dr. Smith",requester_location_id=2,  priority=Priority.CTAS_I,description="Cardiac arrest, need emergency medication from pharmacy",
        emergency=True
    )
    req1_status = service.get_request_status(request1)
    print(f"  Request ID: {request1}")
    print(f" status: {req1_status.status.value}")
    print(f"  Priority: {req1_status.priority.display_name}")
    print(f" targ Response Time: {req1_status.target_response_time_minutes} minutes")
    print(f" assigned Drone: {req1_status.assigned_drone_id}")
    print()
    # ex 2: CTAS V - Non-urgent (food delivery)
    print("Example 2: CTAS V - Non-urgent")
    request2 = service.create_request(
        requester_id="NU001",requester_name="Nurse Johnson",
        requester_location_id=6,  # Ward A
        priority=Priority.CTAS_V,description="patient requesting food from cafeteria",
        emergency=False
    )
    req2_status = service.get_request_status(request2)
    print(f" req ID: {request2}")
    print(f"  Status: {req2_status.status.value}")
    print(f" priiortuy: {req2_status.priority.display_name}")
    print(f" Target Response Time: {req2_status.target_response_time_minutes} minutes")
    print(f"  assigned Drone: {req2_status.assigned_drone_id}")
    print()
    # ex 3: CTAS II - Emergent (severe injury)
    print("Example 3: CTAS II - Emergent")
    request3 = service.create_request(
        requester_id="DR002",requester_name="Dr. Williams",
        requester_location_id=1,  # Emergency Room
        priority=Priority.CTAS_II,description="severe head injury, need blood samples from lab",
        emergency=True
    )
    req3_status = service.get_request_status(request3)
    print(f" Request ID: {request3}")
    print(f"  status: {req3_status.status.value}")
    print(f" Priority: {req3_status.priority.name}")
    print(f" assigned Drone: {req3_status.assigned_drone_id}")
    print()
    # get system statistics
    print(" System ststas")
    stats = service.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    # ex: Complete a request and show energy savings
    print("ex 4: Completing req and calc energy savings")
    service.complete_request(
        request1,
        3,  # drone ends up at pharmacy
        traditional_method="vehicle",  # comp against traditional vehicle
        payload_weight_kg=0.5  # typical medication weight
    )
    req1_status = service.get_request_status(request1)
    print(f"  req {request1} status: {req1_status.status.value}")
    print(f"  drone returned to location: {service.get_drone_status(req1_status.assigned_drone_id).current_location_id}")
    # display energy savings
    if req1_status.energy_saved_kwh is not None:
        energy_report = service.get_energy_report(request1)
        if energy_report:
            print(f"\n  =energy savings report for req {request1} ")
            print(f"  distance traveled: {energy_report['distance_km']} km ({energy_report['distance_meters']} m)")
            print(f"  drone energy consumed: {energy_report['drone_energy_kwh']} kWh")
            print(f"  trad method energy: {energy_report['traditional_energy_kwh']} kWh")
            print(f"  energy saved: {energy_report['energy_saved_kwh']} kWh ({energy_report['energy_savings_percentage']}%)")
            if energy_report.get('co2_saved_kg'):
                print(f"  CO2 emissions saved: {energy_report['co2_saved_kg']} kg")
    print()
    # final statistics including energy totals
    print("Final System Statistics (Including Energy Savings) ")
    stats = service.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
if __name__ == "__main__":
    example_usage()
