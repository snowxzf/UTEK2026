# Hackathon Guide: api.py, service.py, and models.py

## 📋 Overview

You're responsible for explaining:
- **models.py** - Data structures and classes
- **service.py** - Core business logic and algorithms
- **api.py** - REST API endpoints and frontend integration

---

## 1. MODELS.PY - Data Structures

### Purpose
Defines all the core data structures (classes) used throughout the system.

### Key Classes

#### **Priority Enum**
```python
class Priority(Enum):
    CTAS_I = 1      # Emergency Critical (cardiac arrest, seizing)
    CTAS_II = 2     # Emergency Urgent (severe injuries)
    CTAS_III = 3    # Normal High (important medication)
    CTAS_IV = 4     # Normal Low (food delivery)
    CTAS_V = 5      # Non-urgent
```
**Key Feature**: CTAS (Canadian Triage and Acuity Scale) - medical priority system

#### **Request Class**
Represents a delivery request from hospital staff.

**Key Fields:**
- `id`, `requester_id`, `requester_name`
- `requester_location_id` - Where the request is coming from
- `priority` - CTAS priority level
- `emergency` - Boolean flag
- `status` - PENDING, ASSIGNED, IN_TRANSIT, COMPLETED, CANCELLED
- `assigned_drone_id` - Which drone is handling this
- `energy_saved_kwh`, `co2_saved_kg` - Energy metrics (after completion)

**Key Feature**: Tracks full lifecycle from creation to completion with energy savings

#### **Drone Class**
Represents a physical drone in the system.

**Key Fields:**
- `id`, `current_location_id` - Where the drone is
- `status` - available, assigned, in_transit, charging
- `emergency_drone` - Boolean (emergency vs normal drone)
- `battery_level_kwh` - Current battery
- `delivery_route` - List of location IDs for current route
- `current_speed_m_per_sec` - Speed based on priority

**Key Feature**: Two types of drones (emergency vs normal), battery management

#### **Location Class**
Represents a physical location in the hospital.

**Key Fields:**
- `id`, `name` - e.g., "Emergency Room", "ICU"
- `x`, `y` - Coordinates (0-186m width, 0-60m height)
- `floor` - Floor number

**Key Feature**: Used to build the graph structure

#### **RequestStatus Enum**
```python
PENDING → ASSIGNED → IN_TRANSIT → COMPLETED
```
**Key Feature**: State machine for request lifecycle

#### **Patient Class** (for prioritization)
- Patient vitals, health risks
- Used to calculate priority scores
- **Key Feature**: Vital Priority System - automatically calculates priority based on patient condition

---

## 2. SERVICE.PY - Core Business Logic

### Purpose
The heart of the system - manages requests, drone assignments, routing, and energy calculations.

### Main Class: `DroneAssignmentService`

#### **Initialization**
```python
def __init__(self, hospital_graph: HospitalGraph):
    self.graph = hospital_graph  # Hospital layout
    self.requests: Dict[int, Request] = {}  # All requests
    self.drones: Dict[int, Drone] = {}  # All drones
    self.priority_queue = []  # Min-heap for priority queue
    self.active_flights: Dict[int, dict] = {}  # Active drone flights
    self.rrt_planner = RRTPathPlanner(...)  # RRT path planner
```

### Key Features to Know:

#### **1. Priority Queue System**
- Uses **min-heap** (Python's `heapq`)
- Lower priority value = higher priority (CTAS I = 1 is most urgent)
- Automatically processes highest priority requests first
- **Key Feature**: Ensures emergency requests are always handled first

#### **2. Closest Drone Assignment**
```python
def _assign_drone_to_request(self, request: Request) -> bool:
    # STEP 1: Use Dijkstra to find closest drone location
    closest_loc_id = self.graph.find_closest_drone_location(
        request.requester_location_id, available_locations
    )
    
    # STEP 2: Use RRT to plan path with collision avoidance
    path = self.rrt_planner.plan_path_with_traffic_rules(...)
    
    # STEP 3: Fallback to Dijkstra if RRT fails
    if len(path) < 2:
        path, _ = self.graph.find_shortest_path(...)
```
**Key Feature**: Combines Dijkstra (optimal assignment) + RRT (dynamic avoidance)

#### **3. Request Lifecycle Management**
```python
create_request() → _assign_drone_to_request() → 
update_drone_positions() → complete_request()
```
**Key Feature**: Full lifecycle tracking with automatic assignment

#### **4. Energy Savings Calculation**
- Calculates drone energy consumption
- Compares against traditional methods (vehicle, electric cart, walking)
- Tracks cumulative savings (`total_energy_saved_kwh`, `total_co2_saved_kg`)
- **Key Feature**: Real-time environmental impact tracking

#### **5. Multi-Stop Optimization**
- Drones can intercept additional requests while in flight
- Evaluates if accepting a second request is energy-efficient
- **Key Feature**: Dynamic route optimization for multiple deliveries

#### **6. Battery Management**
- Tracks battery levels for each drone
- Sends drones to charging stations when battery is low
- **Key Feature**: Prevents drones from running out of battery mid-flight

#### **7. Path Efficiency Comparison**
- Compares actual path (RRT+Dijkstra) vs next quickest path
- Calculates time and distance savings
- **Key Feature**: Demonstrates algorithm efficiency

#### **8. Priority-Based Speed**
```python
EMERGENCY_SPEED_M_PER_SEC = 4.0
NORMAL_SPEED_M_PER_SEC = 2.5
LOW_PRIORITY_SPEED_M_PER_SEC = 1.5
```
**Key Feature**: Emergency drones move faster

#### **9. Material Pickup Time**
- 10 seconds per item for material pickup
- Added to total travel time
- **Key Feature**: Realistic time accounting

#### **10. Thread Safety**
- Uses `threading.Lock()` for concurrent access
- **Key Feature**: Safe for multi-threaded API requests

### Key Methods:

1. **`create_request()`** - Creates new request, automatically assigns drone
2. **`_assign_drone_to_request()`** - Core assignment logic (Dijkstra + RRT)
3. **`complete_request()`** - Marks request complete, calculates energy savings
4. **`get_request_status()`** - Returns current request status
5. **`get_statistics()`** - System-wide stats (total energy saved, etc.)
6. **`update_drone_positions()`** - Updates drone locations during flight
7. **`_check_and_intercept_request()`** - Multi-stop optimization
8. **`get_energy_report()`** - Detailed energy savings report

---

## 3. API.PY - REST API Server

### Purpose
Flask REST API that connects frontend to backend service layer.

### Key Features:

#### **1. Flask Server**
```python
app = Flask(__name__)
app.run(host='0.0.0.0', port=5001, debug=True)
```
- Serves web dashboard at `http://localhost:5001/`
- REST API endpoints at `/api/*`

#### **2. System Initialization**
```python
POST /api/initialize
```
- Creates hospital graph with all locations
- Initializes 20 drones (6 emergency, 14 normal)
- Sets up charging stations
- **Key Feature**: One endpoint to set up entire system

#### **3. Request Management Endpoints**

**Create Request:**
```python
POST /api/request/create
Body: {
    "requester_id": "DR001",
    "requester_location_id": 2,
    "priority": "emergency_critical",
    "emergency": true,
    ...
}
```
**Key Feature**: Automatically assigns closest drone

**Get Request Status:**
```python
GET /api/request/<id>
Returns: Full request details including energy data if completed
```

**Complete Request:**
```python
POST /api/request/<id>/complete
Body: {
    "final_location_id": 3,
    "traditional_method": "vehicle",
    "payload_weight_kg": 0.5
}
```
**Key Feature**: Calculates and stores energy savings

**Get Energy Report:**
```python
GET /api/request/<id>/energy
Returns: Detailed energy report (distance, energy saved, CO2, etc.)
```

#### **4. Drone Management Endpoints**

**Get All Drones:**
```python
GET /api/drones/all
Returns: All drones with current status, location, route, priority
```
**Key Feature**: Used by frontend for multi-drone visualization

**Get Single Drone:**
```python
GET /api/drone/<id>
Returns: Detailed drone info including assigned request
```

#### **5. Statistics Endpoints**

**System Statistics:**
```python
GET /api/statistics
Returns: {
    "total_requests": ...,
    "total_energy_saved_kwh": ...,
    "total_co2_saved_kg": ...,
    "average_energy_saved_per_trip_kwh": ...
}
```
**Key Feature**: Cumulative environmental impact tracking

**Path Efficiency Statistics:**
```python
GET /api/statistics/path-efficiency
Returns: Comparison data (actual path vs alternative)
```
**Key Feature**: Shows algorithm efficiency

#### **6. Graph Structure Endpoint**
```python
GET /api/graph/structure
Returns: {
    "locations": [...],  # All locations with coordinates
    "pathways": [...],   # All hallways/connections
    "bounds": {...}      # Min/max coordinates for scaling
}
```
**Key Feature**: Used by frontend to visualize hospital layout

#### **7. Patient Data Endpoints**
```python
GET /api/patients
GET /api/patient/<id>
```
**Key Feature**: Patient database for automatic prioritization

#### **8. Health Check**
```python
GET /api/health
Returns: System status (initialized, number of drones, etc.)
```

### Key Implementation Details:

1. **Error Handling**: All endpoints return proper HTTP status codes (200, 400, 404, 500)
2. **JSON Serialization**: Converts Python objects to JSON for frontend
3. **CORS Support**: Allows frontend to make requests
4. **Static File Serving**: Serves `templates/index.html` as web dashboard
5. **Request Serialization**: `serialize_request()` includes route data for visualization

---

## 🎯 Key Talking Points for Hackathon

### For MODELS.PY:
1. **"We use CTAS (Canadian Triage and Acuity Scale) - the real medical priority system used in hospitals"**
2. **"Our Request class tracks the full lifecycle with energy savings data"**
3. **"We have two types of drones: emergency and normal, each with different capabilities"**
4. **"The Vital Priority System automatically calculates priority based on patient vitals"**

### For SERVICE.PY:
1. **"We combine Dijkstra's algorithm for optimal drone assignment with RRT for dynamic collision avoidance"**
2. **"Priority queue ensures emergency requests are always processed first"**
3. **"We track cumulative energy savings and CO2 emissions in real-time"**
4. **"Drones can intercept multiple requests for efficiency - we evaluate if it's energy-efficient first"**
5. **"We compare our algorithm's path against the next quickest alternative to show efficiency"**
6. **"Battery management prevents drones from running out mid-flight"**
7. **"Emergency drones move at 4 m/s, normal drones at 2.5 m/s"**

### For API.PY:
1. **"RESTful API design - clean separation between frontend and backend"**
2. **"One initialization endpoint sets up the entire system"**
3. **"Real-time statistics endpoint shows cumulative environmental impact"**
4. **"Graph structure endpoint enables frontend visualization of hospital layout"**
5. **"All endpoints return proper HTTP status codes and error handling"**
6. **"We serve the web dashboard and API from the same Flask server"**

---

## 🔥 Potential Questions & Answers

**Q: How do you ensure emergency requests are handled first?**
A: We use a min-heap priority queue where lower priority values (CTAS I = 1) are processed first. The queue is sorted by priority value, then by waiting time.

**Q: How do you find the closest drone?**
A: We use Dijkstra's algorithm on the hospital graph to find the shortest path distance, not just Euclidean distance. This accounts for hallways and pathways.

**Q: What happens if RRT pathfinding fails?**
A: We fall back to Dijkstra's shortest path algorithm. This ensures we always have a valid route.

**Q: How do you calculate energy savings?**
A: We calculate drone energy consumption based on distance and payload weight, then compare against traditional methods (vehicle, electric cart, walking) using industry-standard formulas.

**Q: Can drones handle multiple requests?**
A: Yes! We have multi-stop optimization. When a drone is in flight, we evaluate if accepting a second request is energy-efficient. If it saves energy or is within 10% of baseline, the drone intercepts the new request.

**Q: How do you prevent collisions?**
A: RRT pathfinding with 3-lane traffic system. Emergency drones get middle lane, normal drones use left/right lanes. Lower priority drones yield to higher priority ones.

**Q: What's the difference between emergency and normal drones?**
A: Emergency drones are faster (4 m/s vs 2.5 m/s), can only handle emergency requests, and get priority in the 3-lane system (middle lane).

**Q: How do you track battery?**
A: Each drone has a battery level. When it drops below threshold, we automatically send it to the nearest charging station before it can accept new requests.

**Q: What data does the frontend get?**
A: Everything! Request status, drone positions, routes, energy savings, statistics, graph structure for visualization. The API provides full system state.

**Q: How do you handle concurrent requests?**
A: Thread-safe implementation using Python's threading.Lock() to prevent race conditions when multiple API requests modify the same data.

---

## 📊 System Flow Example

1. **Request Created** → `POST /api/request/create`
2. **Service Layer** → `create_request()` adds to priority queue
3. **Auto Assignment** → `_assign_drone_to_request()`:
   - Finds closest drone (Dijkstra)
   - Plans path (RRT with collision avoidance)
   - Assigns drone
4. **Flight Updates** → `update_drone_positions()` moves drone along route
5. **Completion** → `POST /api/request/<id>/complete`
6. **Energy Calculation** → Calculates savings vs traditional method
7. **Statistics Update** → Cumulative totals updated

---

## 💡 Quick Reference

**Models.py**: Data structures (Request, Drone, Location, Priority)
**Service.py**: Business logic (assignment, routing, energy, battery)
**API.py**: REST endpoints (create request, get status, statistics)

**Key Innovation**: Dijkstra (optimal) + RRT (dynamic) = Best of both worlds!
