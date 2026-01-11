# Algorithm Summary for Hackathon Presentation

## Overview

Our system uses a **hybrid pathfinding approach** combining **Dijkstra's Algorithm** and **RRT (Rapidly-exploring Random Tree)** to solve the hospital drone logistics problem with dynamic obstacle avoidance and multi-drone coordination.

## Algorithms Used

### 1. **Dijkstra's Algorithm** (Weighted Graph Pathfinding)
- **Purpose**: Find the closest available drone to a request location
- **Use Case**: Optimal drone assignment based on shortest path distance
- **Innovation**: Used for graph-based routing through hospital hallways, not just Euclidean distance

### 2. **RRT (Rapidly-exploring Random Tree)** (Dynamic Path Planning)
- **Purpose**: Dynamic path planning with collision avoidance
- **Use Case**: Navigate around obstacles and other drones in real-time
- **Innovation**: Extended with 3-lane traffic system and priority-based yielding

### 3. **Combined RRT + Dijkstra** (Our Innovation)
- **Purpose**: Optimal routing with dynamic obstacle avoidance
- **How it works**:
  1. Dijkstra finds the closest drone and initial optimal path
  2. RRT refines the path dynamically, avoiding collisions and other drones
  3. Combines graph-based optimality (Dijkstra) with free-space flexibility (RRT)

## Key Innovations

### Innovation 1: Combining Graph-Based and Free-Space Pathfinding
- **Dijkstra alone**: Only works on fixed graph (can't avoid dynamic obstacles)
- **RRT alone**: Doesn't guarantee optimal paths, random exploration is inefficient
- **Our approach**: Use Dijkstra for optimal initial routing, RRT for dynamic refinement

### Innovation 2: 3-Lane Traffic System
- Each hallway supports 3 drones side-by-side (3m width total)
- Priority-based lane assignment:
  - Emergency/high-priority drones → middle lane
  - Normal/low-priority drones → left/right lanes
- Lower-priority drones yield to higher-priority ones

### Innovation 3: Priority-Based Closest-Drone Assignment
- Not just closest by distance, but closest by **shortest path** through the graph
- Considers drone type (emergency vs normal)
- Real-time availability checking

## Code Snippets

### 1. Dijkstra for Finding Closest Drone

**Location**: `graph.py` - `find_closest_drone_location()`

```python
def find_closest_drone_location(self, requester_location_id: int, 
                                drone_locations: List[int]) -> Optional[int]:
    """Find closest drone using Dijkstra's shortest path (not Euclidean distance)"""
    
    # Use Dijkstra to find shortest paths from requester location
    distances, _ = self.weighted_dijkstra(requester_location_id)
    
    # Find minimum distance among available drone locations
    closest_id = None
    min_distance = float('inf')
    
    for drone_loc_id in drone_locations:
        if drone_loc_id in distances and distances[drone_loc_id] < min_distance:
            min_distance = distances[drone_loc_id]
            closest_id = drone_loc_id
    
    return closest_id
```

**Why it's innovative**: Uses graph-based shortest path through hospital hallways, not just straight-line Euclidean distance.

### 2. RRT with 3-Lane Traffic System and Priority-Based Yielding

**Location**: `rrt_pathfinding.py` - `_is_collision_free()`

```python
def _is_collision_free(self, point, other_drones, current_drone_id, 
                       is_emergency, current_lane, current_priority_level):
    """Check collision with 3-lane system and priority-based yielding"""
    
    for drone_id, trajectory in other_drones.items():
        other_lane = getattr(other_pos, 'lane', 1)
        other_priority = getattr(other_pos, 'priority_level', 3)
        
        # Same lane: stricter collision check
        if current_lane == other_lane:
            dist = self._distance(point, predicted_pos)
            if dist < self.lane_width * 1.5:
                # Lower priority must yield to higher priority
                if (not is_emergency and current_priority_level < 4) and \
                   (other_is_emergency or other_priority >= 4):
                    return False  # Lower priority must yield
        
        # Emergency vehicles get 3x safety margin
        if other_is_emergency and not is_emergency:
            emergency_safety_radius = self.obstacle_radius * 3.0
            if dist < emergency_safety_radius:
                return False
    
    return True
```

**Why it's innovative**: Extends RRT with structured 3-lane traffic system and priority-based yielding rules (inspired by emergency vehicle protocols).

### 3. Combined Algorithm in Service Layer

**Location**: `service.py` - `_assign_drone_to_request()`

```python
def _assign_drone_to_request(self, request: Request) -> bool:
    """Assign closest available drone to request using RRT path planning"""
    is_emergency = request.emergency or request.priority.is_emergency
    available_locations = self._get_available_drone_locations(for_emergency=is_emergency)
    if not available_locations:
        return False
    
    # STEP 1: Use Dijkstra to find closest drone location
    closest_loc_id = self.graph.find_closest_drone_location(
        request.requester_location_id, available_locations
    )
    if closest_loc_id is None:
        return False
    
    # Find the drone at that location
    assigned_drone = None
    for drone in self.drones.values():
        if (drone.status == "available" and 
            drone.current_location_id == closest_loc_id and
            drone.emergency_drone == is_emergency):
            assigned_drone = drone
            break
    
    # STEP 2: Use RRT to plan path with collision avoidance
    start_loc = self.graph.nodes[closest_loc_id]
    goal_loc = self.graph.nodes[request.requester_location_id]
    
    path = self.rrt_planner.plan_path_with_traffic_rules(
        start_loc=start_loc,
        goal_loc=goal_loc,
        current_drone_id=assigned_drone.id,
        is_emergency=is_emergency,
        active_drone_flights=self.active_flights,
        all_drones=self.drones,
        current_priority_level=request.priority.value
    )
    
    # STEP 3: Fallback to Dijkstra if RRT fails
    if len(path) < 2:
        path, _ = self.graph.find_shortest_path(closest_loc_id, request.requester_location_id)
    
    # Assign the route
    assigned_drone.delivery_route = path
    request.assigned_drone_id = assigned_drone.id
    return True
```

**Why it's innovative**: 
- Uses Dijkstra for optimal assignment
- Uses RRT for dynamic path refinement
- Falls back to Dijkstra if RRT fails
- Combines graph optimality with free-space flexibility

### 4. 3-Lane Collision Checking

**Location**: `rrt_pathfinding.py` - `_is_collision_free_with_lanes()`

```python
def _is_collision_free_with_lanes(self, from_point, to_point, 
                                  active_drone_flights, all_drones,
                                  current_drone_id, lane_offset):
    """
    Check if path segment is collision-free considering 3-lane system
    """
    # Calculate lane position (left: -1, middle: 0, right: +1)
    current_lane = lane_offset
    
    for drone_id, flight_info in active_drone_flights.items():
        if drone_id == current_drone_id:
            continue
        
        other_drone = all_drones.get(drone_id)
        if not other_drone:
            continue
        
        # Check priority - lower priority must yield
        other_priority = flight_info.get('priority_level', 3)
        current_priority = ...  # current drone's priority
        
        if current_priority < other_priority:
            # Lower priority: must yield if in same lane
            if self._same_lane_conflict(current_lane, other_drone, from_point, to_point):
                return False
        elif current_priority > other_priority:
            # Higher priority: can use any lane
            pass
    
    return True
```

**Why it's innovative**: Implements structured multi-drone coordination with priority-based yielding.

## Summary for Presentation

**What algorithms?**
- Dijkstra's Algorithm (weighted graph pathfinding)
- RRT (Rapidly-exploring Random Tree) with 3-lane traffic system

**How are they different from base algorithms?**
1. **Dijkstra**: Extended to work on hospital hallway graph, finds closest drone by path distance
2. **RRT**: Enhanced with 3-lane traffic system and priority-based lane assignment
3. **Combined**: Uses Dijkstra for optimal assignment + RRT for dynamic avoidance

**How are they used together?**
1. **Dijkstra** finds the closest available drone (by shortest path)
2. **RRT** plans the actual route with collision avoidance and lane management
3. **Fallback**: If RRT fails, use Dijkstra's shortest path
4. **Result**: Optimal routing with real-time obstacle avoidance

**Key Innovation**: We combine the **optimality of graph-based algorithms** (Dijkstra) with the **flexibility of sampling-based algorithms** (RRT) to create a system that's both efficient and adaptive to dynamic environments.
