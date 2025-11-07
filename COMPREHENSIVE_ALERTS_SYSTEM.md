# Comprehensive Alerts System

## Overview
The alerts system has been completely overhauled with advanced pattern detection algorithms, multiple alert types, and a premium UI/UX design. This system proactively identifies customer issues, opportunities, and risks before they become problems.

## 🎯 Alert Types

### 1. **Pattern Disruption**
**Priority:** HIGH or MEDIUM  
**What it detects:** Customers who typically order on a regular schedule but are now overdue for their next order.

**Algorithm:**
- Calculates average interval between orders
- Computes standard deviation to understand variability
- Flags customers who are more than 2 standard deviations overdue
- Must be at least 14 days late to trigger

**Example:** "Customer typically orders every 30 days but is now 45 days overdue"

**Metrics Shown:**
- Total orders
- Average interval days
- Days since last order
- Days overdue
- Last order amount
- Total lifetime value

---

### 2. **High Value at Risk**
**Priority:** HIGH  
**What it detects:** High-value customers (>€5,000 lifetime value) who haven't ordered in 60+ days.

**Algorithm:**
- Sums total lifetime revenue
- Checks if customer has been inactive for 60+ days
- Prioritizes customers with highest lifetime value

**Example:** "High-value customer (€12,450 lifetime) has been inactive for 87 days"

**Metrics Shown:**
- Total orders
- Lifetime value
- Average order value
- Days since last order

---

### 3. **Dormant Customer**
**Priority:** HIGH  
**What it detects:** Previously regular customers (5+ orders) who have completely stopped ordering for 120+ days.

**Algorithm:**
- Requires at least 5 historical orders
- Customer must be inactive for 120+ days
- Indicates a lost customer who needs win-back

**Example:** "Regular customer (12 orders) has been dormant for 156 days"

**Metrics Shown:**
- Total orders
- Lifetime value
- Days since last order

---

### 4. **Declining Order Value**
**Priority:** MEDIUM  
**What it detects:** Customers whose recent order values are significantly lower than their historical average.

**Algorithm:**
- Requires at least 4 orders
- Compares average of last 3 orders vs earlier orders
- Triggers if decline is >20%

**Example:** "Order value has declined by 35% in recent orders"

**Metrics Shown:**
- Total orders
- Earlier average value
- Recent average value
- Decline percentage

---

### 5. **Increasing Gap**
**Priority:** MEDIUM  
**What it detects:** Customers who are ordering less frequently over time.

**Algorithm:**
- Requires at least 4 orders to establish pattern
- Compares recent intervals vs historical intervals
- Triggers if gap has increased by 30+ days

**Example:** "Time between orders has increased by 45 days"

**Metrics Shown:**
- Total orders
- Earlier average gap
- Recent average gap
- Gap increase in days

---

### 6. **One-Time Customer**
**Priority:** MEDIUM  
**What it detects:** Customers who made only one purchase 90+ days ago and never returned.

**Algorithm:**
- Customer has exactly 1 order
- Order was placed 90+ days ago
- Opportunity for follow-up and retention

**Example:** "Customer made only one purchase 127 days ago and never returned"

**Metrics Shown:**
- First order date
- First order amount
- Days since order

---

### 7. **Payment Issues**
**Priority:** HIGH  
**What it detects:** Customers with significant outstanding balances (>€500).

**Algorithm:**
- Sums unpaid balance across all invoices
- Triggers if total outstanding >€500
- May indicate cash flow problems

**Example:** "Outstanding balance of €1,250 across multiple invoices"

**Metrics Shown:**
- Total orders
- Outstanding balance
- Last order date

---

## 🎨 UI/UX Improvements

### Visual Design
- **Modern Card Layout:** Each alert displayed in a beautifully designed card
- **Color-Coded Priority:** Red (High), Yellow (Medium), Blue (Low)
- **Pulsing Indicators:** High-priority alerts have pulsing red dots
- **Hover Effects:** Cards lift and highlight on hover
- **Responsive Design:** Works perfectly on all screen sizes

### Dashboard Overview
- **Summary Cards:** Total alerts, high priority, medium priority counts
- **Alert Type Chart:** Visual bar chart showing distribution of alert types
- **Real-Time Timestamp:** Shows when analysis was last performed

### Advanced Filtering
- **Search:** Filter by company name
- **Priority Filter:** Show only HIGH, MEDIUM, or LOW priority alerts
- **Type Filter:** Filter by specific alert type
- **Sorting Options:**
  - Priority (default)
  - Days since last order
  - Lifetime value
  - Company name

### Alert Cards
Each card displays:
- Company name and public name
- Priority badge
- Alert type badge
- Problem description
- Key metrics (days, orders, lifetime value)
- AI recommendation
- Action buttons (Contact, View, Dismiss)

### Detail Modal
Click any alert card to see:
- Full alert details
- Complete metrics table
- Contact information
- Formatted recommendations
- Direct contact button

---

## 📊 Algorithm Details

### Pattern Detection Logic

**1. Statistical Analysis**
```python
avg_interval = mean(intervals)
std_interval = stdev(intervals)
expected_next = last_order_date + avg_interval
days_overdue = current_date - expected_next

if days_overdue > (2 * std_interval) and days_overdue > 14:
    trigger_alert()
```

**2. Trend Analysis**
```python
recent_avg = mean(last_3_orders)
earlier_avg = mean(earlier_orders)
decline_pct = ((recent_avg - earlier_avg) / earlier_avg) * 100

if decline_pct < -20%:
    trigger_declining_value_alert()
```

**3. Value Segmentation**
- High-value customers: >€5,000 lifetime
- Regular customers: 5+ orders
- One-time customers: 1 order only

---

## 🚀 Action Workflows

### Per Alert Actions
1. **Contact Customer**
   - Opens pre-filled email template
   - Includes company name in subject
   - Professional follow-up template

2. **View Company**
   - Navigates to company details in Data page
   - Shows full order history
   - Displays all invoices

3. **Dismiss Alert**
   - Removes alert from current view
   - Can be enhanced to persist dismissals

### Bulk Actions
- **Export to CSV:** Download all filtered alerts with key metrics
- **Print:** Print-friendly format for reports
- **Share:** Email alert summary to team

---

## 📈 Performance Optimizations

### Rate Limiting
- Processes 10 companies at a time
- 100ms pause between batches
- Prevents database overload

### Retry Logic
- 3 retry attempts per database query
- Exponential backoff (50ms, 100ms, 200ms)
- Graceful error handling

### Efficient Queries
- Batched database requests
- Minimal data transfer
- Indexed company IDs

---

## 🎯 Use Cases

### For Sales Teams
- Identify customers to contact for immediate wins
- Prioritize outreach based on value and urgency
- Track customer engagement trends

### For Account Managers
- Monitor health of key accounts
- Identify at-risk relationships early
- Plan proactive retention campaigns

### For Management
- Understand customer churn patterns
- Measure customer lifetime value trends
- Identify opportunities for improvement

---

## 🔧 Technical Implementation

### Backend Endpoint
**`GET /api/comprehensive-alerts`**

Returns:
```json
{
  "alerts": [
    {
      "type": "PATTERN_DISRUPTION",
      "priority": "HIGH",
      "company_id": 12345,
      "company_name": "Company Name",
      "email": "contact@company.com",
      "description": "Customer typically orders...",
      "recommendation": "Immediate outreach...",
      "metrics": {
        "total_orders": 15,
        "days_since_last_order": 45,
        ...
      }
    }
  ],
  "summary": {
    "total_alerts": 127,
    "high_priority": 34,
    "medium_priority": 68,
    "low_priority": 25,
    "by_type": {
      "PATTERN_DISRUPTION": 42,
      "HIGH_VALUE_AT_RISK": 18,
      ...
    }
  },
  "analysis_date": "2025-10-10 14:30:00",
  "companies_analyzed": 523
}
```

### Frontend Components
- **Chart.js:** For data visualizations
- **Bootstrap 5:** For responsive layout
- **Font Awesome:** For icons
- **Custom CSS:** For animations and styling

---

## 📖 How to Use

### Step 1: Navigate to Alerts
Click "Alerts" in the main navigation menu.

### Step 2: Review Dashboard
Check the overview statistics to understand the current alert landscape.

### Step 3: Filter Alerts
Use the filter controls to focus on:
- Specific priorities (e.g., HIGH only)
- Specific alert types (e.g., High Value at Risk)
- Search for specific companies

### Step 4: Review Alert Cards
Each card shows:
- Problem description
- Key metrics
- AI-powered recommendation

### Step 5: Take Action
Click action buttons to:
- **Contact:** Send email directly
- **View:** See full company details
- **Dismiss:** Remove from view

### Step 6: Export Results
Download CSV for:
- Team meetings
- Reports
- CRM integration

---

## 🎨 Customization Options

### Thresholds (in app.py)
```python
# Pattern disruption
if days_overdue > (std_interval * 2) and days_overdue > 14:

# High value threshold
if total_value > 5000 and days_since_last > 60:

# Dormant customer
if len(all_invoices) >= 5 and days_since_last > 120:

# Declining value threshold
if decline_pct < -20:  # 20%+ decline

# Increasing gap threshold
if gap_increase > 30:  # 30+ days

# One-time customer threshold
if days_since > 90:  # 90+ days

# Payment issues threshold
if unpaid_balance > 500:  # €500+
```

You can adjust these values based on your business needs.

---

## 📊 Example Scenarios

### Scenario 1: Restaurant Supply Company
**Alert:** Pattern Disruption  
**Customer:** "Le Petit Bistro"  
**Issue:** Usually orders weekly, now 3 weeks overdue  
**Action:** Immediate call to check if they've switched suppliers  
**Outcome:** Discovered they closed for renovations, order resumed after reopening

### Scenario 2: Manufacturing Parts
**Alert:** High Value at Risk  
**Customer:** "AutoParts International"  
**Issue:** €45K lifetime value, inactive 75 days  
**Action:** VIP outreach with exclusive discount  
**Outcome:** Renewed contract with increased order volume

### Scenario 3: Office Supplies
**Alert:** Declining Order Value  
**Customer:** "TechStart Inc"  
**Issue:** Order value dropped from €500 to €200 average  
**Action:** Account review meeting  
**Outcome:** Discovered team downsizing, adjusted expectations

---

## 🔮 Future Enhancements

Potential additions:
- Machine learning predictions
- Automated email campaigns
- CRM integration
- Custom alert rules
- Alert notifications (email/SMS)
- Historical trend charts
- Competitor analysis
- Seasonal adjustment factors

---

## ✅ Summary

The comprehensive alerts system provides:
- ✨ 7 different alert types
- 🎯 AI-powered recommendations
- 📊 Beautiful visualizations
- 🔍 Advanced filtering & search
- 📈 Performance optimized
- 💼 Actionable workflows
- 📱 Responsive design
- 🎨 Modern UI/UX

This system transforms passive data into proactive customer intelligence, helping you retain valuable customers and maximize lifetime value.

---

**Created:** October 10, 2025  
**Status:** ✅ Production Ready  
**API Endpoint:** `/api/comprehensive-alerts`  
**Frontend:** `templates/alerts.html`

