# 🚀 Trips Feature - Quick Setup Checklist

## Prerequisites
- ✅ Supabase account with database access
- ✅ Google Maps API key with required APIs enabled
- ✅ Python 3.8+ environment
- ✅ Existing companies/prospects with geocoded locations

## Setup Steps

### 1️⃣ Database Setup (5 minutes)

**Action:** Create database tables in Supabase

1. Open Supabase Dashboard → SQL Editor
2. Copy contents of `create_trips_table.sql`
3. Execute the SQL script
4. Verify tables created:
   - ✅ `trips` table
   - ✅ `trip_stops` table
   - ✅ Indexes created
   - ✅ RLS policies enabled

**Test:**
```sql
SELECT * FROM trips;
SELECT * FROM trip_stops;
```

---

### 2️⃣ Install Dependencies (2 minutes)

**Action:** Add OR-Tools library

```bash
pip install ortools>=9.8.0
```

**Verify Installation:**
```bash
python -c "import ortools; print('OR-Tools installed successfully!')"
```

---

### 3️⃣ Google Maps API Configuration (5 minutes)

**Action:** Enable required Google Maps APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable these APIs:
   - ✅ Maps JavaScript API
   - ✅ Places API
   - ✅ Distance Matrix API
   - ✅ Directions API
   - ✅ Geocoding API

3. Ensure your API key in `.env` or `config.py`:
```python
GOOGLE_MAPS_API_KEY = "your_api_key_here"
```

**Test API Key:**
```bash
curl "https://maps.googleapis.com/maps/api/geocode/json?address=Brussels&key=YOUR_KEY"
```

---

### 4️⃣ File Verification (1 minute)

**Action:** Ensure all files are in place

```bash
# Check Python files
ls -la route_optimizer.py                    # ✅ Route optimization service
ls -la app.py                                 # ✅ Backend with trip endpoints

# Check templates
ls -la templates/trips.html                   # ✅ Trips page
ls -la templates/planning_working.html        # ✅ Updated planning page
ls -la templates/base.html                    # ✅ Updated navigation

# Check SQL
ls -la create_trips_table.sql                 # ✅ Database schema

# Check documentation
ls -la TRIPS_FEATURE_GUIDE.md                 # ✅ Complete guide
ls -la TRIPS_QUICK_SETUP.md                   # ✅ This file
```

---

### 5️⃣ Start the Application (1 minute)

**Action:** Run Flask server

```bash
python app.py
```

**Expected Output:**
```
 * Running on http://0.0.0.0:5002
 * Debug mode: on
```

---

### 6️⃣ Test the Feature (10 minutes)

#### Test 1: Access Trips Page
1. Navigate to: `http://localhost:5002/trips`
2. Should see empty trips list
3. "Create New Trip" button visible
4. ✅ **PASS** if page loads without errors

#### Test 2: Create a Test Trip
1. Go to: `http://localhost:5002/planning`
2. Load companies data
3. Select 3-5 companies with geocoded locations
4. Click "Create Trip" button (green)
5. Fill in modal:
   - Name: "Test Trip"
   - Date: Tomorrow's date
   - Time: 09:00
   - Start Location: Your office address
   - Notes: "Testing trips feature"
6. Click "Create Trip"
7. ✅ **PASS** if redirected to trips page with new trip

#### Test 3: View Trip Details
1. Click on the newly created trip
2. Should see:
   - ✅ Google Map with route
   - ✅ Green "S" marker at start
   - ✅ Numbered blue markers for stops
   - ✅ Blue route line connecting locations
   - ✅ Sidebar with ordered stops
   - ✅ Trip statistics (distance, duration, stops)

#### Test 4: Modify Trip
1. Click "Re-optimize" button
2. ✅ **PASS** if route recalculates
3. Delete one stop
4. ✅ **PASS** if stop removed and others reordered

#### Test 5: Delete Trip
1. Click "Delete" button
2. Confirm deletion
3. ✅ **PASS** if trip removed from list

---

## 🔍 Verification Checklist

After setup, verify these items work:

### Backend
- [ ] `/api/trips` returns trips list (even if empty)
- [ ] Route optimizer module imports without errors
- [ ] Supabase connection established
- [ ] Google Maps API key loaded

### Frontend
- [ ] "Trips" tab appears in navigation
- [ ] Planning page has "Create Trip" button
- [ ] Trips page loads without console errors
- [ ] Google Maps initializes correctly

### Functionality
- [ ] Can select companies on planning page
- [ ] Trip creation modal opens
- [ ] Form validation works
- [ ] Trip saves to database
- [ ] Map displays route correctly
- [ ] Can delete stops
- [ ] Can delete trips
- [ ] Re-optimization works

---

## 🚨 Common Issues & Quick Fixes

### Issue 1: "Module 'ortools' not found"
```bash
pip install ortools
# OR in virtual environment
source venv/bin/activate
pip install ortools
```

### Issue 2: "Database not available"
**Check:**
- Supabase credentials in config
- Tables created successfully
- RLS policies not blocking access

**Fix:**
```python
# In app.py, verify:
supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
```

### Issue 3: Google Maps not loading
**Check:**
- API key in template: `{{ google_maps_api_key }}`
- API key passed from Flask route
- Required APIs enabled in Google Cloud

**Fix:**
```python
# In app.py, trips_page route:
@app.route('/trips')
@login_required
def trips_page():
    return render_template('trips.html', google_maps_api_key=GOOGLE_MAPS_API_KEY)
```

### Issue 4: Companies not showing
**Check:**
- Companies have `latitude` and `longitude` fields
- Geocoding completed
- Data loaded in planning page

**Fix:**
```python
# Run geocoding script if needed
python geocode_companies.py
```

### Issue 5: "Route optimizer not available"
**Check:**
- `route_optimizer.py` exists
- File imported in `app.py`
- No syntax errors

**Fix:**
```python
# In app.py, check imports:
try:
    from route_optimizer import optimize_trip_route
except Exception as e:
    print(f"Route optimizer import error: {e}")
    optimize_trip_route = None
```

---

## 📊 Performance Benchmarks

Expected performance on typical hardware:

| Stops | Optimization Time | Map Loading | Total Time |
|-------|------------------|-------------|------------|
| 5     | < 1 sec          | 1-2 sec     | 2-3 sec    |
| 10    | 1-3 sec          | 2-3 sec     | 4-6 sec    |
| 15    | 3-5 sec          | 2-4 sec     | 6-9 sec    |
| 20    | 5-10 sec         | 3-5 sec     | 10-15 sec  |

**Note:** First load may be slower due to API initialization

---

## 🎯 Next Steps

After successful setup:

1. **Import Real Data**
   - Ensure all companies are geocoded
   - Verify address accuracy
   - Update any missing coordinates

2. **Test with Real Routes**
   - Create actual sales routes
   - Compare with manual planning
   - Measure distance savings

3. **Train Team**
   - Share TRIPS_FEATURE_GUIDE.md
   - Demo the workflow
   - Collect feedback

4. **Monitor Usage**
   - Track trip creation
   - Monitor optimization performance
   - Identify common patterns

5. **Iterate & Improve**
   - Add requested features
   - Optimize based on usage
   - Expand functionality

---

## 📞 Support

If you encounter issues:

1. **Check logs:** Look for errors in terminal
2. **Browser console:** Check for JavaScript errors
3. **Database:** Verify data integrity in Supabase
4. **API limits:** Check Google Maps quota usage
5. **Documentation:** Review TRIPS_FEATURE_GUIDE.md

---

## ✅ Setup Complete!

If all tests pass, you're ready to use the Trips feature!

**Quick links:**
- Planning page: `http://localhost:5002/planning`
- Trips page: `http://localhost:5002/trips`
- API docs: See TRIPS_FEATURE_GUIDE.md

**Happy optimizing! 🗺️✨**

