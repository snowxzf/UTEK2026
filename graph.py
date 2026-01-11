"""
Hospital graph implementation with weighted Dijkstra's algorithm.
References:
1. Dijkstra, E. W. (1959). A note on two problems in connexion with graphs.
   Numerische Mathematik, 1(1), 269-271. https://doi.org/10.1007/BF01386390
2. Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2009). 
   Introduction to Algorithms (3rd ed.). MIT Press. (Section 24.3: Dijkstra's algorithm)
"""
from typing import Dict, List, Optional, Tuple
import heapq
import math
from models import Location


class HospitalGraph:
    """
    Weighted graph representing hospital layout for Dijkstra's algorithm
    Edges represent pathways between locations with travel times as weights
    """
    def __init__(self):
        self.nodes: Dict[int, Location] = {}
        self.adjacency_list: Dict[int, List[Tuple[int, float]]] = {}
        # Format: {node_id: [(neighbor_id, weight), ...]}

    def add_location(self, location: Location):
        """Add a location/node to the graph"""
        self.nodes[location.id] = location
        if location.id not in self.adjacency_list:
            self.adjacency_list[location.id] = []

    def add_pathway(self, from_id: int, to_id: int, weight: float, bidirectional: bool = True):
        """
        Add a pathway (edge) between two locations
        Weight represents travel time/cost
        """
        if from_id not in self.adjacency_list:
            self.adjacency_list[from_id] = []
        if to_id not in self.adjacency_list:
            self.adjacency_list[to_id] = []

        self.adjacency_list[from_id].append((to_id, weight))

        if bidirectional:
            self.adjacency_list[to_id].append((from_id, weight))

    def euclidean_distance(self, loc1: Location, loc2: Location) -> float:
        """Calculate Euclidean distance between two locations"""
        dx = loc1.x - loc2.x
        dy = loc1.y - loc2.y
        same_floor = 1 if loc1.floor == loc2.floor else 10  # Penalty for floor changes
        return math.sqrt(dx*dx + dy*dy) * same_floor
    
    def weighted_dijkstra(self, start_id: int, target_id: Optional[int] = None) -> Tuple[Dict[int, float], Dict[int, int]]:
        """
        Weighted Dijkstra's algorithm implementation
        Returns: (distances, previous_nodes)
        If target_id provided, stops early when target is reached
        """
        if start_id not in self.nodes:
            raise ValueError(f"Start location {start_id} not in graph")

        # Initialize distances: all nodes initially unreachable (infinity)
        distances: Dict[int, float] = {node_id: float('inf') for node_id in self.nodes}
        distances[start_id] = 0.0

        # Track previous node for path reconstruction
        previous: Dict[int, int] = {}

        # Priority queue: (distance, node_id)
        pq = [(0.0, start_id)]
        visited = set()

        while pq:
            current_dist, current_id = heapq.heappop(pq)

            if current_id in visited:
                continue

            visited.add(current_id)

            # Early termination if target reached
            if target_id is not None and current_id == target_id:
                break

            # Explore neighbors
            if current_id in self.adjacency_list:
                for neighbor_id, edge_weight in self.adjacency_list[current_id]:
                    if neighbor_id in visited:
                        continue
                    # Calculate total distance: edge weight + heuristic adjustment
                    new_dist = current_dist + edge_weight
                    # If found a shorter path, update it
                    if new_dist < distances[neighbor_id]:
                        distances[neighbor_id] = new_dist
                        previous[neighbor_id] = current_id
                        heapq.heappush(pq, (new_dist, neighbor_id))

        return distances, previous

    def find_shortest_path(self, start_id: int, target_id: int) -> Tuple[List[int], float]:
        """
        Find shortest path between two locations
        Returns: (path as list of location IDs, total distance)
        """
        if start_id not in self.nodes or target_id not in self.nodes:
            return [], float('inf')

        distances, previous = self.weighted_dijkstra(start_id, target_id)

        if distances[target_id] == float('inf'):
            return [], float('inf')

        # Reconstruct path
        path = []
        current = target_id
        while current is not None:
            path.append(current)
            current = previous.get(current)

        path.reverse()
        return path, distances[target_id]
    
    def find_second_shortest_path(self, start_id: int, target_id: int) -> Tuple[List[int], float]:
        """
        Find the second shortest path between two locations (next quickest alternative)
        Uses Yen's k-shortest paths algorithm approach: find shortest, then find next shortest
        that doesn't use the exact same edges
        
        Returns: (path as list of location IDs, total distance)
        """
        if start_id not in self.nodes or target_id not in self.nodes:
            return [], float('inf')
        
        # Get the shortest path first
        shortest_path, shortest_dist = self.find_shortest_path(start_id, target_id)
        if shortest_path == [] or shortest_dist == float('inf'):
            return [], float('inf')
        
        # If path is just start->target, no second path exists
        if len(shortest_path) < 3:
            return [], float('inf')
        
        # Try removing each edge from the shortest path and find new shortest
        second_shortest_path = []
        second_shortest_dist = float('inf')
        
        # For each edge in the shortest path, temporarily remove it and find shortest
        for i in range(len(shortest_path) - 1):
            from_node = shortest_path[i]
            to_node = shortest_path[i + 1]
            
            # Temporarily remove this edge
            original_edges_from = self.adjacency_list[from_node].copy()
            original_edges_to = self.adjacency_list[to_node].copy()
            
            # Remove bidirectional edge
            self.adjacency_list[from_node] = [
                (nid, w) for nid, w in self.adjacency_list[from_node] if nid != to_node
            ]
            self.adjacency_list[to_node] = [
                (nid, w) for nid, w in self.adjacency_list[to_node] if nid != from_node
            ]
            
            # Find shortest path with this edge removed
            alt_path, alt_dist = self.find_shortest_path(start_id, target_id)
            
            # Restore the edge
            self.adjacency_list[from_node] = original_edges_from
            self.adjacency_list[to_node] = original_edges_to
            
            # If we found a valid alternative path that's shorter than current best
            if alt_path and alt_dist < second_shortest_dist and alt_path != shortest_path:
                second_shortest_path = alt_path
                second_shortest_dist = alt_dist
        
        if second_shortest_path:
            return second_shortest_path, second_shortest_dist
        
        # If no second path found by edge removal, return empty (only one path exists)
        return [], float('inf')
    
    def find_closest_drone_location(self, requester_location_id: int, drone_locations: List[int]) -> Optional[int]:
        """
        Find the closest drone to the requester location
        Returns: drone_location_id or None if no drones available
        """
        if not drone_locations:
            return None

        if requester_location_id not in self.nodes:
            return None

        distances, _ = self.weighted_dijkstra(requester_location_id)

        # Filter to only available drone locations and find minimum
        closest_id = None
        min_distance = float('inf')

        for drone_loc_id in drone_locations:
            if drone_loc_id in distances and distances[drone_loc_id] < min_distance:
                min_distance = distances[drone_loc_id]
                closest_id = drone_loc_id
        
        return closest_id
