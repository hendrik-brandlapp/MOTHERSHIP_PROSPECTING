#!/usr/bin/env python3
"""
MCP Server for MOTHERSHIP_PROSPECTING
Exposes CRM data and operations to Claude Desktop via Model Context Protocol
"""

import os
import json
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, Any
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://gpjoypslbrpvnhqzvacc.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create MCP server
server = Server("mothership-prospecting")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def json_serialize(obj: Any) -> str:
    """Serialize objects to JSON, handling dates and other types"""
    def default(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(obj, default=default, indent=2)


def format_response(data: Any, message: str = None) -> list[TextContent]:
    """Format response data for MCP"""
    if message:
        return [TextContent(type="text", text=f"{message}\n\n{json_serialize(data)}")]
    return [TextContent(type="text", text=json_serialize(data))]


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools"""
    return [
        # ===== COMPANIES & SALES (Priority) =====
        Tool(
            name="list_companies",
            description="List companies from the database with optional filters. Returns customer/supplier data with revenue stats.",
            inputSchema={
                "type": "object",
                "properties": {
                    "is_customer": {"type": "boolean", "description": "Filter by customer status"},
                    "is_supplier": {"type": "boolean", "description": "Filter by supplier status"},
                    "city": {"type": "string", "description": "Filter by city (partial match)"},
                    "country": {"type": "string", "description": "Filter by country code (e.g., 'BE', 'NL')"},
                    "has_revenue_2024": {"type": "boolean", "description": "Only companies with 2024 revenue"},
                    "has_revenue_2025": {"type": "boolean", "description": "Only companies with 2025 revenue"},
                    "min_revenue": {"type": "number", "description": "Minimum total revenue"},
                    "limit": {"type": "integer", "description": "Max results (default 50)", "default": 50},
                    "order_by": {"type": "string", "description": "Order by field", "enum": ["name", "total_revenue_all_time", "last_invoice_date", "created_at"]}
                }
            }
        ),
        Tool(
            name="get_company",
            description="Get detailed information about a specific company by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "integer", "description": "The company ID"}
                },
                "required": ["company_id"]
            }
        ),
        Tool(
            name="search_companies",
            description="Search companies by name or VAT number",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (name or VAT)"},
                    "limit": {"type": "integer", "description": "Max results", "default": 20}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_company_revenue",
            description="Get detailed revenue breakdown for a company",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "integer", "description": "The company ID"}
                },
                "required": ["company_id"]
            }
        ),
        Tool(
            name="list_invoices",
            description="List sales invoices with optional filters. Use order_by='total_amount' to find biggest invoices.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Filter by year (2024, 2025, or 2026)"},
                    "company_id": {"type": "integer", "description": "Filter by company ID"},
                    "company_name": {"type": "string", "description": "Filter by company name (partial match)"},
                    "is_paid": {"type": "boolean", "description": "Filter by payment status"},
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "order_by": {"type": "string", "description": "Sort field", "enum": ["invoice_date", "total_amount"], "default": "invoice_date"},
                    "order_desc": {"type": "boolean", "description": "Sort descending (default true)", "default": True},
                    "limit": {"type": "integer", "description": "Max results", "default": 50}
                }
            }
        ),
        Tool(
            name="get_sales_analytics",
            description="Get sales analytics and summary statistics. Use year='all' to compare all years. Returns revenue by month or company.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {"type": "string", "description": "Year to analyze: '2024', '2025', '2026', or 'all' for comparison"},
                    "group_by": {"type": "string", "description": "Group by dimension", "enum": ["company", "month", "day"]},
                    "top_n": {"type": "integer", "description": "Top N results for company grouping", "default": 10}
                }
            }
        ),
        Tool(
            name="update_company",
            description="Update company information (notes, tags, salesperson)",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "integer", "description": "The company ID"},
                    "notes": {"type": "string", "description": "Company notes"},
                    "company_tag": {"type": "string", "description": "Company tag/label"},
                    "assigned_salesperson": {"type": "string", "description": "Assigned salesperson name"}
                },
                "required": ["company_id"]
            }
        ),

        # ===== PROSPECTS & PIPELINE =====
        Tool(
            name="list_prospects",
            description="List prospects with optional status filter",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status",
                              "enum": ["new_leads", "first_contact", "meeting_planned", "follow_up", "customer", "ex_customer", "contact_later", "unqualified"]},
                    "region": {"type": "string", "description": "Filter by region"},
                    "assigned_to": {"type": "string", "description": "Filter by assigned salesperson"},
                    "limit": {"type": "integer", "description": "Max results", "default": 50}
                }
            }
        ),
        Tool(
            name="get_prospect",
            description="Get detailed information about a specific prospect",
            inputSchema={
                "type": "object",
                "properties": {
                    "prospect_id": {"type": "string", "description": "The prospect UUID"}
                },
                "required": ["prospect_id"]
            }
        ),
        Tool(
            name="create_prospect",
            description="Create a new prospect in the pipeline",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Company/prospect name"},
                    "address": {"type": "string", "description": "Address"},
                    "website": {"type": "string", "description": "Website URL"},
                    "status": {"type": "string", "description": "Initial status", "default": "new_leads"},
                    "notes": {"type": "string", "description": "Notes about the prospect"},
                    "region": {"type": "string", "description": "Region/area"},
                    "assigned_salesperson": {"type": "string", "description": "Assigned salesperson"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="update_prospect",
            description="Update an existing prospect",
            inputSchema={
                "type": "object",
                "properties": {
                    "prospect_id": {"type": "string", "description": "The prospect UUID"},
                    "status": {"type": "string", "description": "New status"},
                    "name": {"type": "string", "description": "Updated name"},
                    "address": {"type": "string", "description": "Updated address"},
                    "website": {"type": "string", "description": "Updated website"},
                    "notes": {"type": "string", "description": "Updated notes"},
                    "next_action": {"type": "string", "description": "Next action to take"},
                    "priority_level": {"type": "integer", "description": "Priority (1-5)"},
                    "contact_later_date": {"type": "string", "description": "Date to contact later (YYYY-MM-DD)"},
                    "contact_later_reason": {"type": "string", "description": "Reason for delaying contact"}
                },
                "required": ["prospect_id"]
            }
        ),
        Tool(
            name="delete_prospect",
            description="Delete a prospect from the pipeline",
            inputSchema={
                "type": "object",
                "properties": {
                    "prospect_id": {"type": "string", "description": "The prospect UUID"}
                },
                "required": ["prospect_id"]
            }
        ),
        Tool(
            name="get_pipeline_stats",
            description="Get prospect pipeline statistics showing counts by status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),

        # ===== TASKS =====
        Tool(
            name="list_tasks",
            description="List sales tasks with filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status",
                              "enum": ["pending", "in_progress", "completed", "cancelled", "overdue"]},
                    "priority": {"type": "integer", "description": "Filter by priority (1-5)"},
                    "task_type": {"type": "string", "description": "Filter by task type"},
                    "assigned_to": {"type": "string", "description": "Filter by assigned person"},
                    "due_before": {"type": "string", "description": "Due before date (YYYY-MM-DD)"},
                    "overdue_only": {"type": "boolean", "description": "Only show overdue tasks"},
                    "limit": {"type": "integer", "description": "Max results", "default": 50}
                }
            }
        ),
        Tool(
            name="create_task",
            description="Create a new sales task",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "task_type": {"type": "string", "description": "Task type",
                                 "enum": ["call", "email", "meeting", "follow_up", "demo", "proposal", "contract", "onboarding", "support", "research", "general"]},
                    "category": {"type": "string", "description": "Task category", "default": "sales"},
                    "priority": {"type": "integer", "description": "Priority (1-5)", "default": 3},
                    "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
                    "due_time": {"type": "string", "description": "Due time (HH:MM)"},
                    "prospect_id": {"type": "string", "description": "Related prospect UUID"},
                    "assigned_to": {"type": "string", "description": "Assigned to person"},
                    "estimated_duration": {"type": "integer", "description": "Duration in minutes"}
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="update_task",
            description="Update an existing task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The task UUID"},
                    "status": {"type": "string", "description": "New status"},
                    "title": {"type": "string", "description": "Updated title"},
                    "description": {"type": "string", "description": "Updated description"},
                    "priority": {"type": "integer", "description": "Updated priority"},
                    "due_date": {"type": "string", "description": "Updated due date"},
                    "progress_percentage": {"type": "integer", "description": "Progress (0-100)"},
                    "notes": {"type": "string", "description": "Task notes"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="complete_task",
            description="Mark a task as completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The task UUID"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="get_task_analytics",
            description="Get task analytics and completion statistics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),

        # ===== ALERTS =====
        Tool(
            name="list_alerts",
            description="List customer alerts (business intelligence notifications)",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status",
                              "enum": ["active", "dismissed", "actioned", "resolved"]},
                    "priority": {"type": "string", "description": "Filter by priority",
                                "enum": ["HIGH", "MEDIUM", "LOW"]},
                    "alert_type": {"type": "string", "description": "Filter by alert type"},
                    "company_id": {"type": "integer", "description": "Filter by company ID"},
                    "limit": {"type": "integer", "description": "Max results", "default": 50}
                }
            }
        ),
        Tool(
            name="dismiss_alert",
            description="Dismiss a customer alert",
            inputSchema={
                "type": "object",
                "properties": {
                    "alert_id": {"type": "integer", "description": "The alert ID"},
                    "dismissed_by": {"type": "string", "description": "Who dismissed it"},
                    "notes": {"type": "string", "description": "Dismissal notes"}
                },
                "required": ["alert_id"]
            }
        ),
        Tool(
            name="action_alert",
            description="Mark an alert as actioned",
            inputSchema={
                "type": "object",
                "properties": {
                    "alert_id": {"type": "integer", "description": "The alert ID"},
                    "actioned_by": {"type": "string", "description": "Who actioned it"},
                    "notes": {"type": "string", "description": "Action notes"}
                },
                "required": ["alert_id"]
            }
        ),

        # ===== TRIPS =====
        Tool(
            name="list_trips",
            description="List planned trips/routes",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status"},
                    "from_date": {"type": "string", "description": "From date (YYYY-MM-DD)"},
                    "to_date": {"type": "string", "description": "To date (YYYY-MM-DD)"},
                    "limit": {"type": "integer", "description": "Max results", "default": 20}
                }
            }
        ),
        Tool(
            name="get_trip",
            description="Get detailed trip information including stops",
            inputSchema={
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string", "description": "The trip UUID"}
                },
                "required": ["trip_id"]
            }
        ),
        Tool(
            name="create_trip",
            description="Create a new trip/route plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Trip name"},
                    "trip_date": {"type": "string", "description": "Trip date (YYYY-MM-DD)"},
                    "start_location": {"type": "string", "description": "Starting location address"},
                    "start_time": {"type": "string", "description": "Start time (HH:MM)"},
                    "notes": {"type": "string", "description": "Trip notes"},
                    "created_by": {"type": "string", "description": "Creator name"}
                },
                "required": ["name", "trip_date"]
            }
        ),

        # ===== AI & ENRICHMENT =====
        Tool(
            name="enrich_company",
            description="AI-powered company enrichment - searches for public information about a company",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Company name to research"},
                    "website_url": {"type": "string", "description": "Company website URL"},
                    "city": {"type": "string", "description": "City location"},
                    "country": {"type": "string", "description": "Country code", "default": "BE"}
                },
                "required": ["company_name"]
            }
        ),

        # ===== PRODUCTS & PRICING =====
        Tool(
            name="list_products",
            description="List products from the catalog",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_id": {"type": "integer", "description": "Filter by category ID"},
                    "is_active": {"type": "boolean", "description": "Filter by active status"},
                    "search": {"type": "string", "description": "Search by name or SKU"},
                    "limit": {"type": "integer", "description": "Max results", "default": 50}
                }
            }
        ),
        Tool(
            name="get_product_prices",
            description="Get prices for a product across all price lists",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product ID"}
                },
                "required": ["product_id"]
            }
        ),

        # ===== WHATSAPP =====
        Tool(
            name="list_whatsapp_messages",
            description="List recent WhatsApp messages",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string", "description": "Filter by phone number"},
                    "status": {"type": "string", "description": "Filter by status"},
                    "limit": {"type": "integer", "description": "Max results", "default": 50}
                }
            }
        ),
    ]


# ============================================================================
# TOOL HANDLERS
# ============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    try:
        # ===== COMPANIES & SALES =====
        if name == "list_companies":
            query = supabase.table('companies').select('id, company_id, name, public_name, city, country_code, is_customer, is_supplier, total_revenue_2024, total_revenue_2025, total_revenue_all_time, invoice_count_all_time, last_invoice_date, phone_number, email, assigned_salesperson')

            if arguments.get('is_customer') is not None:
                query = query.eq('is_customer', arguments['is_customer'])
            if arguments.get('is_supplier') is not None:
                query = query.eq('is_supplier', arguments['is_supplier'])
            if arguments.get('city'):
                query = query.ilike('city', f"%{arguments['city']}%")
            if arguments.get('country'):
                query = query.eq('country_code', arguments['country'])
            if arguments.get('has_revenue_2024'):
                query = query.gt('total_revenue_2024', 0)
            if arguments.get('has_revenue_2025'):
                query = query.gt('total_revenue_2025', 0)
            if arguments.get('min_revenue'):
                query = query.gte('total_revenue_all_time', arguments['min_revenue'])

            order_by = arguments.get('order_by', 'name')
            if order_by == 'total_revenue_all_time':
                query = query.order('total_revenue_all_time', desc=True)
            elif order_by == 'last_invoice_date':
                query = query.order('last_invoice_date', desc=True)
            else:
                query = query.order('name')

            limit = arguments.get('limit', 50)
            result = query.limit(limit).execute()
            return format_response(result.data, f"Found {len(result.data)} companies")

        elif name == "get_company":
            result = supabase.table('companies').select('*').eq('company_id', arguments['company_id']).single().execute()
            return format_response(result.data)

        elif name == "search_companies":
            query = arguments['query']
            limit = arguments.get('limit', 20)

            # Search by name or VAT
            result = supabase.table('companies').select('id, company_id, name, public_name, vat_number, city, country_code, is_customer, total_revenue_all_time').or_(f"name.ilike.%{query}%,public_name.ilike.%{query}%,vat_number.ilike.%{query}%").limit(limit).execute()
            return format_response(result.data, f"Found {len(result.data)} companies matching '{query}'")

        elif name == "get_company_revenue":
            company_id = arguments['company_id']

            # Get company data
            company = supabase.table('companies').select('company_id, name, total_revenue_2024, total_revenue_2025, total_revenue_all_time, invoice_count_2024, invoice_count_2025, invoice_count_all_time, first_invoice_date, last_invoice_date, average_invoice_value').eq('company_id', company_id).single().execute()

            # Get recent invoices from all years
            invoices_2024 = supabase.table('sales_2024').select('invoice_number, invoice_date, total_amount').eq('company_id', company_id).order('invoice_date', desc=True).limit(10).execute()
            invoices_2025 = supabase.table('sales_2025').select('invoice_number, invoice_date, total_amount').eq('company_id', company_id).order('invoice_date', desc=True).limit(10).execute()
            invoices_2026 = supabase.table('sales_2026').select('invoice_number, invoice_date, total_amount').eq('company_id', company_id).order('invoice_date', desc=True).limit(10).execute()

            return format_response({
                "company": company.data,
                "recent_invoices_2026": invoices_2026.data,
                "recent_invoices_2025": invoices_2025.data,
                "recent_invoices_2024": invoices_2024.data
            })

        elif name == "list_invoices":
            year = arguments.get('year', 2026)
            table = f'sales_{year}'

            query = supabase.table(table).select('id, invoice_id, invoice_number, invoice_date, company_id, company_name, total_amount, balance, is_paid')

            if arguments.get('company_id'):
                query = query.eq('company_id', arguments['company_id'])
            if arguments.get('company_name'):
                query = query.ilike('company_name', f"%{arguments['company_name']}%")
            if arguments.get('is_paid') is not None:
                query = query.eq('is_paid', arguments['is_paid'])
            if arguments.get('start_date'):
                query = query.gte('invoice_date', arguments['start_date'])
            if arguments.get('end_date'):
                query = query.lte('invoice_date', arguments['end_date'])

            # Sorting
            order_by = arguments.get('order_by', 'invoice_date')
            order_desc = arguments.get('order_desc', True)

            limit = arguments.get('limit', 50)
            result = query.order(order_by, desc=order_desc).limit(limit).execute()
            return format_response(result.data, f"Found {len(result.data)} invoices")

        elif name == "get_sales_analytics":
            year_arg = str(arguments.get('year', '2025'))
            group_by = arguments.get('group_by', 'company')
            top_n = arguments.get('top_n', 10)

            # Determine which years to query
            if year_arg == 'all':
                years_to_query = ['2024', '2025', '2026']
            else:
                years_to_query = [year_arg]

            # Fetch data from all requested years
            all_data = []
            for yr in years_to_query:
                table = f'sales_{yr}'
                try:
                    result = supabase.table(table).select('company_id, company_name, invoice_date, total_amount, invoice_data').execute()
                    for inv in result.data:
                        inv['year'] = yr
                        # Calculate revenue from line items (ex-VAT) like DUANO "Omzet"
                        invoice_data = inv.get('invoice_data') or {}
                        line_items = invoice_data.get('invoice_line_items') or []
                        revenue = sum(float(item.get('revenue') or 0) for item in line_items)
                        # Fallback to total_amount if no line items
                        if revenue == 0:
                            revenue = float(inv.get('total_amount') or 0)
                        inv['revenue'] = revenue
                    all_data.extend(result.data)
                except Exception as e:
                    print(f"Could not fetch {table}: {e}")

            if group_by == 'company':
                # Aggregate by company
                company_totals = {}
                for inv in all_data:
                    cid = inv['company_id']
                    if cid not in company_totals:
                        company_totals[cid] = {'company_name': inv['company_name'], 'total_revenue': 0, 'invoice_count': 0}
                    company_totals[cid]['total_revenue'] += inv['revenue']
                    company_totals[cid]['invoice_count'] += 1

                sorted_companies = sorted(company_totals.items(), key=lambda x: x[1]['total_revenue'], reverse=True)[:top_n]
                analytics = [{'company_id': k, 'company_name': v['company_name'], 'total_revenue': round(v['total_revenue'], 2), 'invoice_count': v['invoice_count']} for k, v in sorted_companies]

            elif group_by == 'month':
                # Aggregate by month (YYYY-MM format)
                month_totals = {}
                for inv in all_data:
                    month_key = inv['invoice_date'][:7] if inv['invoice_date'] else 'unknown'
                    if month_key not in month_totals:
                        month_totals[month_key] = {'revenue': 0, 'invoice_count': 0}
                    month_totals[month_key]['revenue'] += inv['revenue']
                    month_totals[month_key]['invoice_count'] += 1

                # Sort by month chronologically
                sorted_months = sorted(month_totals.items(), key=lambda x: x[0])
                analytics = [{'month': k, 'revenue': round(v['revenue'], 2), 'invoice_count': v['invoice_count']} for k, v in sorted_months]

            else:
                # Summary
                total_revenue = sum(inv['revenue'] for inv in all_data)
                analytics = {
                    'years': years_to_query,
                    'total_invoices': len(all_data),
                    'total_revenue': round(total_revenue, 2)
                }

            year_label = 'all years (2024-2026)' if year_arg == 'all' else year_arg
            return format_response(analytics, f"Sales analytics for {year_label}")

        elif name == "update_company":
            company_id = arguments.pop('company_id')
            update_data = {k: v for k, v in arguments.items() if v is not None}
            update_data['updated_at'] = datetime.now().isoformat()

            result = supabase.table('companies').update(update_data).eq('company_id', company_id).execute()
            return format_response(result.data, "Company updated successfully")

        # ===== PROSPECTS & PIPELINE =====
        elif name == "list_prospects":
            query = supabase.table('prospects').select('id, name, address, website, status, region, priority_level, assigned_salesperson, next_action, created_at, updated_at')

            if arguments.get('status'):
                query = query.eq('status', arguments['status'])
            if arguments.get('region'):
                query = query.ilike('region', f"%{arguments['region']}%")
            if arguments.get('assigned_to'):
                query = query.eq('assigned_salesperson', arguments['assigned_to'])

            limit = arguments.get('limit', 50)
            result = query.order('created_at', desc=True).limit(limit).execute()
            return format_response(result.data, f"Found {len(result.data)} prospects")

        elif name == "get_prospect":
            result = supabase.table('prospects').select('*').eq('id', arguments['prospect_id']).single().execute()
            return format_response(result.data)

        elif name == "create_prospect":
            prospect_data = {
                'name': arguments['name'],
                'address': arguments.get('address'),
                'website': arguments.get('website'),
                'status': arguments.get('status', 'new_leads'),
                'notes': arguments.get('notes'),
                'region': arguments.get('region'),
                'assigned_salesperson': arguments.get('assigned_salesperson'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            result = supabase.table('prospects').insert(prospect_data).execute()
            return format_response(result.data[0], "Prospect created successfully")

        elif name == "update_prospect":
            prospect_id = arguments.pop('prospect_id')
            update_data = {k: v for k, v in arguments.items() if v is not None}
            update_data['updated_at'] = datetime.now().isoformat()

            result = supabase.table('prospects').update(update_data).eq('id', prospect_id).execute()
            return format_response(result.data, "Prospect updated successfully")

        elif name == "delete_prospect":
            result = supabase.table('prospects').delete().eq('id', arguments['prospect_id']).execute()
            return format_response({"deleted": True}, "Prospect deleted successfully")

        elif name == "get_pipeline_stats":
            result = supabase.table('prospects').select('status').execute()

            stats = {}
            for prospect in result.data:
                status = prospect['status']
                stats[status] = stats.get(status, 0) + 1

            total = len(result.data)
            pipeline = {
                'total_prospects': total,
                'by_status': stats,
                'percentages': {k: round(v/total*100, 1) if total > 0 else 0 for k, v in stats.items()}
            }
            return format_response(pipeline, "Pipeline Statistics")

        # ===== TASKS =====
        elif name == "list_tasks":
            query = supabase.table('sales_tasks').select('id, title, description, task_type, category, priority, status, due_date, due_time, assigned_to, prospect_id, progress_percentage, created_at')

            if arguments.get('status'):
                query = query.eq('status', arguments['status'])
            if arguments.get('priority'):
                query = query.eq('priority', arguments['priority'])
            if arguments.get('task_type'):
                query = query.eq('task_type', arguments['task_type'])
            if arguments.get('assigned_to'):
                query = query.eq('assigned_to', arguments['assigned_to'])
            if arguments.get('due_before'):
                query = query.lte('due_date', arguments['due_before'])
            if arguments.get('overdue_only'):
                today = date.today().isoformat()
                query = query.lt('due_date', today).neq('status', 'completed')

            limit = arguments.get('limit', 50)
            result = query.order('due_date').limit(limit).execute()
            return format_response(result.data, f"Found {len(result.data)} tasks")

        elif name == "create_task":
            task_data = {
                'title': arguments['title'],
                'description': arguments.get('description'),
                'task_type': arguments.get('task_type', 'general'),
                'category': arguments.get('category', 'sales'),
                'priority': arguments.get('priority', 3),
                'status': 'pending',
                'due_date': arguments.get('due_date'),
                'due_time': arguments.get('due_time'),
                'prospect_id': arguments.get('prospect_id'),
                'assigned_to': arguments.get('assigned_to'),
                'estimated_duration': arguments.get('estimated_duration'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            result = supabase.table('sales_tasks').insert(task_data).execute()
            return format_response(result.data[0], "Task created successfully")

        elif name == "update_task":
            task_id = arguments.pop('task_id')
            update_data = {k: v for k, v in arguments.items() if v is not None}
            update_data['updated_at'] = datetime.now().isoformat()

            result = supabase.table('sales_tasks').update(update_data).eq('id', task_id).execute()
            return format_response(result.data, "Task updated successfully")

        elif name == "complete_task":
            update_data = {
                'status': 'completed',
                'progress_percentage': 100,
                'completed_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            result = supabase.table('sales_tasks').update(update_data).eq('id', arguments['task_id']).execute()
            return format_response(result.data, "Task marked as completed")

        elif name == "get_task_analytics":
            result = supabase.table('sales_tasks').select('status, priority, task_type, category, due_date').execute()
            data = result.data

            today = date.today().isoformat()
            analytics = {
                'total_tasks': len(data),
                'by_status': {},
                'by_priority': {},
                'by_type': {},
                'overdue_count': 0,
                'due_today': 0
            }

            for task in data:
                # Count by status
                status = task['status']
                analytics['by_status'][status] = analytics['by_status'].get(status, 0) + 1

                # Count by priority
                priority = task['priority']
                analytics['by_priority'][priority] = analytics['by_priority'].get(priority, 0) + 1

                # Count by type
                task_type = task['task_type']
                analytics['by_type'][task_type] = analytics['by_type'].get(task_type, 0) + 1

                # Check overdue/due today
                if task['due_date']:
                    if task['due_date'] < today and task['status'] not in ['completed', 'cancelled']:
                        analytics['overdue_count'] += 1
                    elif task['due_date'] == today:
                        analytics['due_today'] += 1

            completed = analytics['by_status'].get('completed', 0)
            analytics['completion_rate'] = round(completed / len(data) * 100, 1) if data else 0

            return format_response(analytics, "Task Analytics")

        # ===== ALERTS =====
        elif name == "list_alerts":
            query = supabase.table('customer_alerts').select('id, company_id, company_name, alert_type, priority, description, recommendation, status, created_at')

            if arguments.get('status'):
                query = query.eq('status', arguments['status'])
            if arguments.get('priority'):
                query = query.eq('priority', arguments['priority'])
            if arguments.get('alert_type'):
                query = query.eq('alert_type', arguments['alert_type'])
            if arguments.get('company_id'):
                query = query.eq('company_id', arguments['company_id'])

            limit = arguments.get('limit', 50)
            result = query.order('created_at', desc=True).limit(limit).execute()
            return format_response(result.data, f"Found {len(result.data)} alerts")

        elif name == "dismiss_alert":
            update_data = {
                'status': 'dismissed',
                'dismissed_at': datetime.now().isoformat(),
                'dismissed_by': arguments.get('dismissed_by', 'unknown'),
                'notes': arguments.get('notes'),
                'updated_at': datetime.now().isoformat()
            }

            result = supabase.table('customer_alerts').update(update_data).eq('id', arguments['alert_id']).execute()
            return format_response(result.data, "Alert dismissed")

        elif name == "action_alert":
            update_data = {
                'status': 'actioned',
                'actioned_at': datetime.now().isoformat(),
                'actioned_by': arguments.get('actioned_by', 'unknown'),
                'notes': arguments.get('notes'),
                'updated_at': datetime.now().isoformat()
            }

            result = supabase.table('customer_alerts').update(update_data).eq('id', arguments['alert_id']).execute()
            return format_response(result.data, "Alert marked as actioned")

        # ===== TRIPS =====
        elif name == "list_trips":
            query = supabase.table('trips').select('id, name, trip_date, start_location, start_time, status, total_distance_km, estimated_duration_minutes, created_by, notes')

            if arguments.get('status'):
                query = query.eq('status', arguments['status'])
            if arguments.get('from_date'):
                query = query.gte('trip_date', arguments['from_date'])
            if arguments.get('to_date'):
                query = query.lte('trip_date', arguments['to_date'])

            limit = arguments.get('limit', 20)
            result = query.order('trip_date', desc=True).limit(limit).execute()
            return format_response(result.data, f"Found {len(result.data)} trips")

        elif name == "get_trip":
            trip = supabase.table('trips').select('*').eq('id', arguments['trip_id']).single().execute()
            stops = supabase.table('trip_stops').select('*').eq('trip_id', arguments['trip_id']).order('stop_order').execute()

            return format_response({
                'trip': trip.data,
                'stops': stops.data
            })

        elif name == "create_trip":
            trip_data = {
                'name': arguments['name'],
                'trip_date': arguments['trip_date'],
                'start_location': arguments.get('start_location'),
                'start_time': arguments.get('start_time'),
                'status': 'planned',
                'notes': arguments.get('notes'),
                'created_by': arguments.get('created_by'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            result = supabase.table('trips').insert(trip_data).execute()
            return format_response(result.data[0], "Trip created successfully")

        # ===== AI & ENRICHMENT =====
        elif name == "enrich_company":
            if not OPENAI_API_KEY:
                return format_response({"error": "OpenAI API key not configured"}, "Enrichment failed")

            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)

            company_name = arguments['company_name']
            website = arguments.get('website_url', '')
            city = arguments.get('city', '')
            country = arguments.get('country', 'BE')

            prompt = f"""Research the following company and provide information:
Company: {company_name}
Website: {website}
Location: {city}, {country}

Provide:
1. Brief company summary (2-3 sentences)
2. Industry/sector
3. Approximate company size if known
4. Key products/services
5. Any notable information

Format as JSON with keys: summary, industry, size, products, notes"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            try:
                enrichment = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                enrichment = {"raw_response": response.choices[0].message.content}

            return format_response(enrichment, f"Enrichment data for {company_name}")

        # ===== PRODUCTS & PRICING =====
        elif name == "list_products":
            query = supabase.table('products').select('id, name, sku, category_id, unit, description, is_active, is_sellable')

            if arguments.get('category_id'):
                query = query.eq('category_id', arguments['category_id'])
            if arguments.get('is_active') is not None:
                query = query.eq('is_active', arguments['is_active'])
            if arguments.get('search'):
                search = arguments['search']
                query = query.or_(f"name.ilike.%{search}%,sku.ilike.%{search}%")

            limit = arguments.get('limit', 50)
            result = query.order('name').limit(limit).execute()
            return format_response(result.data, f"Found {len(result.data)} products")

        elif name == "get_product_prices":
            product_id = arguments['product_id']

            product = supabase.table('products').select('*').eq('id', product_id).single().execute()
            prices = supabase.table('product_prices').select('*, sales_price_lists(name)').eq('product_id', product_id).execute()

            return format_response({
                'product': product.data,
                'prices': prices.data
            })

        # ===== WHATSAPP =====
        elif name == "list_whatsapp_messages":
            query = supabase.table('whatsapp_messages').select('id, from_number, to_number, message_body, message_type, direction, status, ai_summary, ai_sentiment, received_at')

            if arguments.get('phone_number'):
                phone = arguments['phone_number']
                query = query.or_(f"from_number.eq.{phone},to_number.eq.{phone}")
            if arguments.get('status'):
                query = query.eq('status', arguments['status'])

            limit = arguments.get('limit', 50)
            result = query.order('received_at', desc=True).limit(limit).execute()
            return format_response(result.data, f"Found {len(result.data)} messages")

        else:
            return format_response({"error": f"Unknown tool: {name}"}, "Error")

    except Exception as e:
        return format_response({"error": str(e)}, f"Error executing {name}")


# ============================================================================
# RESOURCES
# ============================================================================

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="mothership://pipeline/stats",
            name="Pipeline Statistics",
            description="Current prospect pipeline statistics",
            mimeType="application/json"
        ),
        Resource(
            uri="mothership://alerts/active",
            name="Active Alerts",
            description="Currently active customer alerts",
            mimeType="application/json"
        ),
        Resource(
            uri="mothership://tasks/overdue",
            name="Overdue Tasks",
            description="Tasks that are past due",
            mimeType="application/json"
        ),
        Resource(
            uri="mothership://sales/summary",
            name="Sales Summary",
            description="Current year sales summary",
            mimeType="application/json"
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource"""

    if uri == "mothership://pipeline/stats":
        result = supabase.table('prospects').select('status').execute()
        stats = {}
        for p in result.data:
            stats[p['status']] = stats.get(p['status'], 0) + 1
        return json_serialize({'total': len(result.data), 'by_status': stats})

    elif uri == "mothership://alerts/active":
        result = supabase.table('customer_alerts').select('id, company_name, alert_type, priority, description').eq('status', 'active').order('priority').limit(20).execute()
        return json_serialize(result.data)

    elif uri == "mothership://tasks/overdue":
        today = date.today().isoformat()
        result = supabase.table('sales_tasks').select('id, title, due_date, priority, assigned_to').lt('due_date', today).neq('status', 'completed').neq('status', 'cancelled').order('due_date').execute()
        return json_serialize(result.data)

    elif uri == "mothership://sales/summary":
        # Get current year data (2026)
        result_2026 = supabase.table('sales_2026').select('total_amount').execute()
        total_2026 = sum(float(i['total_amount'] or 0) for i in result_2026.data)

        # Get 2025 data for comparison
        result_2025 = supabase.table('sales_2025').select('total_amount').execute()
        total_2025 = sum(float(i['total_amount'] or 0) for i in result_2025.data)

        return json_serialize({
            'year_2026': {
                'total_invoices': len(result_2026.data),
                'total_revenue': round(total_2026, 2)
            },
            'year_2025': {
                'total_invoices': len(result_2025.data),
                'total_revenue': round(total_2025, 2)
            }
        })

    return json_serialize({"error": "Resource not found"})


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
