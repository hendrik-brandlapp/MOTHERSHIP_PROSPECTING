# Prospect Management System

This document explains the new prospect management functionality added to the DOUANO Frontend application.

## Overview

The prospect management system allows you to:
- Search for companies using Google Places API
- Save prospects to a Supabase database
- Automatically enrich prospect data using AI web search
- Manage prospect statuses and track your sales pipeline
- Filter and organize your prospect database

## Setup Instructions

### 1. Install Dependencies

First, install the new Supabase dependency:

```bash
pip install -r requirements.txt
```

### 2. Set up Supabase Database

1. Go to your Supabase project dashboard: https://app.supabase.com/project/gpjoypslbrpvnhqzvacc
2. Navigate to the SQL Editor
3. Copy and paste the contents of `supabase_setup.sql` and run it
4. This will create the `prospects` table with all necessary indexes and policies

### 3. Environment Configuration

The Supabase configuration is already set up in `app.py` with the provided credentials:
- **Supabase URL**: `https://gpjoypslbrpvnhqzvacc.supabase.co`
- **Anon Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (already configured)

## Features

### Search Prospects Tab

1. **Google Places Search**: Search for companies using natural language queries like "vegan restaurants antwerp"
2. **Interactive Map**: View search results on an interactive Google Maps interface
3. **Company Details**: Click on results to see detailed information including:
   - Address and contact information
   - Photos from Google Places
   - Website links
   - AI-powered Companyweb search results

4. **Save Prospect Button**: After viewing company details and running AI search, click "Save Prospect" to:
   - Store the company in your Supabase database
   - Automatically trigger background data enrichment
   - Add enriched data (VAT number, email, phone, directors) to the prospect profile

### Prospect Database Tab

1. **View All Prospects**: See all saved prospects in a clean card-based interface
2. **Filter and Search**: 
   - Text search by company name or address
   - Filter by prospect status (new, contacted, qualified, converted)
3. **Status Management**: Update prospect statuses with one-click buttons
4. **Prospect Information**: View all saved data including:
   - Basic company information
   - Enriched data from AI searches
   - Creation and update timestamps

## Database Schema

The `prospects` table includes the following fields:

```sql
- id: UUID (primary key)
- name: VARCHAR(255) - Company name
- address: TEXT - Company address
- website: VARCHAR(500) - Company website
- status: VARCHAR(50) - Prospect status (new/contacted/qualified/converted)
- enriched_data: JSONB - AI-enriched company data
- google_place_id: VARCHAR(255) - Google Places reference
- notes: TEXT - Additional notes
- created_at: TIMESTAMPTZ - Creation timestamp
- updated_at: TIMESTAMPTZ - Last update timestamp
```

## API Endpoints

The following new API endpoints have been added:

### GET /api/prospects
Retrieve all prospects with optional filtering:
- `?status=new` - Filter by status
- `?limit=50` - Limit results

### POST /api/prospects
Create a new prospect:
```json
{
  "name": "Company Name",
  "address": "Company Address",
  "website": "https://example.com",
  "status": "new",
  "enriched_data": {},
  "google_place_id": "ChIJ..."
}
```

### PATCH /api/prospects/{id}
Update a prospect (typically used for status changes):
```json
{
  "status": "contacted"
}
```

### DELETE /api/prospects/{id}
Delete a prospect from the database.

## Background Data Enrichment

When you save a prospect, the system automatically:

1. **Immediate Save**: Saves the basic prospect information to Supabase
2. **Background Enrichment**: Starts a background process to:
   - Search Companyweb.be for additional company information
   - Use AI to extract structured data (VAT, email, phone, directors)
   - Update the prospect record with enriched data
   - Handle failures gracefully without affecting the user experience

## Usage Workflow

1. **Search**: Use the Search Prospects tab to find companies
2. **Research**: Click on results to view details and run AI searches
3. **Save**: Click "Save Prospect" to add companies to your database
4. **Manage**: Use the Prospect Database tab to track and update prospects
5. **Follow Up**: Update prospect statuses as you progress through your sales process

## Troubleshooting

### Common Issues

1. **"Supabase not configured" error**: 
   - Check that the Supabase client is properly initialized
   - Verify the database table exists (run the SQL setup script)

2. **Background enrichment not working**:
   - Ensure OpenAI API key is configured
   - Check the console for background task errors

3. **Prospects not loading**:
   - Verify Supabase connection
   - Check Row Level Security policies
   - Ensure the prospects table exists

### Logging

Background enrichment errors are logged to the console. Check your Flask application logs for debugging information.

## Security Notes

- Row Level Security (RLS) is enabled on the prospects table
- Only authenticated users can access prospect data
- The anon key is used for client-side operations
- Consider implementing user-specific access controls for production use

## Future Enhancements

Potential improvements for the prospect management system:
- Email integration for automated outreach
- Calendar integration for scheduling follow-ups
- Advanced search and filtering options
- Export functionality for prospect lists
- Integration with CRM systems
- Bulk operations for prospect management
