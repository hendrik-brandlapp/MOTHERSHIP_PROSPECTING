# Invoice Sync & Display Fix

## Problem
New invoices were being successfully added to the `sales_2025` and `sales_2024` tables in the database, but they weren't showing up in the frontend. This was because the frontend displays data from the `companies` table, which contains pre-calculated aggregate metrics (revenue totals, invoice counts, etc.) that weren't being updated after syncing new invoices.

## Root Cause
The application uses two data structures:
1. **Invoice Tables** (`sales_2024`, `sales_2025`) - Store individual invoice records
2. **Companies Table** (`companies`) - Stores aggregated company data with pre-calculated metrics

When new invoices were synced, only the invoice tables were updated. The companies table metrics remained stale, causing the frontend to show outdated information.

## Solution Implemented

### 1. **Automatic Metrics Recalculation**
Created a new function `recalculate_company_metrics_from_invoices()` that:
- Reads invoice data from both 2024 and 2025 tables
- Calculates fresh aggregates for each company:
  - `total_revenue_2024`, `total_revenue_2025`, `total_revenue_all_time`
  - `invoice_count_2024`, `invoice_count_2025`, `invoice_count_all_time`
  - `average_invoice_value`
  - `first_invoice_date`, `last_invoice_date`
- Updates the companies table with the new values

### 2. **Auto-Refresh After Sync**
Modified both sync endpoints to automatically trigger metrics recalculation:
- `/api/sync-2025-invoices` - Now updates company metrics after syncing 2025 invoices
- `/api/sync-2024-invoices` - Now updates company metrics after syncing 2024 invoices

### 3. **Manual Refresh Button**
Added a new "Refresh Metrics" button in the Data page that allows manual recalculation of company metrics without re-fetching data from the API. This is useful when:
- You want to verify metrics are accurate
- The auto-refresh fails for some reason
- You've made manual database changes

### 4. **Resource Exhaustion Fixes** (Bonus)
Also fixed the `[Errno 35] Resource temporarily unavailable` errors by adding:
- Rate limiting (pauses every 10/50 operations)
- Retry logic with exponential backoff (3 retries per operation)
- Better error filtering (suppresses noisy resource errors)

## How It Works Now

### Daily Sync Workflow:
1. User clicks "Daily Sync" button
2. System fetches latest invoices from DOUANO API
3. New/updated invoices are saved to `sales_2025` table
4. **✨ NEW:** System automatically recalculates company metrics
5. Companies table is updated with fresh totals
6. Frontend displays updated data (auto-refreshes after 2 seconds)

### Manual Refresh Workflow:
1. User clicks "Refresh Metrics" button
2. System recalculates all company aggregates from invoice tables
3. Companies table is updated
4. Frontend displays updated data (auto-refreshes after 1.5 seconds)

## New API Endpoints

### `POST /api/refresh-company-metrics`
Manually triggers recalculation of company metrics from invoice data.

**Response:**
```json
{
  "success": true,
  "message": "Company metrics recalculated successfully"
}
```

## Testing

### Test the Fix:
1. Navigate to the Data page
2. Click "Daily Sync" to fetch new invoices
3. Wait for the sync to complete (green success message)
4. Observe the "Company metrics are being automatically updated..." message
5. Page will auto-refresh showing updated invoice counts and revenue totals

### Verify Metrics:
1. Click "Refresh Metrics" button at any time
2. System will recalculate all metrics from scratch
3. Updated data will display automatically

## Benefits

✅ **Automatic Updates** - No manual intervention needed after syncing  
✅ **Data Consistency** - Company metrics always reflect actual invoice data  
✅ **Performance** - Metrics calculated from database (no API calls)  
✅ **Reliability** - Retry logic handles temporary failures  
✅ **Transparency** - Clear UI feedback about what's happening  
✅ **Flexibility** - Manual refresh option available when needed  

## Files Modified

- **app.py**: 
  - Added `recalculate_company_metrics_from_invoices()` function
  - Updated `/api/sync-2025-invoices` endpoint
  - Updated `/api/sync-2024-invoices` endpoint
  - Added `/api/refresh-company-metrics` endpoint
  - Fixed resource exhaustion errors with retry logic

- **templates/data.html**:
  - Added "Refresh Metrics" button
  - Added `refreshCompanyMetrics()` JavaScript function
  - Updated sync success messages to show auto-refresh status

## Notes

- The metrics recalculation processes ALL companies, so it may take 10-30 seconds depending on the database size
- The frontend automatically refreshes data after recalculation completes
- If you see outdated data, use "Refresh Metrics" button to force an update
- The "Populate Companies DB" button is still available for full company data refresh from the DOUANO API (includes addresses, categories, etc.)

---

**Created:** October 10, 2025  
**Author:** AI Assistant  
**Status:** ✅ Implemented & Ready for Use

