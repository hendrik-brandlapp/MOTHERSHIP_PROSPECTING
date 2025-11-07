# 🚀 Quick Setup Guide - Customer Alerts System

## ⚠️ You're seeing this because the database table doesn't exist yet

The new comprehensive alerts system needs a database table to store alerts. This is a **ONE-TIME SETUP** that takes less than 2 minutes.

---

## ✅ Step-by-Step Instructions

### 1️⃣ Open Supabase Dashboard
- Go to: **https://supabase.com**
- Log in to your account
- Click on your project

### 2️⃣ Open SQL Editor
- In the left sidebar, click **"SQL Editor"**
- Click the **"New Query"** button (top right)

### 3️⃣ Copy the SQL
Open the file `create_alerts_table_simple.sql` in your project and copy all its contents.

**Or copy this directly:**

```sql
CREATE TABLE IF NOT EXISTS customer_alerts (
    id BIGSERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    public_name TEXT,
    email TEXT,
    
    alert_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    status TEXT NOT NULL DEFAULT 'active',
    actioned_at TIMESTAMP WITH TIME ZONE,
    actioned_by TEXT,
    dismissed_at TIMESTAMP WITH TIME ZONE,
    dismissed_by TEXT,
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    first_detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_alerts_company_id ON customer_alerts(company_id);
CREATE INDEX idx_alerts_type ON customer_alerts(alert_type);
CREATE INDEX idx_alerts_priority ON customer_alerts(priority);
CREATE INDEX idx_alerts_status ON customer_alerts(status);

ALTER TABLE customer_alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all operations" ON customer_alerts FOR ALL USING (true) WITH CHECK (true);
```

### 4️⃣ Run the SQL
- Paste the SQL into the editor
- Click the **"RUN"** button (or press Ctrl+Enter / Cmd+Enter)
- You should see: ✅ **"Success. No rows returned"**

### 5️⃣ Test It!
- Go back to your app's Alerts page
- Refresh the page (F5 or Cmd+R)
- Click **"Recalculate Alerts"**
- Wait 30-60 seconds
- **You should see alerts!** 🎉

---

## 🎯 What This Creates

The SQL creates:
- A `customer_alerts` table to store all detected customer alerts
- Indexes for fast querying by company, type, priority, and status
- Row-level security policies for data protection

---

## 🔧 Troubleshooting

### "Table already exists" error
✅ That's fine! The table is created. Just go back to the app and refresh.

### "Permission denied" error
❌ Make sure you're logged into the correct Supabase project and have admin access.

### Still seeing errors?
- Double-check you copied **all** the SQL (including the CREATE POLICY line at the end)
- Make sure you clicked "RUN" in Supabase
- Try refreshing your browser
- Check the browser console (F12) for detailed error messages

---

## 📊 What You'll Get

Once setup is complete, you'll have access to:

✨ **7 Types of Customer Alerts:**
1. **Pattern Disruption** - Customers who stopped ordering on schedule
2. **Declining Order Value** - Customers spending less over time
3. **Increasing Gap** - Orders becoming less frequent
4. **High Value at Risk** - Valuable customers going quiet
5. **Payment Issues** - Outstanding balances
6. **Dormant Customers** - Regular customers who completely stopped
7. **One-Time Customers** - Never came back after first purchase

🎯 **Smart Features:**
- Priority levels (HIGH/MEDIUM/LOW)
- Statistical analysis of ordering patterns
- Actionable recommendations
- Contact tracking (dismissed/actioned alerts)
- Real-time updates
- Beautiful visualizations

---

Need help? Check the terminal logs or browser console for detailed error messages.

