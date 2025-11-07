# Quick Start: 2025 Sales Invoice Sync

## 🚀 Get Started in 3 Steps

### Step 1: Create the Database Table

Execute this SQL in your Supabase SQL Editor:

```bash
# Open: https://supabase.com/dashboard/project/gpjoypslbrpvnhqzvacc/sql

# Then paste and run the contents of:
create_2025_sales_table.sql
```

### Step 2: Access the Web Interface

Navigate to: **http://localhost:5002/sales-2025**

### Step 3: Click "Start Sync"

That's it! The system will:
- ✅ Fetch all 2025 invoices from Douano
- ✅ Store raw JSON data in Supabase
- ✅ Extract key fields for easy querying
- ✅ Show you statistics

## 📊 What You Get

### Real-time Statistics
- Total invoices for 2025
- Total revenue
- Outstanding balances
- Paid vs unpaid invoices
- Number of unique companies

### Raw Data Storage
Every invoice is stored as complete JSON in the `invoice_data` field, so you can query any field later.

## 🔄 Alternative: Command Line

If you prefer command line:

```bash
python3 sync_2025_invoices.py
```

This also creates a backup JSON file: `2025_invoices_backup.json`

## 📝 Example Queries

### Get Top Customers by Revenue
```sql
SELECT 
  company_name,
  COUNT(*) as invoices,
  SUM(total_amount) as revenue
FROM sales_2025
GROUP BY company_name
ORDER BY revenue DESC
LIMIT 10;
```

### Find Unpaid Invoices
```sql
SELECT 
  invoice_number,
  company_name,
  total_amount,
  balance,
  due_date
FROM sales_2025
WHERE is_paid = false
ORDER BY due_date;
```

## 🆘 Need Help?

See the full documentation: `SALES_2025_README.md`

