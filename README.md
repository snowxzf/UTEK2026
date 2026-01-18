# Hospital Drone Logistics System

A backend system for managing drone assignments in a hospital environment, implementing weighted Dijkstra's algorithm for optimal drone routing and priority-based request management.

## Overview

This system is designed for the **University of Toronto Engineering Competition (UTEK) 2026 Programming Competition**. It addresses the challenge of efficient medical logistics by managing drone assignments for hospital staff (doctors and nurses) with priority-based queuing and closest-drone assignment.

Demo: https://drive.google.com/file/d/1g4pHR3_r5QDC2kCOILnMMqGwaZwHQfoD/view?usp=sharing

## Features

- **Priority-Based Request System**: 
  - Emergency Critical (Priority 4): Seizing patients, cardiac arrest, etc.
  - Emergency Urgent (Priority 3): Severe injuries, critical medication needed
  - Normal High (Priority 2): Important medication, sample transport
  - Normal Low (Priority 1): Food delivery, non-urgent supplies

- **Advanced Pathfinding**: 
  - Weighted Dijkstra's Algorithm for shortest path calculation
  - RRT (Rapidly-exploring Random Tree) path planning for collision avoidance
  - Combined RRT+Dijkstra algorithm for optimal routing with dynamic obstacle avoidance

- **3-Lane Traffic System**: 
  - Each hallway supports 3 drones side-by-side (3m total width, 1m per lane)
  - Priority-based lane assignment (emergency/high-priority drones use middle lane)
  - Yielding system where lower-priority drones yield to higher-priority ones

- **Automatic Assignment**: Requests are automatically assigned to the nearest available drone based on proximity and priority

- **Expanded Hospital Layout**: 
  - 14 main locations (IDs 1-8, 19-24) including Emergency Room, ICU, Pharmacy, Lab, Surgery, Radiology, Cardiology, etc.
  - 20 charging stations (IDs 9-18, 25-28) strategically placed in hallways
  - Complex pathway network for realistic routing scenarios

- **Drone Distribution**: 
  - 6 emergency drones and 14 normal drones (20 total)
  - Half of each type start at leftmost node (Emergency Room), half at rightmost node (Lab)
  - Closest-drone assignment based on shortest path distance

- **Energy Savings Tracking**: 
  - Calculates energy consumption per trip (drone vs traditional methods)
  - Tracks cumulative energy savings and CO2 emissions saved
  - Compares against traditional methods (vehicles, electric carts, walking staff)
  - Displays energy reports for each completed request
  - Shows system-wide energy statistics
  - Path efficiency comparison (actual algorithm vs next quickest path)

- **Real-Time Visualizations**:
  - Multi-drone traffic system visualization showing priority-based lane usage
  - Individual path visualization with actual hospital hallways displayed
  - Graph structure visualization showing all pathways and locations

- **Modular Architecture**: Clean separation of concerns with data models, graph algorithms, and service layer

## Project Structure

```
TEAM_6/
├── models.py              # Data structures (Location, Drone, Request, Priority, Patient)
├── graph.py               # HospitalGraph with weighted Dijkstra implementation
├── service.py             # DroneAssignmentService with priority queue and RRT path planning
├── energy.py              # Energy calculation and savings tracking module
├── rrt_pathfinding.py     # RRT path planner with 3-lane traffic system and collision avoidance
├── items.py               # Item catalog and payload management for drone deliveries
├── patients.py            # Patient database and vitals management
├── main.py                # Entry point, initialization (14 locations, 20 charging stations, 20 drones)
├── api.py                 # Flask REST API server for frontend integration
├── templates/
│   ├── index.html         # Web dashboard UI with visualizations
│   ├── image.png          # Hospital map image
│   └── image2.png         # Additional hospital visualization
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

### File Descriptions

- **models.py**: Defines core data structures including `Location`, `Drone`, `Request`, `Priority`, `RequestStatus`, and `Patient` classes. Implements Vital Priority System scoring for patient prioritization.

- **graph.py**: Implements `HospitalGraph` class with weighted Dijkstra's algorithm for finding shortest paths between locations. Manages hospital layout, pathways, and location relationships.

- **service.py**: Core business logic for `DroneAssignmentService`. Handles request creation, priority queue management, drone assignment, route planning with RRT, energy tracking, and request completion. Implements multi-criteria prioritization based on CTAS levels and Vital Priority Scores.

- **energy.py**: `EnergyCalculator` class for calculating drone energy consumption, comparing against traditional methods (vehicle, electric cart, walking), and computing CO₂ emissions saved. Based on Matternet M2 drone specifications.

- **rrt_pathfinding.py**: Implements RRT (Rapidly-exploring Random Tree) path planning algorithm for collision-avoiding drone paths. Supports 3-lane traffic system, priority-based lane assignment, yielding logic, obstacle avoidance, and multi-drone coordination. Combined with Dijkstra for optimal pathfinding.

- **items.py**: `ItemCatalog` class managing available items for drone delivery. Handles item categorization, weight calculations, payload validation, and splitting large payloads across multiple requests.

- **patients.py**: Patient database management with vitals tracking. Handles patient data, current vitals, health risks, lifestyle risks, and automatic vitals updates over time. Supports real-time vitals history.

- **main.py**: Initialization script that sets up hospital graph, locations, pathways, charging stations, and drones. Includes example usage demonstrating the system with different priority levels.

- **api.py**: Flask REST API server providing endpoints for request management, drone tracking, statistics, patient data, and energy reports. Serves the web dashboard UI and provides API access for external integrations.

Note: map.js and map.css have been removed. Hospital layout visualization is now integrated directly into templates/index.html using SVG.

- **templates/index.html**: Main web dashboard UI template. Includes request management, drone tracking, system statistics, patient selection, payload management, real-time updates, multi-drone traffic visualization, individual path visualization with hospital layout, path efficiency comparison charts, and environmental impact analysis. Location IDs: 1-28 (14 locations + 20 charging stations).

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
curl -X POST http://localhost:5001/api/initialize
```

3. Create a request:
```bash
curl -X POST http://localhost:5001/api/request/create \
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
curl http://localhost:5001/api/request/1
```

5. Complete a request:
```bash
curl -X POST http://localhost:5001/api/request/1/complete \
  -H "Content-Type: application/json" \
  -d '{
    "final_location_id": 3,
    "traditional_method": "vehicle",
    "payload_weight_kg": 0.5
  }'
```

6. Get system statistics:
```bash
curl http://localhost:5001/api/statistics
```

7. Access the web dashboard:
```bash
# Open in browser:
http://localhost:5001/
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
- `GET /api/drones/all` - Get all drones with their current status and routes
- `GET /api/statistics` - Get system statistics (includes total energy savings)
- `GET /api/graph/structure` - Get hospital graph structure (locations, pathways, bounds)
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

## UI Development Status

**Current State**: The web dashboard UI (`templates/index.html`) includes core functionality for request management, drone tracking, system statistics, and patient data visualization. The dashboard provides real-time updates and displays completed request details including energy savings reports.

**Planned After Presentation**:
- **Energy Savings Graph**: Add a comprehensive graph/chart visualization showing total energy savings over time, including:
  - Time-series chart of cumulative energy savings (kWh)
  - CO₂ emissions savings visualization
  - Per-trip energy savings breakdown
  - Comparison graphs showing drone efficiency vs traditional methods
- **Enhanced UI Features**: Improve the overall user experience with additional visualizations and analytics dashboards

Note: While the backend fully supports energy tracking and reporting (accessible via API endpoints and programmatic access), the visual graph component is planned for future implementation after the presentation.

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
- Energy savings graph visualization (planned post-presentation)

## License

This project is created for the UTEK 2026 Programming Competition. 

## Authors

Team 6 - University of Toronto Engineering Competition 2026
