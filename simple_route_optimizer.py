"""
Simple Route Optimization using TSP algorithms
No external dependencies required - pure Python implementation
"""

import math
from typing import List, Dict, Tuple


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth
    Returns distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def create_distance_matrix(locations: List[Dict]) -> List[List[float]]:
    """
    Create a distance matrix between all locations using Haversine formula
    
    Args:
        locations: List of dicts with 'lat' and 'lng' keys
    
    Returns:
        2D list of distances in kilometers
    """
    n = len(locations)
    matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = haversine_distance(
                    locations[i]['lat'], locations[i]['lng'],
                    locations[j]['lat'], locations[j]['lng']
                )
    
    return matrix


def nearest_neighbor_tsp(distance_matrix: List[List[float]], start_index: int = 0) -> List[int]:
    """
    Solve TSP using Nearest Neighbor greedy algorithm
    
    Args:
        distance_matrix: 2D list of distances
        start_index: Starting location index
    
    Returns:
        List of location indices in visit order
    """
    n = len(distance_matrix)
    unvisited = set(range(n))
    route = [start_index]
    unvisited.remove(start_index)
    
    current = start_index
    
    while unvisited:
        # Find nearest unvisited location
        nearest = min(unvisited, key=lambda x: distance_matrix[current][x])
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest
    
    return route


def calculate_route_distance(route: List[int], distance_matrix: List[List[float]]) -> float:
    """Calculate total distance for a given route"""
    total = 0.0
    for i in range(len(route) - 1):
        total += distance_matrix[route[i]][route[i + 1]]
    return total


def two_opt_improvement(route: List[int], distance_matrix: List[List[float]], max_iterations: int = 100) -> List[int]:
    """
    Improve route using 2-opt algorithm
    
    This algorithm repeatedly removes two edges and reconnects them in a different way
    if it reduces the total distance.
    """
    improved = True
    best_route = route[:]
    iteration = 0
    
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        
        for i in range(1, len(route) - 2):
            for j in range(i + 1, len(route)):
                if j - i == 1:
                    continue
                
                # Try reversing the segment between i and j
                new_route = route[:]
                new_route[i:j] = reversed(route[i:j])
                
                # Check if this improves the route
                if calculate_route_distance(new_route, distance_matrix) < calculate_route_distance(best_route, distance_matrix):
                    best_route = new_route[:]
                    improved = True
        
        route = best_route[:]
    
    return best_route


def optimize_trip_route(
    start_location: Dict,
    destinations: List[Dict],
    google_maps_api_key: str = None
) -> Dict:
    """
    Optimize a trip route using TSP algorithms
    
    Args:
        start_location: Dict with 'lat', 'lng', and optionally 'name', 'address'
        destinations: List of dicts with 'lat', 'lng', and optionally 'name', 'address', 'id'
        google_maps_api_key: Optional (not used in this implementation, here for compatibility)
    
    Returns:
        Dict with success status, ordered stops, and route metrics
    """
    try:
        # Validate inputs
        if not destinations or len(destinations) == 0:
            return {
                'success': False,
                'error': 'No destinations provided'
            }
        
        # Filter out destinations without valid coordinates
        valid_destinations = [
            d for d in destinations 
            if d.get('lat') is not None and d.get('lng') is not None
        ]
        
        if len(valid_destinations) == 0:
            return {
                'success': False,
                'error': 'No destinations with valid coordinates'
            }
        
        # If only one destination, no optimization needed
        if len(valid_destinations) == 1:
            dest = valid_destinations[0]
            distance = haversine_distance(
                start_location['lat'], start_location['lng'],
                dest['lat'], dest['lng']
            )
            
            return {
                'success': True,
                'ordered_stops': [{
                    'name': dest.get('name', 'Stop 1'),
                    'address': dest.get('address', ''),
                    'latitude': dest['lat'],
                    'longitude': dest['lng'],
                    'company_id': dest.get('id', ''),
                    'type': dest.get('type', 'unknown')
                }],
                'total_distance_km': round(distance * 2, 2),  # Round trip
                'estimated_duration_minutes': int((distance * 2 / 40) * 60),  # 40 km/h average
                'num_locations': 1
            }
        
        # Create combined list with start location first
        all_locations = [start_location] + valid_destinations
        
        # Create distance matrix
        distance_matrix = create_distance_matrix(all_locations)
        
        # Solve TSP using Nearest Neighbor
        route_indices = nearest_neighbor_tsp(distance_matrix, start_index=0)
        
        # Improve with 2-opt
        route_indices = two_opt_improvement(route_indices, distance_matrix)
        
        # Calculate total distance (including return to start)
        total_distance = calculate_route_distance(route_indices, distance_matrix)
        
        # Add return distance to start location
        if len(route_indices) > 1:
            last_stop_idx = route_indices[-1]
            return_distance = distance_matrix[last_stop_idx][0]  # Distance from last stop back to start (index 0)
            total_distance += return_distance
        
        # Build ordered stops (exclude start location)
        ordered_stops = []
        for idx in route_indices[1:]:  # Skip index 0 (start location)
            loc = all_locations[idx]
            ordered_stops.append({
                'name': loc.get('name', f'Stop {len(ordered_stops) + 1}'),
                'address': loc.get('address', ''),
                'latitude': loc['lat'],
                'longitude': loc['lng'],
                'company_id': loc.get('id', ''),
                'type': loc.get('type', 'unknown')
            })
        
        # Estimate duration (40 km/h average urban speed)
        estimated_duration_minutes = int((total_distance / 40.0) * 60)
        # Add time per stop (15 min average)
        estimated_duration_minutes += len(ordered_stops) * 15
        
        return {
            'success': True,
            'ordered_stops': ordered_stops,
            'total_distance_km': round(total_distance, 2),
            'estimated_duration_minutes': estimated_duration_minutes,
            'num_locations': len(ordered_stops),
            'optimization_method': 'Nearest Neighbor + 2-opt'
        }
        
    except Exception as e:
        print(f"Route optimization error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e)
        }


# For backward compatibility with existing code
class RouteOptimizer:
    """Simple wrapper for compatibility"""
    
    def __init__(self, google_maps_api_key: str = None):
        self.google_maps_api_key = google_maps_api_key
    
    def optimize_route(self, start_location: Dict, destinations: List[Dict]) -> Dict:
        return optimize_trip_route(start_location, destinations, self.google_maps_api_key)

