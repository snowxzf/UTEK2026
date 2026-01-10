# Hospital Drone Logistics System

A backend system for managing drone assignments in a hospital environment, implementing weighted Dijkstra's algorithm for optimal drone routing and priority-based request management.

## Overview

This system is designed for the **University of Toronto Engineering Competition (UTEK) 2026 Programming Competition**. It addresses the challenge of efficient medical logistics by managing drone assignments for hospital staff (doctors and nurses) with priority-based queuing and closest-drone assignment.

## Features

- **Priority-Based Request System**: 
  - Emergency Critical (Priority 4): Seizing patients, cardiac arrest, etc.
  - Emergency Urgent (Priority 3): Severe injuries, critical medication needed
  - Normal High (Priority 2): Important medication, sample transport
  - Normal Low (Priority 1): Food delivery, non-urgent supplies

- **Weighted Dijkstra's Algorithm**: Finds the closest available drone to any requester location

- **Automatic Assignment**: Requests are automatically assigned to the nearest available drone based on priority

- **Energy Savings Tracking**: 
  - Calculates energy consumption per trip (drone vs traditional methods)
  - Tracks cumulative energy savings and CO2 emissions saved
  - Compares against traditional methods (vehicles, electric carts, walking staff)
  - Displays energy reports for each completed request
  - Shows system-wide energy statistics

- **Infinite Drones Assumption**: System tracks drone locations but assumes infinite availability

- **Modular Architecture**: Clean separation of concerns with data models, graph algorithms, and service layer

## Project Structure

```
TEAM_6/
├── models.py          # Data structures (Location, Drone, Request, Priority)
├── graph.py           # HospitalGraph with weighted Dijkstra implementation
├── service.py         # DroneAssignmentService with priority queue logic
├── energy.py          # Energy calculation and savings tracking module
├── main.py            # Entry point, initialization, and example usage
├── api.py             # Optional Flask REST API wrapper
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## Installation

1. Ensure Python 3.7+ is installed

2. Install dependencies (optional, only needed for Flask API):
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage (Command Line)

Run the example script:
```bash
python main.py
```

This will:
- Initialize the hospital system with sample locations and drones
- Create example requests with different priority levels
- Demonstrate automatic drone assignment
- Show system statistics

### Using the REST API

1. Start the API server:
```bash
python api.py
```

2. Initialize the system:
```bash
curl -X POST http://localhost:5000/api/initialize
```

3. Create a request:
```bash
curl -X POST http://localhost:5000/api/request/create \
  -H "Content-Type: application/json" \
  -d '{
    "requester_id": "DR001",
    "requester_name": "Dr. Smith",
    "requester_location_id": 2,
    "priority": "emergency_critical",
    "description": "Patient seizing, need emergency medication",
    "emergency": true
  }'
```

4. Get request status:
```bash
curl http://localhost:5000/api/request/1
```

5. Complete a request:
```bash
curl -X POST http://localhost:5000/api/request/1/complete \
  -H "Content-Type: application/json" \
  -d '{
    "final_location_id": 3,
    "traditional_method": "vehicle",
    "payload_weight_kg": 0.5
  }'
```

6. Get system statistics:
```bash
curl http://localhost:5000/api/statistics
```

## API Endpoints

- `POST /api/initialize` - Initialize the hospital system
- `POST /api/request/create` - Create a new drone request
- `GET /api/request/<id>` - Get request details (includes energy data if completed)
- `POST /api/request/<id>/complete` - Mark request as completed and calculate energy savings
- `GET /api/request/<id>/energy` - Get detailed energy report for a completed request
- `POST /api/request/<id>/cancel` - Cancel a pending request
- `GET /api/requests/pending` - Get all pending requests
- `GET /api/drone/<id>` - Get drone details
- `GET /api/statistics` - Get system statistics (includes total energy savings)
- `GET /api/health` - Health check

## Code Examples

### Creating a Request Programmatically

```python
from main import initialize_hospital_system
from models import Priority

# Initialize system
service = initialize_hospital_system()

# Create emergency request
request_id = service.create_request(
    requester_id="DR001",
    requester_name="Dr. Smith",
    requester_location_id=2,  # ICU
    priority=Priority.EMERGENCY_CRITICAL,
    description="Patient seizing, need emergency medication",
    emergency=True
)

# Check status
req = service.get_request_status(request_id)
print(f"Status: {req.status.value}")
print(f"Assigned Drone: {req.assigned_drone_id}")

# Complete request and get energy savings
service.complete_request(
    request_id,
    final_location_id=3,  # Where drone ends up
    traditional_method="vehicle",  # Compare against vehicle
    payload_weight_kg=0.5  # Weight in kg
)

# Get energy report
energy_report = service.get_energy_report(request_id)
if energy_report:
    print(f"Energy saved: {energy_report['energy_saved_kwh']} kWh")
    print(f"CO2 saved: {energy_report['co2_saved_kg']} kg")
    print(f"Savings percentage: {energy_report['energy_savings_percentage']}%")

# Get system statistics (includes total energy savings)
stats = service.get_statistics()
print(f"Total energy saved: {stats['total_energy_saved_kwh']} kWh")
print(f"Total CO2 saved: {stats['total_co2_saved_kg']} kg")
```

### Adding Custom Hospital Layout

```python
from models import Location
from graph import HospitalGraph
from service import DroneAssignmentService

# Create custom graph
graph = HospitalGraph()

# Add locations
graph.add_location(Location(1, "Emergency Room", 0, 0, 1))
graph.add_location(Location(2, "ICU", 10, 0, 1))
# ... add more locations

# Add pathways (from_id, to_id, weight)
graph.add_pathway(1, 2, 10.0)  # ER to ICU with weight 10.0
# ... add more pathways

# Create service
service = DroneAssignmentService(graph)

# Add drones
service.add_drone(location_id=1)
# ... add more drones
```

## Algorithm Details

### Weighted Dijkstra's Algorithm

The system uses Dijkstra's algorithm with weighted edges to find the shortest path between locations. Weights represent travel time/cost between locations.

**Time Complexity**: O(E log V) where E is the number of edges and V is the number of vertices

**Space Complexity**: O(V) for storing distances and previous nodes

### Priority Queue

Requests are managed using a min-heap priority queue, ensuring:
- Emergency Critical requests are processed first
- Within the same priority level, earlier requests are processed first
- Automatic reassignment when drones become available

## Testing

Run the example to test basic functionality:
```bash
python main.py
```

For more comprehensive testing, you can extend the system with pytest:
```bash
pip install pytest pytest-cov
pytest
```

## Competition Requirements Alignment

This implementation addresses the UTEK 2026 Programming Competition rubric:

- ✅ **Functionality**: Robust request and assignment system with full lifecycle management
- ✅ **Adaptability**: Dynamic response to priority changes, automatic reassignment
- ✅ **Innovation**: Weighted Dijkstra with priority-based queuing for optimal routing
- ✅ **Code Quality**: 
  - **Readability**: Well-indented, clearly named variables, comprehensive comments
  - **Modularity**: Separated into logical modules (models, graph, service, API)
  - **Efficiency**: Optimized Dijkstra implementation with early termination
- ✅ **Relevance**: Directly addresses hospital logistics with emergency handling

## Energy Savings Output Locations

Energy savings data is available in multiple places:

### 1. **Request Details** (After Completion)
- Accessed via `service.get_request_status(request_id)` 
- Fields: `energy_saved_kwh`, `distance_traveled_meters`, `drone_energy_kwh`, `traditional_energy_kwh`, `co2_saved_kg`

### 2. **Energy Report** (Detailed Report)
- Accessed via `service.get_energy_report(request_id)`
- Returns formatted dictionary with all energy metrics including:
  - Distance in meters and kilometers
  - Drone energy consumption
  - Traditional method energy consumption
  - Energy saved (kWh and percentage)
  - CO2 emissions saved

### 3. **System Statistics**
- Accessed via `service.get_statistics()`
- Includes:
  - `total_energy_saved_kwh`: Cumulative energy savings across all trips
  - `total_co2_saved_kg`: Cumulative CO2 savings
  - `average_energy_saved_per_trip_kwh`: Average savings per trip
  - `trips_with_energy_data`: Number of completed trips with energy data

### 4. **API Endpoints**
- `GET /api/request/<id>`: Includes energy data in response if request is completed
- `GET /api/request/<id>/energy`: Dedicated endpoint for detailed energy report
- `GET /api/statistics`: System-wide statistics including total energy savings
- `POST /api/request/<id>/complete`: Response includes energy report

### 5. **Console Output** (main.py)
- Example usage automatically displays energy savings when completing requests
- Shows formatted energy report with all metrics

## Energy Calculation Details

The system calculates energy savings by comparing:
- **Drone Energy**: Based on distance traveled and payload weight
  - Base energy for takeoff/landing
  - Distance-based energy consumption (varies with payload)
  
- **Traditional Methods** (configurable):
  - **Vehicle**: Gas-powered hospital carts/vehicles
  - **Electric Cart**: Battery-powered carts
  - **Walking**: Staff retrieval (human energy equivalent)

- **CO2 Emissions**: Calculated from energy saved using grid emissions factor (0.4 kg CO2/kWh)

## Future Enhancements

Potential improvements for production use:
- Multi-floor support with elevator routing
- Time-based metrics and analytics
- Request cancellation with drone reassignment
- Drone battery management
- Integration with hospital management systems
- Real-time location tracking
- Path visualization
- Customizable energy calculation constants
- Historical energy reports and analytics

## License

This project is created for the UTEK 2026 Programming Competition.

## Authors

Team 6 - University of Toronto Engineering Competition 2026
