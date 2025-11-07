# Alerts System - Quick Setup Guide

## 🚀 Complete in 3 Steps!

---

## Step 1: Create Database Table (2 minutes)

### Option A: Via Supabase Dashboard
1. Go to https://supabase.com
2. Open your project
3. Navigate to **SQL Editor**
4. Copy the entire contents of `create_alerts_table.sql`
5. Paste into SQL Editor
6. Click **Run** or press `Ctrl+Enter`
7. Wait for "Success" message

### Option B: Via Command Line
```bash
psql -h YOUR_SUPABASE_HOST -U postgres -d postgres < create_alerts_table.sql
```

### Verify Table Creation
```sql
-- Run this in SQL Editor
SELECT COUNT(*) FROM customer_alerts;
-- Should return: 0 (table exists but empty)
```

---

## Step 2: Generate Initial Alerts (1-2 minutes)

1. **Start your Flask app** (if not running):
   ```bash
   cd /Users/hendrikdewinne/MOTHERSHIP_PROSPECTING
   source venv/bin/activate
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5002/alerts
   ```

3. **Click "Recalculate Alerts"** button (blue button at top)

4. **Wait** for analysis to complete (30-60 seconds)
   - You'll see a loading spinner
   - Success message will show:
     ```
     Analysis complete! X new alerts detected, Y updated.
     ```

5. **Page will automatically reload** showing all alerts

---

## Step 3: Set Up Auto-Updates (Optional, 5 minutes)

### For Mac/Linux (Cron Job)

1. **Open terminal**

2. **Edit crontab**:
   ```bash
   crontab -e
   ```

3. **Add this line** (updates every 6 hours):
   ```bash
   0 */6 * * * curl -X POST http://localhost:5002/api/alerts/refresh >/dev/null 2>&1
   ```

4. **Save and exit** (`:wq` in vim, `Ctrl+X` then `Y` in nano)

### For Windows (Task Scheduler)

1. Open **Task Scheduler**
2. Click **Create Basic Task**
3. Name: "Update Customer Alerts"
4. Trigger: Daily
5. Action: Start a program
6. Program: `curl`
7. Arguments: `-X POST http://localhost:5002/api/alerts/refresh`
8. Finish

### Alternative: Manual Updates

Just click the **"Recalculate Alerts"** button whenever you want fresh data!

---

## ✅ Verification Checklist

- [ ] Table `customer_alerts` exists in Supabase
- [ ] Alerts page loads without errors
- [ ] "Recalculate Alerts" button generates alerts
- [ ] Alerts display with cards and metrics
- [ ] "Dismiss" button works and removes alerts
- [ ] "Contact" button opens email and marks actioned
- [ ] Page reloads quickly (1-2 seconds)

---

## 🎯 Quick Test

1. **Navigate to Alerts page**
2. **Should see:** Summary dashboard, alert cards
3. **Click any alert card:** Modal with details opens
4. **Click "Dismiss":** Alert disappears
5. **Click "Reload":** Alert is still gone (persisted!)
6. **Click "Recalculate Alerts":** Fresh analysis runs

---

## 📊 Usage Tips

### Daily Workflow
1. **Morning:** Check alerts page
2. **Review HIGH priority** alerts first
3. **Contact customers** via "Contact" button
4. **Dismiss** resolved alerts
5. **Export** weekly reports if needed

### When to Recalculate
- ✅ After syncing new invoices
- ✅ At start of work day
- ✅ Before sales meetings
- ✅ After major customer changes
- ❌ Not needed on every page load (uses database!)

### Filter Like a Pro
```
Search: "restaurant"  → Find restaurant customers
Priority: HIGH        → Focus on urgent issues
Type: HIGH_VALUE_AT_RISK  → Protect revenue
Sort By: Lifetime Value   → Prioritize by $$$
```

---

## 🔧 Troubleshooting

### "Table does not exist"
**Fix:** Run Step 1 again (create_alerts_table.sql)

### "No alerts showing"
**Fix:** Click "Recalculate Alerts" to generate data

### "Page is slow"
**Fix:** Make sure you're clicking "Reload" (fast) not "Recalculate" (slow)

### "Dismissed alerts keep coming back"
**Fix:** They should stay dismissed. If not:
```sql
-- Check alert status
SELECT id, company_name, status FROM customer_alerts WHERE id = YOUR_ALERT_ID;
```

---

## 📈 Next Steps

Once alerts are running:

1. **Review Weekly**
   - Export alerts to CSV
   - Track response times
   - Measure customer retention

2. **Adjust Thresholds** (optional)
   - Edit `app.py` line ~6135 onwards
   - Customize what triggers alerts
   - Restart Flask app

3. **Team Training**
   - Show team the alerts page
   - Explain priority levels
   - Demonstrate workflows

4. **Integrate with CRM** (advanced)
   - Use API endpoints
   - Auto-create tasks
   - Sync with Salesforce/HubSpot

---

## 🎉 You're Done!

Your intelligent alert system is now:
- ✅ Analyzing all customers
- ✅ Detecting 7 types of patterns
- ✅ Storing data persistently
- ✅ Tracking actions and dismissals
- ✅ Ready for daily use

### Need Help?

Refer to these docs:
- `COMPREHENSIVE_ALERTS_SYSTEM.md` - Full algorithm details
- `ALERTS_DATABASE_SYSTEM.md` - Database & API reference
- `ALERTS_UPGRADE_SUMMARY.md` - What's new overview

---

**Setup Time:** ~5 minutes  
**ROI:** Catch churning customers before they're gone  
**Effort:** Minimal (auto-updates!)  

Happy alerting! 🚀

