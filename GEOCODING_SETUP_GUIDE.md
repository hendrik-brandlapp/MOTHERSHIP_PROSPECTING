# Geocoding Setup Guide

## Overview

This guide explains the new geocoding feature that enables efficient visualization of companies and prospects on the Planning page map.

## What Changed

### 1. Navigation Updates ✅
- **Tab renamed**: "Data" is now called "**Companies**" with a building icon
- **Tab order**: Companies → Alerts → Planning → Tasks → Prospecting
- **Hidden tabs**: CRM and Analytics are now hidden for a cleaner interface

### 2. Planning Page Improvements ✅
- **Map layout**: Map now displayed at the top in a more square format (full width, 500px height)
- **Better organization**: Selection controls on the left (7 columns), details panel on the right (5 columns)
- **Improved UX**: Company/prospect lists are more compact (300px max height)

### 3. Database Geocoding Feature ✅

#### New Database Columns
Added to `companies` table:
- `latitude` (DECIMAL 10,8) - Latitude coordinate
- `longitude` (DECIMAL 11,8) - Longitude coordinate  
- `geocoded_address` (TEXT) - The address that was geocoded
- `geocoding_quality` (TEXT) - Quality indicator (exact, approximate, city, etc.)
- `geocoded_at` (TIMESTAMP) - When geocoding was performed
- `geocoding_provider` (TEXT) - Service used (default: 'mapbox')

#### Performance Benefits
- **Before**: Every map load required geocoding addresses on-the-fly (slow, rate-limited)
- **After**: Coordinates stored in database, instant map loading
- **Fallback**: If no coordinates exist, still geocodes on-the-fly

## Setup Instructions

### Step 1: Apply Database Migration

Run the SQL migration to add geocoding columns:

```bash
# Copy the SQL file contents
cat add_geocoding_columns.sql

# Then run in Supabase SQL Editor or via psql
psql -h <your-supabase-host> -U postgres -d postgres -f add_geocoding_columns.sql
```

Or manually run in Supabase Dashboard → SQL Editor:
1. Go to your Supabase project
2. Click "SQL Editor"
3. Paste contents of `add_geocoding_columns.sql`
4. Click "Run"

### Step 2: Configure Environment

Ensure your environment has the Mapbox API key:

```bash
# In your .env file or config.py
MAPBOX_API_KEY=pk.your_mapbox_public_key_here
```

### Step 3: Run Geocoding Script

Geocode all companies in the database:

```bash
# Activate your virtual environment
source venv/bin/activate  # or .\venv\Scripts\activate on Windows

# Install required packages (if not already installed)
pip install requests supabase

# Run the geocoding script
python geocode_companies.py
```

#### Geocoding Script Options

```bash
# Geocode all companies without coordinates (default)
python geocode_companies.py

# Geocode only first 10 companies (for testing)
python geocode_companies.py --limit 10

# Force re-geocode ALL companies (even if already geocoded)
python geocode_companies.py --force

# Combine options
python geocode_companies.py --limit 50 --force
```

#### What the Script Does

1. **Fetches companies** from database without coordinates
2. **Extracts addresses** from multiple possible fields:
   - `raw_company_data.invoice_address`
   - `addresses` JSONB array
   - Individual address fields (`address_line1`, `city`, etc.)
3. **Geocodes** using Mapbox Geocoding API
4. **Stores results** with quality indicators
5. **Rate limiting**: Respects API limits (10 requests/second)

#### Expected Output

```
🌍 Starting company geocoding process...
   Force mode: False
   Limit: None (all companies)
   Batch size: 50

📥 Fetching companies from database...
📊 Found 127 companies to geocode

[1/127] Processing: ACME Corporation (ID: 42)
  📍 Address: Sint-Sebastiaansstraat 68, Brussels, 1000, Belgium
  ✅ Geocoded: 50.8503421, 4.3517103 (quality: exact)
  💾 Updated database

[2/127] Processing: Example BV (ID: 43)
  📍 Address: Rue de la Loi 123, Brussels, 1040, Belgium
  ✅ Geocoded: 50.8429541, 4.3721008 (quality: exact)
  💾 Updated database

...

============================================================
📊 GEOCODING SUMMARY
============================================================
✅ Successfully geocoded: 115
❌ Failed to geocode:    8
⚠️  Skipped (no address): 4
📝 Total processed:      127
============================================================
```

## Using the Planning Page

### 1. Load Data
Click the **"Load Data"** button to fetch companies and prospects.

### 2. Select Items
- Switch between **Companies** and **Prospects** tabs
- Use **search** to filter by name or address
- **Select checkboxes** for items you want to visualize
- Use **"All"** / **"None"** buttons for bulk selection

### 3. Visualize on Map
Click **"Visualize"** button to add selected items to the map.

**What happens:**
- Items with database coordinates appear **instantly** ⚡
- Items without coordinates are **geocoded on-the-fly** (slower)
- Console shows: `"Using DB coordinates"` vs `"Geocoded on-the-fly"`

### 4. Interact with Map
- **Click markers** to see company/prospect details
- **Blue markers** = Companies
- **Green markers** = Prospects
- **Click company name** in list to zoom to its location
- Use **refresh button** to reload cache

## Geocoding Quality Indicators

The `geocoding_quality` field indicates accuracy:

| Quality | Description | Example |
|---------|-------------|---------|
| `exact` | Precise address or POI | Specific street address |
| `approximate` | Neighborhood/locality | General area |
| `postal_code` | Postcode level | ZIP code centroid |
| `city` | City level | City center |
| `region` | Regional level | Province/state |
| `country` | Country level | Country centroid |

## Maintenance

### Re-geocode Companies
When company addresses change, re-geocode them:

```bash
# Re-geocode specific companies (edit script to filter by ID)
python geocode_companies.py --limit 10

# Force re-geocode all companies
python geocode_companies.py --force
```

### Check Geocoding Status

Query in Supabase SQL Editor:

```sql
-- Count geocoded vs not geocoded
SELECT 
    COUNT(*) FILTER (WHERE geocoded_at IS NOT NULL) as geocoded,
    COUNT(*) FILTER (WHERE geocoded_at IS NULL) as not_geocoded,
    COUNT(*) as total
FROM companies;

-- See companies by quality
SELECT geocoding_quality, COUNT(*) as count
FROM companies
WHERE geocoded_at IS NOT NULL
GROUP BY geocoding_quality
ORDER BY count DESC;

-- Find companies without coordinates
SELECT id, name, city, address_line1
FROM companies
WHERE geocoded_at IS NULL
LIMIT 10;
```

### Update Mapbox API Key

If you need to change the Mapbox API key:

1. Update in `config.py` or `.env`:
   ```
   MAPBOX_API_KEY=pk.new_key_here
   ```

2. Restart Flask application:
   ```bash
   # Kill existing process, then:
   python app.py
   ```

## Troubleshooting

### Problem: "No results found" during geocoding

**Solutions:**
- Check if address is valid and complete
- Verify country bias in script (default: 'BE' for Belgium)
- Some addresses might be too vague (e.g., just a city name)

### Problem: Rate limiting errors

**Solutions:**
- Script already implements rate limiting (10 req/sec)
- If hitting limits, reduce `REQUESTS_PER_SECOND` in script
- Run in smaller batches using `--limit` option

### Problem: Map doesn't show markers

**Solutions:**
1. Check browser console for errors
2. Verify Mapbox API key is valid and loaded
3. Ensure companies have valid coordinates:
   ```sql
   SELECT * FROM companies WHERE latitude IS NOT NULL LIMIT 5;
   ```
4. Try clicking "Refresh" button on Planning page

### Problem: Coordinates seem wrong

**Solutions:**
1. Check `geocoding_quality` - might be low quality (city vs exact)
2. Verify address in database is correct
3. Re-geocode with `--force` flag:
   ```bash
   python geocode_companies.py --force --limit 10
   ```

## API Rate Limits

**Mapbox Geocoding API:**
- Free tier: 100,000 requests/month
- Rate limit: 600 requests/minute
- Script uses: 10 requests/second (conservative)

## Next Steps

Consider these enhancements:

1. **Batch geocoding endpoint** - Create API endpoint to trigger geocoding from UI
2. **Geocoding status dashboard** - Show which companies need geocoding
3. **Auto-geocode on import** - Geocode new companies automatically
4. **Route planning** - Calculate optimal routes between selected companies
5. **Clustering** - Group nearby companies on map for better visualization
6. **Export routes** - Export to Google Maps or other navigation apps

## Files Created/Modified

### New Files
- `add_geocoding_columns.sql` - Database migration
- `geocode_companies.py` - Geocoding script
- `GEOCODING_SETUP_GUIDE.md` - This guide

### Modified Files
- `templates/base.html` - Navigation updates
- `templates/planning.html` - Improved layout and geocoding logic

## Support

For issues or questions:
1. Check this guide first
2. Review console logs in browser (F12)
3. Check Flask application logs
4. Verify database schema with `\d companies` in psql

---

**Last Updated:** October 24, 2025

