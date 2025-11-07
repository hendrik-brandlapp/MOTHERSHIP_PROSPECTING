# 2025 Sales Invoice Data Extraction

This feature extracts all raw sales invoice data from 2025 and stores it in a Supabase database for analysis and reporting.

## Overview

The system provides multiple ways to sync 2025 invoice data:

1. **Web Interface** - Easy-to-use UI with one-click sync
2. **Command Line Script** - Standalone Python script for automation
3. **API Endpoints** - Programmatic access for integrations

## Database Structure

### Table: `sales_2025`

Stores raw invoice data with the following fields:

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key (auto-increment) |
| `invoice_id` | INTEGER | Unique invoice ID from Douano |
| `invoice_data` | JSONB | Complete raw JSON data from API |
| `company_id` | INTEGER | Company ID |
| `company_name` | TEXT | Company name |
| `invoice_number` | TEXT | Invoice number |
| `invoice_date` | DATE | Invoice date |
| `due_date` | DATE | Payment due date |
| `total_amount` | DECIMAL | Total invoice amount |
| `balance` | DECIMAL | Outstanding balance |
| `is_paid` | BOOLEAN | Payment status |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Record update time |

## Setup Instructions

### 1. Create the Database Table

Run the SQL migration in your Supabase SQL editor:

```bash
# Copy the contents of create_2025_sales_table.sql
# and execute it in Supabase SQL Editor
```

Or using psql:
```bash
psql -h gpjoypslbrpvnhqzvacc.supabase.co -U postgres -d postgres < create_2025_sales_table.sql
```

### 2. Configure Environment Variables

Ensure these variables are set in your `.env` file:

```env
DOUANO_ACCESS_TOKEN=your_access_token_here
SUPABASE_URL=https://gpjoypslbrpvnhqzvacc.supabase.co
SUPABASE_ANON_KEY=your_supabase_key_here
```

## Usage

### Method 1: Web Interface (Recommended)

1. Navigate to the **2025 Sales Data** page in your app
2. Click the "Start Sync" button
3. Wait for the sync to complete
4. View statistics and results

**URL:** `http://localhost:5002/sales-2025`

### Method 2: Command Line Script

Run the standalone Python script:

```bash
python3 sync_2025_invoices.py
```

This will:
- Fetch all 2025 invoices from Douano API
- Save them to Supabase
- Create a JSON backup file (`2025_invoices_backup.json`)

### Method 3: API Endpoints

#### Sync Invoices
```bash
curl -X POST http://localhost:5002/api/sync-2025-invoices \
  -H "Content-Type: application/json"
```

#### Get Statistics
```bash
curl http://localhost:5002/api/2025-sales-stats
```

## API Response Examples

### Sync Response
```json
{
  "success": true,
  "total_fetched": 150,
  "saved": 120,
  "updated": 30,
  "errors": 0,
  "message": "Successfully synced 150 invoices"
}
```

### Stats Response
```json
{
  "total_invoices": 150,
  "total_revenue": 125000.50,
  "total_outstanding": 15000.00,
  "paid_invoices": 130,
  "unpaid_invoices": 20,
  "unique_companies": 45
}
```

## Features

### ✅ What It Does

- **Fetches All 2025 Invoices** - Retrieves complete invoice data via pagination
- **Stores Raw JSON** - Preserves complete API response for future analysis
- **Extracts Key Fields** - Makes common fields easily queryable
- **Handles Updates** - Updates existing records, inserts new ones
- **Creates Backups** - JSON backup file when using CLI script
- **Provides Statistics** - Real-time stats on synced data

### 🔍 Data Integrity

- **Unique Constraint** - Prevents duplicate invoices (by `invoice_id`)
- **Atomic Operations** - Insert or update in single transaction
- **Error Handling** - Continues processing even if individual records fail
- **Audit Trail** - Tracks `created_at` and `updated_at` timestamps

## Querying the Data

### Example SQL Queries

#### Get Total Revenue by Company
```sql
SELECT 
  company_name,
  COUNT(*) as invoice_count,
  SUM(total_amount) as total_revenue,
  SUM(balance) as outstanding
FROM sales_2025
GROUP BY company_name
ORDER BY total_revenue DESC;
```

#### Find Overdue Invoices
```sql
SELECT 
  invoice_number,
  company_name,
  invoice_date,
  due_date,
  balance
FROM sales_2025
WHERE is_paid = false 
  AND due_date < CURRENT_DATE
ORDER BY due_date;
```

#### Query Raw JSON Data
```sql
SELECT 
  invoice_number,
  invoice_data->>'buyer_name' as buyer,
  invoice_data->'invoice_line_items' as line_items
FROM sales_2025
WHERE company_id = 123;
```

## Automation

### Cron Job Setup

To sync data automatically every day:

```bash
# Edit crontab
crontab -e

# Add this line to sync at 6 AM daily
0 6 * * * cd /path/to/MOTHERSHIP_PROSPECTING && /usr/bin/python3 sync_2025_invoices.py >> /var/log/sales_sync.log 2>&1
```

## Troubleshooting

### Common Issues

1. **Authentication Error**
   - Check `DOUANO_ACCESS_TOKEN` is valid
   - Verify token hasn't expired

2. **Supabase Connection Failed**
   - Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY`
   - Check network connectivity
   - Ensure table exists (run migration)

3. **No Data Found**
   - Verify date filters (2025-01-01 to 2025-12-31)
   - Check if invoices exist in Douano

4. **Duplicate Key Errors**
   - This is normal - duplicate invoices are updated
   - Check logs for other error types

## Performance Notes

- **Pagination** - Fetches 100 invoices per page
- **Batch Processing** - Processes all pages sequentially
- **Network Dependent** - Speed depends on API response time
- **Typical Duration** - 1-5 minutes for 100-500 invoices

## Security

- ✅ Requires authentication (OAuth token)
- ✅ Row Level Security (RLS) enabled on table
- ✅ Only authenticated users can read data
- ✅ Service role required for write operations

## Support

For issues or questions:
1. Check application logs: `flask.log`
2. Review Supabase logs in dashboard
3. Verify API connectivity with Douano

## Future Enhancements

Potential improvements:
- [ ] Add filtering by date range
- [ ] Export to CSV/Excel
- [ ] Email notifications on sync completion
- [ ] Dashboard with charts and analytics
- [ ] Compare year-over-year data
- [ ] Scheduled automatic syncs

