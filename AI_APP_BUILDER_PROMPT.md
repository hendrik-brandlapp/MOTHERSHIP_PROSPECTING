# MOTHERSHIP PROSPECTING - Mobile App Builder Prompt

## App Overview

Build a **Field Sales CRM Mobile App** for a beverage distribution company's sales team. The app helps salespeople manage customer visits, track prospects through a sales pipeline, plan optimized routes, log visit notes with photos, and stay on top of tasks - all while on the road.

**Target Users**: Field sales representatives who visit retail locations (cafes, restaurants, shops) to sell kombucha/beverage products.

**Primary Use Case**: A salesperson plans their day's route, drives to locations, logs visit outcomes with notes/photos, updates customer status, and tracks their pipeline - all from their phone.

---

## Core Features & Screens

### 1. HOME DASHBOARD
**Purpose**: Quick overview of the day's work and key metrics

**Show**:
- Today's planned route with number of stops
- Tasks due today (with urgency indicators)
- Recent alerts requiring attention
- Quick stats: visits this week, pipeline value, conversion rate
- Quick action buttons: "Start Today's Route", "Add New Visit Note", "Log Quick Task"

---

### 2. COMPANIES / CUSTOMERS DATABASE
**Purpose**: Browse and search all companies in the territory

**Features**:
- Search by name, city, or category
- Filter by:
  - Customer status (active customer, prospect, ex-customer)
  - Category (cafe, restaurant, retail, etc.)
  - Revenue tier (high/medium/low)
  - Last visit date
  - Assigned salesperson
- Card view showing: company name, address, last order date, total revenue
- Tap to see full company detail

**Company Detail Screen**:
- Company info: name, address, contact person, phone, email
- Map showing location
- Revenue summary (2024, 2025, all-time)
- Invoice history
- Categories/tags
- **Visit Notes** - chronological list of all visit notes with photos
- **Add Visit Note** button - log new visit with text + photos
- Quick actions: Call, Navigate, Email, WhatsApp
- Edit company info (address, contact, categories)

---

### 3. PROSPECTS PIPELINE (Kanban-style)
**Purpose**: Track prospects through the sales funnel

**Pipeline Stages**:
1. **New Leads** - Not yet contacted
2. **First Contact** - Initial conversation done
3. **Meeting Planned** - Visit scheduled
4. **Follow-up** - Samples sent or tasting done
5. **Customer** - Now an active customer
6. **Ex-Customer** - Stopped ordering
7. **Contact Later** - Interested but timing not right (with reminder date)
8. **Unqualified** - Not a fit (with reason: no fridge space, too expensive, prefers competition, etc.)

**Features**:
- Drag-and-drop between stages (or swipe actions)
- Tap prospect to see detail/edit
- Add new prospect from company or manually
- Set priority level (1-5)
- Schedule follow-up tasks
- Filter by region, prospect type, priority

**Prospect Detail**:
- Company info linked
- Current stage + history of stage changes
- Notes and visit history
- Scheduled tasks
- Contact later date (if applicable)
- Unqualified reason (if applicable)

---

### 4. ROUTE PLANNING & TRIPS
**Purpose**: Plan and execute optimized daily routes

**Trip List Screen**:
- Upcoming trips by date
- Past trips with completion status
- Create new trip button

**Create/Edit Trip**:
- Trip name and date
- Start location (can use current location)
- Start time
- Add stops by:
  - Selecting from companies database
  - Selecting from prospects
  - Searching by address
- Reorder stops manually
- **Optimize Route** button - automatically reorder for shortest driving distance
- Estimated total distance and duration

**Active Trip Screen** (during the day):
- Map showing route with all stops
- List of stops in order with:
  - Company name
  - Address
  - Estimated arrival time
  - Checkbox to mark complete
- Current stop highlighted
- **Navigate** button - opens in Maps app
- **Add Visit Note** - quick note logging for current stop
- **Mark Complete** - moves to next stop
- Add notes per stop (what happened, photos)

**Trip Stop Notes**:
- Text notes about the visit
- Photo attachments (fridge photo, menu, storefront, etc.)
- Timestamp
- Who added it

---

### 5. VISIT NOTES & CHECK-INS
**Purpose**: Log what happened at each visit

**Add Visit Note Screen**:
- Select company (or auto-fill if navigated from company/trip)
- Note text (freeform)
- Add photos from camera or gallery
- Visit outcome dropdown:
  - Successful - placed order
  - Interested - follow up needed
  - Not interested
  - Not available / closed
  - Meeting rescheduled
- Update company status if needed
- Tag with categories
- Save as draft or submit

**Visit History**:
- Chronological feed of all visit notes
- Filter by company, date range, outcome
- Search in notes
- View attached photos full-screen

---

### 6. TASKS
**Purpose**: Track to-dos and follow-ups

**Task Types**:
- Call
- Email
- Meeting
- Follow-up
- Demo/Tasting
- Proposal
- Contract
- Support
- General

**Task List Screen**:
- Filter: Today, This Week, Overdue, All
- Sort by due date, priority
- Show: title, due date, linked company/prospect, priority badge
- Swipe to complete or reschedule

**Add/Edit Task**:
- Title
- Description
- Task type (dropdown)
- Priority (1-5)
- Due date and time
- Link to prospect or company
- Assign to salesperson
- Add notes

---

### 7. ALERTS & INTELLIGENCE
**Purpose**: AI-generated insights about customers

**Alert Types**:
- **Pattern Disruption** - Customer who usually orders monthly hasn't ordered in 45+ days
- **High Value at Risk** - Big customer showing declining orders
- **Dormant Customer** - No activity for 90+ days
- **Reactivation Opportunity** - Ex-customer who might be worth re-approaching

**Alert Card Shows**:
- Company name
- Alert type badge (color-coded by priority: red/orange/yellow)
- Description of what triggered the alert
- Recommendation (e.g., "Call to check in")
- Key metrics (days since order, lifetime value, etc.)
- Quick actions: Call, Dismiss, Create Task

---

### 8. SETTINGS & PROFILE
- User profile (name, assigned region)
- Notification preferences
- Sync settings
- Default start location
- Offline mode toggle
- Logout

---

## Database Structure

Use **Supabase** (PostgreSQL) for the database. Here are the key tables:

### COMPANIES
```
- id (primary key)
- company_id (external ID from ERP)
- name
- address_line1, city, post_code, country
- latitude, longitude (for mapping)
- contact_person_name, contact_person_email, contact_person_phone
- email, phone_number, website
- company_categories (array/json - e.g., ["cafe", "restaurant"])
- is_customer (boolean)
- total_revenue_2024, total_revenue_2025, total_revenue_all_time
- invoice_count_all_time
- first_invoice_date, last_invoice_date
- salesperson (assigned rep)
- tags (array)
- notes
- created_at, updated_at
```

### PROSPECTS
```
- id (uuid, primary key)
- name
- company_id (links to companies if existing)
- address, city, phone, email, website
- latitude, longitude
- status (enum: new_leads, first_contact, meeting_planned, follow_up, customer, ex_customer, contact_later, unqualified)
- region
- prospect_type
- priority_level (1-5)
- contact_later_date
- contact_later_reason
- unqualified_reason (enum: no_fridge_space, no_fit, not_convinced, too_expensive, prefers_competition, unclear)
- unqualified_details
- last_contact_date
- next_action
- notes
- created_at, updated_at
```

### TRIPS
```
- id (uuid, primary key)
- name
- trip_date
- start_location (address)
- start_time
- start_lat, start_lng
- status (planned, in_progress, completed, cancelled)
- total_distance_km
- estimated_duration_minutes
- created_by (salesperson)
- notes
- created_at, updated_at
```

### TRIP_STOPS
```
- id (uuid, primary key)
- trip_id (foreign key to trips)
- company_id (optional link)
- company_name
- address
- latitude, longitude
- stop_order (integer for sequencing)
- estimated_arrival (time)
- actual_arrival (time)
- duration_minutes (default 30)
- notes
- completed (boolean)
- created_at
```

### TRIP_STOP_NOTES
```
- id (primary key)
- trip_stop_id (foreign key)
- note_text
- created_by
- created_at, updated_at
```

### TRIP_STOP_ATTACHMENTS
```
- id (primary key)
- trip_stop_id
- note_id (links to specific note)
- file_name
- file_type
- file_size
- storage_path (Supabase Storage)
- description
- created_by
- created_at
```

### COMPANY_NOTES
```
- id (primary key)
- company_id
- note_text
- created_by
- created_at, updated_at
```

### COMPANY_ATTACHMENTS
```
- id (primary key)
- company_id
- note_id (optional, links note to images)
- file_name
- file_type
- file_size
- storage_path
- description
- created_by
- created_at
```

### SALES_TASKS
```
- id (uuid, primary key)
- title
- description
- task_type (enum: call, email, meeting, follow_up, demo, proposal, contract, onboarding, support, research, general)
- category (sales, marketing, support, admin)
- priority (1-5)
- status (pending, in_progress, completed, cancelled, overdue)
- due_date, due_time
- scheduled_date, scheduled_time
- estimated_duration (minutes)
- prospect_id (optional foreign key)
- assigned_to (salesperson)
- created_by
- progress_percentage
- completed_at
- notes
- tags (json array)
- attachments (json array)
- created_at, updated_at
```

### CUSTOMER_ALERTS
```
- id (primary key)
- company_id (foreign key)
- company_name
- email
- alert_type (e.g., PATTERN_DISRUPTION, HIGH_VALUE_AT_RISK, DORMANT_CUSTOMER)
- priority (HIGH, MEDIUM, LOW)
- description
- recommendation
- metrics (json - days_since_order, lifetime_value, etc.)
- status (active, dismissed, actioned, resolved)
- actioned_at, actioned_by
- dismissed_at, dismissed_by
- notes
- created_at, updated_at
```

---

## File Storage

Use **Supabase Storage** for:
- Visit photos (bucket: `company-attachments`)
- Trip stop photos (bucket: `trip-attachments`)

Photos should be:
- Compressed before upload (max 1MB)
- Named with timestamp + company ID for easy retrieval
- Linked to notes via the attachments tables

---

## Key User Flows

### Flow 1: Starting the Day
1. Open app > See today's route on dashboard
2. Tap "Start Route"
3. See map with all stops, first stop highlighted
4. Tap "Navigate" to open in Maps
5. Drive to location

### Flow 2: Completing a Visit
1. Arrive at stop
2. Meet with customer/prospect
3. Open app > Current trip > Current stop
4. Tap "Add Note"
5. Write what happened
6. Take photos if relevant (fridge setup, display, etc.)
7. Select outcome (placed order, interested, not interested, etc.)
8. Save note
9. Mark stop as complete
10. App shows next stop

### Flow 3: Updating a Prospect Status
1. After a successful visit where they agree to become a customer
2. Go to prospect detail
3. Change status from "Follow-up" to "Customer"
4. Optionally create a task for onboarding call
5. Prospect moves through pipeline

### Flow 4: Planning Tomorrow's Route
1. Go to Trips > Create New Trip
2. Set date and start location
3. Add stops by browsing companies or searching
4. Tap "Optimize Route"
5. Review optimized order
6. Save trip
7. Ready for tomorrow

### Flow 5: Quick Task from Alert
1. See alert: "High Value Customer - No order in 45 days"
2. Tap alert
3. Tap "Create Task"
4. App pre-fills: "Follow up with [Company Name]"
5. Set due date
6. Save
7. Dismiss alert

---

## AI/Claude Agent Tools

Build these tools for an AI assistant to help the salesperson:

### Tool: search_companies
**Purpose**: Find companies by various criteria
**Parameters**:
- query (name, city, or keyword)
- category (optional)
- is_customer (boolean, optional)
- min_revenue (optional)
- max_days_since_last_order (optional)
**Returns**: List of matching companies with key info

### Tool: get_company_detail
**Purpose**: Get full details about a specific company
**Parameters**: company_id
**Returns**: All company data including notes, revenue, visit history

### Tool: add_visit_note
**Purpose**: Log a visit note to a company
**Parameters**:
- company_id
- note_text
- outcome (optional)
- created_by
**Returns**: Created note ID

### Tool: update_company
**Purpose**: Update company information
**Parameters**:
- company_id
- fields to update (address, contact, phone, email, categories, etc.)
**Returns**: Success confirmation

### Tool: get_prospects
**Purpose**: List prospects with optional filtering
**Parameters**:
- status (optional, e.g., "first_contact")
- region (optional)
- priority_min (optional)
**Returns**: List of prospects

### Tool: update_prospect_status
**Purpose**: Move a prospect to a new pipeline stage
**Parameters**:
- prospect_id
- new_status
- reason (if unqualified)
- contact_later_date (if contact_later)
**Returns**: Updated prospect

### Tool: create_task
**Purpose**: Create a new task
**Parameters**:
- title
- task_type
- due_date
- priority
- prospect_id or company_id (optional)
- assigned_to
- notes
**Returns**: Created task

### Tool: get_tasks
**Purpose**: List tasks
**Parameters**:
- status (pending, completed, overdue)
- due_date_range
- assigned_to
**Returns**: List of tasks

### Tool: complete_task
**Purpose**: Mark a task as done
**Parameters**: task_id
**Returns**: Success confirmation

### Tool: get_trip
**Purpose**: Get trip details with all stops
**Parameters**: trip_id or trip_date
**Returns**: Trip with ordered stops

### Tool: create_trip
**Purpose**: Create a new trip/route
**Parameters**:
- name
- trip_date
- start_location
- start_time
- stops (array of company_ids or addresses)
**Returns**: Created trip with stops

### Tool: add_stop_to_trip
**Purpose**: Add a stop to an existing trip
**Parameters**:
- trip_id
- company_id or address
- stop_order (optional, adds at end if not specified)
**Returns**: Updated trip

### Tool: optimize_route
**Purpose**: Reorder stops for shortest driving distance
**Parameters**: trip_id
**Returns**: Trip with optimized stop order

### Tool: mark_stop_complete
**Purpose**: Mark a trip stop as visited
**Parameters**:
- trip_stop_id
- notes (optional)
**Returns**: Success confirmation

### Tool: get_alerts
**Purpose**: Get active customer alerts
**Parameters**:
- priority (optional: HIGH, MEDIUM, LOW)
- alert_type (optional)
**Returns**: List of alerts

### Tool: dismiss_alert
**Purpose**: Dismiss an alert
**Parameters**:
- alert_id
- reason (optional)
**Returns**: Success confirmation

### Tool: get_visit_history
**Purpose**: Get visit notes for a company
**Parameters**:
- company_id
- limit (optional, default 10)
**Returns**: List of visit notes with dates and content

### Tool: geocode_address
**Purpose**: Get coordinates for an address
**Parameters**: address (string)
**Returns**: latitude, longitude, formatted_address

### Tool: search_nearby
**Purpose**: Find companies near a location
**Parameters**:
- latitude
- longitude
- radius_km
**Returns**: List of companies within radius

---

## Example AI Agent Conversations

**User**: "What companies haven't I visited in Ghent recently?"
**Agent uses**: search_companies with city="Ghent" and max_days_since_last_order=30
**Response**: "Here are 5 companies in Ghent you haven't visited in the last month: [list]"

**User**: "Add a note to Cafe Noir that they want a tasting next week"
**Agent uses**: search_companies to find Cafe Noir, then add_visit_note
**Response**: "Done! I've added the note to Cafe Noir. Want me to create a task for the tasting?"

**User**: "Plan a route for tomorrow hitting all my prospects in Antwerp"
**Agent uses**: get_prospects with region="Antwerp", then create_trip with those stops, then optimize_route
**Response**: "Created a route for tomorrow with 6 stops in Antwerp. Starting from your usual location, the optimized route is: [list]. Total estimated driving: 45 minutes."

**User**: "Mark BioBites as unqualified - they don't have fridge space"
**Agent uses**: update_prospect_status with new_status="unqualified" and reason="no_fridge_space"
**Response**: "BioBites has been moved to Unqualified with reason: No fridge space."

---

## Additional Notes for Builder

1. **Offline Support**: The app should work offline for viewing data and logging notes. Sync when back online.

2. **Maps Integration**: Use native maps (Apple Maps/Google Maps) for navigation. Show company pins on maps.

3. **Camera Access**: Easy photo capture for visit notes. Support multiple photos per note.

4. **Notifications**: Push notifications for:
   - Tasks due today
   - High priority alerts
   - Upcoming trip reminders

5. **Location Services**: Use GPS for:
   - Auto-suggesting nearby companies
   - Current location as trip start
   - Tracking visit locations

6. **Quick Actions**: From company card, allow:
   - One-tap call
   - One-tap navigate
   - One-tap WhatsApp

7. **Data Sync**: Real-time sync with Supabase when online. Queue actions offline.

8. **Role-based**: Each salesperson sees their own territory/assigned companies, but can search all.

---

## Summary

This is a field sales CRM app focused on:
- **Route planning** - Create and optimize daily visit routes
- **Visit logging** - Capture notes and photos at each stop
- **Pipeline management** - Track prospects through sales stages
- **Task management** - Stay on top of follow-ups
- **Customer intelligence** - Act on AI-generated alerts
- **Location updates** - Keep company addresses and coordinates current

The key differentiator is the tight integration between routes, visits, and the prospect pipeline - making it easy for salespeople to execute their day while keeping the CRM updated.
