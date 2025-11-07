# 🗺️ Trips Feature - Complete Guide

## Overview

The **Trips** feature is a powerful route optimization system integrated into your CRM that uses the **Traveling Salesman Problem (TSP)** algorithm to automatically calculate the most efficient route for visiting multiple companies or prospects.

## 🎯 Key Features

### 1. **Intelligent Route Optimization**
- Uses OR-Tools library with TSP solver
- Minimizes total travel distance
- Calculates optimal visit order
- Supports both driving distances (Google Maps API) and straight-line distances (Haversine formula)

### 2. **Visual Trip Management**
- Interactive Google Maps visualization
- Clear route display with numbered stops
- Distance and duration estimates
- Easy drag-and-drop interface for stop management

### 3. **Flexible Trip Creation**
- Select companies or prospects from the Planning page
- Custom start location with address autocomplete
- Schedule trips with date and time
- Add notes and metadata

## 📋 Database Schema

### Tables Created

#### `trips`
- `id` (UUID, Primary Key)
- `name` (VARCHAR) - Trip name
- `trip_date` (DATE) - Scheduled date
- `start_location` (VARCHAR) - Starting point name
- `start_time` (TIME) - Departure time
- `start_lat`, `start_lng` (DECIMAL) - Starting coordinates
- `status` (VARCHAR) - planned | in_progress | completed
- `total_distance_km` (DECIMAL) - Calculated distance
- `estimated_duration_minutes` (INTEGER) - Travel time estimate
- `notes` (TEXT) - Optional trip notes
- `created_at`, `updated_at` (TIMESTAMP)

#### `trip_stops`
- `id` (UUID, Primary Key)
- `trip_id` (UUID, Foreign Key → trips)
- `company_id` (VARCHAR) - Reference to company
- `company_name` (VARCHAR) - Stop name
- `address` (VARCHAR) - Stop address
- `latitude`, `longitude` (DECIMAL) - Stop coordinates
- `stop_order` (INTEGER) - Visit sequence (optimized)
- `estimated_arrival` (TIME) - Planned arrival
- `duration_minutes` (INTEGER) - Time at location
- `completed` (BOOLEAN) - Visit status
- `created_at` (TIMESTAMP)

## 🚀 How to Use

### Step 1: Setup Database

Run the SQL migration in Supabase:

```bash
# In Supabase SQL Editor, execute:
/Users/hendrikdewinne/MOTHERSHIP_PROSPECTING/create_trips_table.sql
```

### Step 2: Install Dependencies

```bash
pip install ortools>=9.8.0
```

The OR-Tools library provides the optimization algorithms.

### Step 3: Create a Trip

1. **Navigate to Planning Page** (`/planning`)
2. **Select Companies/Prospects**
   - Use the map interface to visualize locations
   - Check the companies or prospects you want to visit
   - Selection count appears on the "Visualize" button

3. **Click "Create Trip"** (green button on map)
   
4. **Fill in Trip Details**
   - **Trip Name**: Give it a descriptive name
   - **Trip Date**: When you plan to visit
   - **Start Time**: Departure time
   - **Starting Location**: Your office or starting point
     - Uses Google Places Autocomplete
     - Automatically geocodes the address
   - **Notes**: Optional trip information

5. **Submit**
   - The system automatically:
     - Optimizes the route using TSP algorithm
     - Calculates total distance
     - Estimates travel duration
     - Creates the trip with ordered stops

### Step 4: View and Manage Trips

Navigate to **Trips Page** (`/trips`)

#### Left Panel: Trip List
- Shows all your trips
- Filter by status (Planned, In Progress, Completed)
- Displays trip metadata:
  - Date and time
  - Number of stops
  - Total distance
  - Status badge

#### Right Panel: Trip Details
- **Interactive Map**
  - Green "S" marker = Start location
  - Numbered blue markers = Stops (in optimal order)
  - Blue route line = Driving directions
  - Click markers for info windows

- **Route Stops Sidebar**
  - Ordered list of all stops
  - Company names and addresses
  - Delete individual stops
  - Automatic reordering after deletion

- **Trip Information**
  - Total stops count
  - Total distance in kilometers
  - Estimated duration
  - Current status

#### Actions Available
- **Re-optimize**: Recalculate route if stops were modified
- **Delete Stop**: Remove a location from the trip
- **Delete Trip**: Remove entire trip

## 🔧 API Endpoints

All endpoints require authentication (`@login_required`)

### GET `/api/trips`
Fetch all trips with optional filters

**Query Parameters:**
- `status` - Filter by trip status
- `from_date` - Start date filter
- `to_date` - End date filter

**Response:**
```json
{
  "success": true,
  "trips": [...]
}
```

### GET `/api/trips/<trip_id>`
Get single trip with all stops

**Response:**
```json
{
  "success": true,
  "trip": {
    "id": "uuid",
    "name": "Trip name",
    "stops": [...]
  }
}
```

### POST `/api/trips`
Create new trip with optimized route

**Request Body:**
```json
{
  "name": "North Region Visit",
  "trip_date": "2025-11-15",
  "start_time": "09:00",
  "start_location": {
    "lat": 50.8503,
    "lng": 4.3517,
    "name": "Brussels Office"
  },
  "destinations": [
    {
      "company_id": "123",
      "name": "Client A",
      "address": "123 Main St",
      "lat": 50.8467,
      "lng": 4.3525
    }
  ],
  "notes": "Optional notes"
}
```

**Response:**
```json
{
  "success": true,
  "trip": {...},
  "message": "Trip created successfully with optimized route"
}
```

### PUT `/api/trips/<trip_id>`
Update trip details

**Request Body:**
```json
{
  "name": "Updated name",
  "status": "completed",
  "notes": "New notes"
}
```

### DELETE `/api/trips/<trip_id>`
Delete trip (cascades to stops)

### DELETE `/api/trips/<trip_id>/stops/<stop_id>`
Remove a stop from trip and reorder

### POST `/api/trips/<trip_id>/optimize`
Re-optimize existing trip route

## 🧠 How the TSP Algorithm Works

The system uses Google's OR-Tools library to solve the Traveling Salesman Problem:

### 1. **Distance Matrix Creation**
```python
# Two methods available:
# A) Google Maps Distance Matrix API (real driving distances)
# B) Haversine formula (straight-line distances)
```

### 2. **Optimization Process**
- **Algorithm**: PATH_CHEAPEST_ARC (first solution)
- **Metaheuristic**: GUIDED_LOCAL_SEARCH (improvement)
- **Objective**: Minimize total travel distance
- **Constraint**: Visit each location exactly once
- **Time Limit**: 30 seconds

### 3. **Output**
- Optimal visit order
- Total distance in kilometers
- Estimated duration (based on 40 km/h average)
- Complete route with coordinates

### Example Calculation

**Input:**
- Start: Office (50.850, 4.351)
- Stop A: Client 1 (50.846, 4.352)
- Stop B: Client 2 (50.855, 4.360)
- Stop C: Client 3 (50.840, 4.345)

**Algorithm Process:**
1. Calculate distances between all points
2. Find the shortest route visiting all locations
3. Return optimized order: Office → C → A → B

**Output:**
- Route: [Office, Stop C, Stop A, Stop B]
- Distance: 12.5 km
- Duration: ~19 minutes

## 📊 Technical Implementation

### Route Optimizer Service
**File:** `route_optimizer.py`

**Key Classes:**
- `Location`: Represents a geographical point
- `RouteOptimizer`: Main optimization engine
  - `haversine_distance()`: Calculate straight-line distances
  - `create_distance_matrix()`: Build distance matrix
  - `get_google_maps_distance_matrix()`: Fetch real driving distances
  - `solve_tsp()`: Run optimization algorithm

**Usage Example:**
```python
from route_optimizer import optimize_trip_route

result = optimize_trip_route(
    start_location={"lat": 50.8503, "lng": 4.3517, "name": "Office"},
    destinations=[
        {"lat": 50.8467, "lng": 4.3525, "name": "Client A"},
        {"lat": 50.8476, "lng": 4.3572, "name": "Client B"}
    ],
    google_maps_api_key="YOUR_API_KEY"
)

print(result['total_distance_km'])  # 8.5
print(result['route'])  # Ordered list of stops
```

### Frontend Components

#### Planning Page Updates
- **"Create Trip" button** added to map controls
- **Modal dialog** for trip creation
- **Google Places Autocomplete** for start location
- **Form validation** before submission
- **Real-time selection tracking**

#### Trips Page
- **Split-panel layout**:
  - Left: Trips list with filters
  - Right: Map visualization + stops sidebar
- **Google Maps integration**:
  - Custom markers (green start, numbered stops)
  - Directions rendering
  - Info windows on click
- **Interactive stop management**
- **Real-time updates**

## 🎨 UI/UX Features

### Modern Design Elements
- **Color-coded status badges**
  - Planned: Blue
  - In Progress: Orange
  - Completed: Green

- **Interactive map markers**
  - Start location: Green circle with "S"
  - Stops: Blue numbered circles
  - Hover for details

- **Smooth transitions**
  - Card hover effects
  - Button animations
  - Toast notifications

### User Experience
- **Intuitive workflow**: Plan → Create → Visualize → Execute
- **Real-time feedback**: Loading states, success/error messages
- **Responsive layout**: Works on desktop and tablet
- **Keyboard accessible**: Full keyboard navigation support

## 📈 Performance Considerations

### Optimization Speed
- **< 5 stops**: Nearly instant (< 1 second)
- **5-15 stops**: Fast (1-3 seconds)
- **15-25 stops**: Moderate (3-10 seconds)
- **> 25 stops**: May require split into multiple trips

### Google Maps API Limits
- **Distance Matrix API**: 25 origins × 25 destinations per request
- **Directions API**: 23 waypoints max
- **Solution**: System automatically handles limits

### Caching Strategy
- Companies/prospects data cached for 5 minutes
- Reduces API calls
- Improves performance

## 🔐 Security

### Authentication
- All API endpoints protected with `@login_required`
- Session-based authentication
- RLS policies enabled on database tables

### Data Validation
- Input sanitization on backend
- Type checking with Pydantic (optional)
- SQL injection prevention via Supabase client

## 🐛 Troubleshooting

### Issue: "Route optimizer not available"
**Solution:** Install OR-Tools
```bash
pip install ortools
```

### Issue: "Could not find location"
**Solution:** 
- Ensure Google Maps API key is set
- Use address from autocomplete dropdown
- Check Places API is enabled

### Issue: "Directions request failed"
**Solution:**
- Check Google Maps Directions API is enabled
- Verify API key has proper permissions
- Fallback: System draws straight lines

### Issue: No stops showing on map
**Solution:**
- Verify companies have lat/lng coordinates
- Run geocoding if needed
- Check browser console for errors

## 🚀 Future Enhancements

### Planned Features
1. **Time Windows**: Specify visit hours for each stop
2. **Multi-Vehicle**: Support multiple sales reps
3. **Real-time Tracking**: GPS integration
4. **Traffic Data**: Consider real-time traffic
5. **Export Routes**: PDF/Excel export
6. **Mobile App**: Native mobile version
7. **Historical Analytics**: Trip performance metrics
8. **Smart Scheduling**: AI-powered best time suggestions

### Potential Integrations
- **Calendar Sync**: Google Calendar, Outlook
- **Navigation Apps**: Waze, Google Maps deep links
- **CRM Activities**: Auto-log visits
- **Reporting**: Sales visit reports

## 📚 References

### Libraries Used
- [OR-Tools](https://developers.google.com/optimization) - Google's optimization tools
- [Supabase](https://supabase.com/) - Backend database
- [Google Maps API](https://developers.google.com/maps) - Maps and routing
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Bootstrap 5](https://getbootstrap.com/) - UI components

### Algorithms
- **Traveling Salesman Problem**: [Wikipedia](https://en.wikipedia.org/wiki/Travelling_salesman_problem)
- **Haversine Formula**: [Wikipedia](https://en.wikipedia.org/wiki/Haversine_formula)
- **Guided Local Search**: [OR-Tools Docs](https://developers.google.com/optimization/routing/routing_options#local_search_options)

### Similar Projects
- [albertferre/travelling-salesman-routing](https://github.com/albertferre/travelling-salesman-routing) - Inspiration for this implementation

## 💡 Tips for Best Results

1. **Geocode all companies** before creating trips
2. **Group by region** for better optimization
3. **Limit to 20 stops** per trip for best performance
4. **Use real addresses** for accurate Google Maps routing
5. **Re-optimize after changes** to maintain efficiency
6. **Check route** before starting trip
7. **Update status** as you progress through stops

## 🎉 Success!

You now have a complete route optimization system! This feature will:
- ✅ Save time planning routes
- ✅ Reduce travel distances
- ✅ Improve sales efficiency
- ✅ Provide professional route visualization
- ✅ Track all visits systematically

Happy routing! 🚗💨

