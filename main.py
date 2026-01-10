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
    locations = [
        Location(1, "Emergency Room", 0, 0, 1),
        Location(2, "ICU", 10, 0, 1),
        Location(3, "Pharmacy", 20, 0, 1),
        Location(4, "Lab", 30, 0, 1),
        Location(5, "Cafeteria", 0, 10, 1),
        Location(6, "Ward A", 10, 10, 1),
        Location(7, "Ward B", 20, 10, 1),
        Location(8, "Surgery", 30, 10, 1),
    ]
    # add charging stations between each room
    # chargings stations are placed at midpoints between adjacent rooms
    charging_stations = [
        Location(9, "Charging Station 1-2", 5, 0, 1),      #  ER and ICU
        Location(10, "Charging Station 2-3", 15, 0, 1),    #  ICU and Pharmacy
        Location(11, "Charging Station 3-4", 25, 0, 1),    #  Pharmacy and Lab
        Location(12, "Charging Station 1-5", 0, 5, 1),     #  ER and Cafeteria
        Location(13, "Charging Station 2-6", 10, 5, 1),    #  ICU and Ward A
        Location(14, "Charging Station 3-7", 20, 5, 1),    #  Pharmacy and Ward B
        Location(15, "Charging Station 4-8", 30, 5, 1),    #  Lab and Surgery
        Location(16, "Charging Station 5-6", 5, 10, 1),    # Cafeteria and Ward A
        Location(17, "Charging Station 6-7", 15, 10, 1),   #  Ward A and Ward B
        Location(18, "Charging Station 7-8", 25, 10, 1),   #  Ward B and Surgery
    ]
    all_locations = locations + charging_stations
    for loc in all_locations:
        graph.add_location(loc)
    # add pathways between rooms (original pathways)
    pathways = [
        (1, 2, 10.0),  # ER to ICU
        (2, 3, 10.0),  # ICU to Pharmacy
        (3, 4, 10.0),  # Pharmacy to Lab
        (1, 5, 14.1),  # ER to Cafeteria (diagonal)
        (2, 6, 10.0),  # ICU to Ward A
        (3, 7, 10.0),  # Pharmacy to Ward B
        (4, 8, 10.0),  # Lab to Surgery
        (5, 6, 10.0),  # Cafeteria to Ward A
        (6, 7, 10.0),  # Ward A to Ward B
        (7, 8, 10.0),  # Ward B to Surgery
    ]
    charging_pathways = [
        # Horizontal pathways with charging stations
        (1, 9, 5.0), (9, 2, 5.0),    # ER -> CS1-2 -> ICU
        (2, 10, 5.0), (10, 3, 5.0),  # ICU -> CS2-3 -> Pharmacy
        (3, 11, 5.0), (11, 4, 5.0),  # pharmancy -> CS3-4 -> Lab
        # vertical pathways with charging stations
        (1, 12, 5.0), (12, 5, 5.0),  # ER -> CS1-5 -> Cafeteria
        (2, 13, 5.0), (13, 6, 5.0),  # ICU -> CS2-6 -> Ward A
        (3, 14, 5.0), (14, 7, 5.0),  # Pharmacy -> CS3-7 -> Ward B
        (4, 15, 5.0), (15, 8, 5.0),  # Lab -> CS4-8 -> Surgery
        # bottom row pathways with charging stations
        (5, 16, 5.0), (16, 6, 5.0),  # Cafeteria -> CS5-6 -> Ward A
        (6, 17, 5.0), (17, 7, 5.0),  # Ward A -> CS6-7 -> Ward B
        (7, 18, 5.0), (18, 8, 5.0),  # Ward B -> CS7-8 -> Surgery
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
    # initalize drones at various locations,reserve some drones specifically for emergency requests
    emergency_drone_locations = [1, 2, 1, 2, 8, 1]  # ER, ICU, Surgery
    for loc_id in emergency_drone_locations:
        service.add_drone(loc_id, emergency_drone=True)
    #  normal drones (for regular requests)
    normal_drone_count = 14
    for i in range(normal_drone_count):
        loc_id = locations[i % len(locations)].id
        service.add_drone(loc_id, emergency_drone=False)
    # total: 6 emergency drones + 14 normal drones = 20 drones
    return service

def example_usage():
    """ex usage of the system"""
    # initalize system
    service = initialize_hospital_system()
    print("hospital Drone log syst \n")
    # Example 1: CTAS I - Resuscitation (cardiac arrest)
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
