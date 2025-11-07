"""
Route Optimization Service using OR-Tools TSP Solver
Based on the Traveling Salesman Problem algorithm
"""

from typing import List, Dict, Tuple, Optional
import math
import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


class Location:
    """Represents a location with coordinates and metadata"""
    def __init__(self, lat: float, lng: float, name: str, address: str = "", company_id: str = ""):
        self.lat = lat
        self.lng = lng
        self.name = name
        self.address = address
        self.company_id = company_id


class RouteOptimizer:
    """
    Route optimization using OR-Tools TSP solver
    Calculates optimal route for visiting multiple locations
    """
    
    def __init__(self, google_maps_api_key: str = None):
        self.google_maps_api_key = google_maps_api_key
    
    def haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate the great circle distance between two points on the earth
        Returns distance in kilometers
        """
        R = 6371  # Radius of the Earth in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance
    
    def create_distance_matrix(self, locations: List[Location]) -> List[List[int]]:
        """
        Create a distance matrix between all locations
        Uses Haversine formula for straight-line distances
        Returns distances in meters (as integers for OR-Tools)
        """
        num_locations = len(locations)
        distance_matrix = [[0] * num_locations for _ in range(num_locations)]
        
        for i in range(num_locations):
            for j in range(num_locations):
                if i == j:
                    distance_matrix[i][j] = 0
                else:
                    # Calculate distance and convert km to meters
                    distance_km = self.haversine_distance(
                        locations[i].lat, locations[i].lng,
                        locations[j].lat, locations[j].lng
                    )
                    distance_matrix[i][j] = int(distance_km * 1000)  # Convert to meters
        
        return distance_matrix
    
    def get_google_maps_distance_matrix(self, locations: List[Location]) -> Optional[List[List[int]]]:
        """
        Get actual driving distances from Google Maps Distance Matrix API
        Returns None if API is not available or fails
        """
        if not self.google_maps_api_key:
            return None
        
        try:
            # Prepare origins and destinations
            coordinates = [f"{loc.lat},{loc.lng}" for loc in locations]
            origins = "|".join(coordinates)
            destinations = "|".join(coordinates)
            
            # Make API request
            url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                "origins": origins,
                "destinations": destinations,
                "key": self.google_maps_api_key,
                "mode": "driving"
            }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get("status") != "OK":
                return None
            
            # Parse distance matrix
            num_locations = len(locations)
            distance_matrix = [[0] * num_locations for _ in range(num_locations)]
            
            for i, row in enumerate(data.get("rows", [])):
                for j, element in enumerate(row.get("elements", [])):
                    if element.get("status") == "OK":
                        distance_matrix[i][j] = element["distance"]["value"]  # Already in meters
                    else:
                        # Fallback to straight-line distance
                        distance_km = self.haversine_distance(
                            locations[i].lat, locations[i].lng,
                            locations[j].lat, locations[j].lng
                        )
                        distance_matrix[i][j] = int(distance_km * 1000)
            
            return distance_matrix
            
        except Exception as e:
            print(f"Error getting Google Maps distances: {e}")
            return None
    
    def solve_tsp(self, locations: List[Location], start_index: int = 0) -> Dict:
        """
        Solve the Traveling Salesman Problem for given locations
        
        Args:
            locations: List of Location objects to visit
            start_index: Index of the starting location (default: 0)
        
        Returns:
            Dictionary with optimized route information
        """
        if len(locations) < 2:
            return {
                "success": False,
                "error": "Need at least 2 locations to optimize route"
            }
        
        # Try to get Google Maps distances, fallback to Haversine
        distance_matrix = self.get_google_maps_distance_matrix(locations)
        if distance_matrix is None:
            distance_matrix = self.create_distance_matrix(locations)
        
        # Create the routing index manager
        manager = pywrapcp.RoutingIndexManager(
            len(distance_matrix),
            1,  # Number of vehicles (1 for TSP)
            start_index  # Depot (starting location)
        )
        
        # Create routing model
        routing = pywrapcp.RoutingModel(manager)
        
        # Create distance callback
        def distance_callback(from_index, to_index):
            """Returns the distance between the two nodes."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 30
        
        # Solve the problem
        solution = routing.SolveWithParameters(search_parameters)
        
        if not solution:
            return {
                "success": False,
                "error": "Could not find a solution"
            }
        
        # Extract the route
        route_indices = []
        route_locations = []
        total_distance = 0
        
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route_indices.append(node)
            route_locations.append({
                "index": node,
                "name": locations[node].name,
                "address": locations[node].address,
                "company_id": locations[node].company_id,
                "latitude": locations[node].lat,
                "longitude": locations[node].lng
            })
            
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
        
        # Add the end location (depot)
        final_node = manager.IndexToNode(index)
        route_indices.append(final_node)
        
        # Convert total distance from meters to kilometers
        total_distance_km = total_distance / 1000.0
        
        # Estimate duration (assuming average speed of 40 km/h in urban areas)
        estimated_duration_minutes = int((total_distance_km / 40.0) * 60)
        
        return {
            "success": True,
            "route": route_locations,
            "route_indices": route_indices,
            "total_distance_km": round(total_distance_km, 2),
            "total_distance_meters": total_distance,
            "estimated_duration_minutes": estimated_duration_minutes,
            "num_locations": len(locations)
        }
    
    def optimize_route(
        self,
        start_location: Dict,
        destinations: List[Dict]
    ) -> Dict:
        """
        Optimize a route starting from a specific location
        
        Args:
            start_location: Dict with keys: lat, lng, name, address (optional)
            destinations: List of dicts with keys: lat, lng, name, address (optional), company_id (optional)
        
        Returns:
            Dictionary with optimized route information
        """
        # Create Location objects
        locations = [
            Location(
                lat=start_location["lat"],
                lng=start_location["lng"],
                name=start_location.get("name", "Start"),
                address=start_location.get("address", "")
            )
        ]
        
        for dest in destinations:
            locations.append(
                Location(
                    lat=dest["lat"],
                    lng=dest["lng"],
                    name=dest.get("name", "Stop"),
                    address=dest.get("address", ""),
                    company_id=dest.get("company_id", "")
                )
            )
        
        # Solve TSP with start at index 0
        result = self.solve_tsp(locations, start_index=0)
        
        if result["success"]:
            # Remove the start location from the route stops (keep it separate)
            result["start_location"] = {
                "name": start_location.get("name", "Start"),
                "address": start_location.get("address", ""),
                "latitude": start_location["lat"],
                "longitude": start_location["lng"]
            }
            
            # The route includes all locations in order
            result["ordered_stops"] = result["route"][1:]  # Skip the start location
        
        return result


# Helper function for easy use
def optimize_trip_route(
    start_location: Dict,
    destinations: List[Dict],
    google_maps_api_key: str = None
) -> Dict:
    """
    Convenience function to optimize a trip route
    
    Example usage:
        result = optimize_trip_route(
            start_location={"lat": 50.8503, "lng": 4.3517, "name": "Brussels Office"},
            destinations=[
                {"lat": 50.8467, "lng": 4.3525, "name": "Client A", "company_id": "123"},
                {"lat": 50.8476, "lng": 4.3572, "name": "Client B", "company_id": "124"}
            ]
        )
    """
    optimizer = RouteOptimizer(google_maps_api_key=google_maps_api_key)
    return optimizer.optimize_route(start_location, destinations)

