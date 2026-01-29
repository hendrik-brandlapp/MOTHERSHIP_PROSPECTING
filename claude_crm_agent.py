"""
Claude CRM Agent - WhatsApp Integration

This module provides a Claude Agent SDK powered assistant that can perform
CRM operations via WhatsApp messages. Users can search companies, update notes,
create routes, manage tasks, and more through natural language.

Requires:
- claude-agent-sdk
- ANTHROPIC_API_KEY environment variable
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from supabase import create_client, Client

# Claude Agent SDK imports
# Note: The Claude Agent SDK requires Claude Code runtime to be installed
# If not available, we'll use a direct Anthropic API fallback
CLAUDE_SDK_AVAILABLE = False
query = None
tool = None
create_sdk_mcp_server = None
ClaudeAgentOptions = None

try:
    from claude_agent_sdk import (
        query,
        tool,
        create_sdk_mcp_server,
        ClaudeAgentOptions
    )
    CLAUDE_SDK_AVAILABLE = True
    print("Claude Agent SDK loaded successfully")
except ImportError as e:
    print(f"Claude Agent SDK not available: {e}")
    print("Using Anthropic API fallback instead")
except Exception as e:
    print(f"Error loading Claude Agent SDK: {e}")
    print("Using Anthropic API fallback instead")


class CRMAgentTools:
    """Custom CRM tools for Claude Agent SDK"""

    def __init__(self):
        """Initialize Supabase client for CRM operations"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)

    # ==================== COMPANY TOOLS ====================

    async def search_companies(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for companies by name, city, or category"""
        try:
            query_text = args.get('query', '')
            city = args.get('city')
            category = args.get('category')
            limit = args.get('limit', 10)

            # Build query - only select columns that exist in the schema
            q = self.supabase.table('companies').select(
                'company_id, name, public_name, city, addresses, email_addresses, company_categories'
            )

            # Apply filters - use textSearch or simple ilike
            if query_text:
                # Use simple ilike on public_name (most common search field)
                q = q.ilike('public_name', f'%{query_text}%')
            if city:
                q = q.ilike('city', f'%{city}%')

            result = q.limit(limit).execute()

            if not result.data:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"No companies found matching '{query_text}'" + (f" in {city}" if city else "")
                    }]
                }

            # Format results
            companies = []
            for c in result.data:
                name = c.get('public_name') or c.get('name')
                categories = c.get('company_categories') or []
                cat_names = [cat.get('name', '') if isinstance(cat, dict) else str(cat) for cat in categories[:3]]

                companies.append({
                    'company_id': c['company_id'],
                    'name': name,
                    'city': c.get('city', 'N/A'),
                    'address': c.get('addresses', 'N/A'),
                    'categories': ', '.join(cat_names) if cat_names else 'N/A'
                })

            text = f"Found {len(companies)} companies:\n\n"
            for i, comp in enumerate(companies, 1):
                text += f"{i}. **{comp['name']}** (ID: {comp['company_id']})\n"
                text += f"   {comp['address']}, {comp['city']}\n"
                text += f"   Categories: {comp['categories']}\n\n"

            return {"content": [{"type": "text", "text": text}]}

        except Exception as e:
            print(f"Error in search_companies: {str(e)}")
            return {"content": [{"type": "text", "text": f"Error searching companies: {str(e)}"}]}

    async def get_company_details(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific company"""
        try:
            company_id = args.get('company_id')

            if not company_id:
                return {"content": [{"type": "text", "text": "Error: company_id is required"}]}

            # Get company info
            result = self.supabase.table('companies').select('*').eq('company_id', company_id).execute()

            if not result.data:
                return {"content": [{"type": "text", "text": f"Company with ID {company_id} not found"}]}

            company = result.data[0]

            # Get recent invoices
            invoices = []
            for year in ['2024', '2025', '2026']:
                try:
                    inv_result = self.supabase.table(f'sales_{year}').select(
                        'invoice_date, total_amount, invoice_number'
                    ).eq('company_id', company_id).order('invoice_date', desc=True).limit(5).execute()
                    invoices.extend(inv_result.data or [])
                except:
                    pass

            # Sort and limit invoices
            invoices.sort(key=lambda x: x.get('invoice_date', ''), reverse=True)
            invoices = invoices[:5]

            # Get alerts
            alerts_result = self.supabase.table('customer_alerts').select(
                'alert_type, priority, description'
            ).eq('company_id', company_id).eq('status', 'active').execute()

            # Format response
            name = company.get('public_name') or company.get('name')

            text = f"## {name}\n\n"
            text += f"**Company ID:** {company_id}\n"
            text += f"**Address:** {company.get('addresses', 'N/A')}, {company.get('city', 'N/A')} {company.get('zip_code', '')}\n"
            text += f"**Email:** {company.get('email') or company.get('email_addresses') or 'N/A'}\n"
            text += f"**Phone:** {company.get('phone') or 'N/A'}\n"
            text += f"**VAT:** {company.get('vat_number') or 'N/A'}\n"

            # Categories
            categories = company.get('company_categories') or []
            if categories:
                cat_names = [cat.get('name', '') if isinstance(cat, dict) else str(cat) for cat in categories]
                text += f"**Categories:** {', '.join(cat_names)}\n"

            # Notes
            if company.get('notes'):
                text += f"\n**Notes:**\n{company.get('notes')}\n"

            # Revenue
            text += f"\n**Total Revenue (2024):** €{company.get('total_revenue_2024', 0):,.2f}\n"
            text += f"**Total Revenue (2025):** €{company.get('total_revenue_2025', 0):,.2f}\n"
            text += f"**Order Count (2024):** {company.get('order_count_2024', 0)}\n"
            text += f"**Order Count (2025):** {company.get('order_count_2025', 0)}\n"

            # Recent invoices
            if invoices:
                text += "\n**Recent Invoices:**\n"
                for inv in invoices:
                    text += f"  - {inv.get('invoice_date')}: €{float(inv.get('total_amount', 0)):,.2f} (#{inv.get('invoice_number', 'N/A')})\n"

            # Alerts
            if alerts_result.data:
                text += "\n**Active Alerts:**\n"
                for alert in alerts_result.data:
                    text += f"  - [{alert['priority']}] {alert['alert_type']}: {alert['description'][:100]}\n"

            return {"content": [{"type": "text", "text": text}]}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error getting company details: {str(e)}"}]}

    async def update_company_notes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a note to a company (inserts into company_notes table)"""
        try:
            company_id = args.get('company_id')
            note = args.get('note')

            if not company_id or not note:
                return {"content": [{"type": "text", "text": "Error: company_id and note are required"}]}

            # Get company internal id and name - company_notes uses internal 'id', not 'company_id'
            result = self.supabase.table('companies').select('id, name, public_name').eq('company_id', company_id).execute()
            if not result.data:
                return {"content": [{"type": "text", "text": f"Company {company_id} not found"}]}

            internal_id = result.data[0].get('id')
            company_name = result.data[0].get('public_name') or result.data[0].get('name')

            # Insert into company_notes table using internal id (not company_id)
            note_result = self.supabase.table('company_notes').insert({
                'company_id': int(internal_id),  # This field stores the internal id
                'note_text': note,
                'created_by': 'WhatsApp Agent'
            }).execute()

            if not note_result.data:
                return {"content": [{"type": "text", "text": "Error: Failed to create note"}]}

            return {
                "content": [{
                    "type": "text",
                    "text": f"Note added to {company_name}:\n\"{note}\""
                }]
            }

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error updating notes: {str(e)}"}]}

    # ==================== INVOICE/REVENUE TOOLS ====================

    async def get_invoice_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get invoice summary for a company or overall"""
        try:
            company_id = args.get('company_id')
            year = args.get('year', '2025')

            if company_id:
                # Get for specific company
                result = self.supabase.table(f'sales_{year}').select(
                    'invoice_date, total_amount, invoice_number, balance'
                ).eq('company_id', company_id).order('invoice_date', desc=True).execute()

                if not result.data:
                    return {"content": [{"type": "text", "text": f"No invoices found for company {company_id} in {year}"}]}

                total_revenue = sum(float(inv.get('total_amount', 0)) for inv in result.data)
                total_outstanding = sum(float(inv.get('balance', 0)) for inv in result.data if inv.get('balance'))

                text = f"**Invoice Summary for Company {company_id} ({year})**\n\n"
                text += f"Total Invoices: {len(result.data)}\n"
                text += f"Total Revenue: €{total_revenue:,.2f}\n"
                text += f"Outstanding Balance: €{total_outstanding:,.2f}\n\n"
                text += "**Recent Invoices:**\n"

                for inv in result.data[:10]:
                    balance_str = f" (€{float(inv.get('balance', 0)):,.2f} outstanding)" if inv.get('balance') else ""
                    text += f"  - {inv['invoice_date']}: €{float(inv['total_amount']):,.2f}{balance_str}\n"

            else:
                # Get overall summary
                result = self.supabase.table(f'sales_{year}').select(
                    'total_amount', count='exact'
                ).execute()

                total_revenue = sum(float(inv.get('total_amount', 0)) for inv in (result.data or []))

                text = f"**Overall Invoice Summary ({year})**\n\n"
                text += f"Total Invoices: {result.count or len(result.data or [])}\n"
                text += f"Total Revenue: €{total_revenue:,.2f}\n"

            return {"content": [{"type": "text", "text": text}]}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error getting invoice summary: {str(e)}"}]}

    # ==================== ALERT TOOLS ====================

    async def get_alerts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get customer alerts (overdue, at-risk, etc.)"""
        try:
            alert_type = args.get('type')  # PATTERN_DISRUPTION, HIGH_VALUE_AT_RISK, DORMANT_CUSTOMER, etc.
            priority = args.get('priority')  # HIGH, MEDIUM, LOW
            city = args.get('city')
            limit = args.get('limit', 20)

            # Build query
            q = self.supabase.table('customer_alerts').select(
                'company_id, company_name, public_name, alert_type, priority, description, metrics'
            ).eq('status', 'active')

            if alert_type:
                q = q.eq('alert_type', alert_type.upper())
            if priority:
                q = q.eq('priority', priority.upper())

            q = q.order('priority', desc=True).limit(limit)

            result = q.execute()

            if not result.data:
                return {"content": [{"type": "text", "text": "No active alerts found matching criteria"}]}

            # Filter by city if needed (need to join with companies)
            alerts = result.data
            if city:
                company_ids = [a['company_id'] for a in alerts]
                companies = self.supabase.table('companies').select('company_id, city').in_('company_id', company_ids).ilike('city', f'%{city}%').execute()
                city_company_ids = {c['company_id'] for c in (companies.data or [])}
                alerts = [a for a in alerts if a['company_id'] in city_company_ids]

            if not alerts:
                return {"content": [{"type": "text", "text": f"No alerts found for companies in {city}"}]}

            text = f"**Customer Alerts** ({len(alerts)} found)\n\n"

            for alert in alerts:
                name = alert.get('public_name') or alert.get('company_name')
                metrics = alert.get('metrics') or {}
                days_since = metrics.get('days_since_last_order', 'N/A')

                text += f"**[{alert['priority']}] {name}** (ID: {alert['company_id']})\n"
                text += f"  Type: {alert['alert_type']}\n"
                text += f"  {alert['description'][:150]}\n"
                text += f"  Days since last order: {days_since}\n\n"

            return {"content": [{"type": "text", "text": text}]}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error getting alerts: {str(e)}"}]}

    # ==================== TRIP/ROUTE TOOLS ====================

    async def create_trip(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new sales trip/route"""
        try:
            name = args.get('name')
            trip_date = args.get('date')  # YYYY-MM-DD or 'today', 'tomorrow'
            notes = args.get('notes', '')

            if not name:
                return {"content": [{"type": "text", "text": "Error: trip name is required"}]}

            # Parse date
            if trip_date == 'today':
                trip_date = datetime.now().strftime('%Y-%m-%d')
            elif trip_date == 'tomorrow':
                trip_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            elif not trip_date:
                trip_date = datetime.now().strftime('%Y-%m-%d')

            # Create trip
            trip_data = {
                'name': name,
                'trip_date': trip_date,
                'status': 'planned',
                'notes': notes,
                'created_by': 'whatsapp_agent',
                'created_at': datetime.now().isoformat()
            }

            result = self.supabase.table('trips').insert(trip_data).execute()

            if result.data:
                trip_id = result.data[0]['id']
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Trip created successfully!\n\n**{name}**\nDate: {trip_date}\nTrip ID: {trip_id}\n\nUse add_trip_stop to add companies to this route."
                    }]
                }
            else:
                return {"content": [{"type": "text", "text": "Error creating trip"}]}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error creating trip: {str(e)}"}]}

    async def add_trip_stop(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a company as a stop to an existing trip"""
        try:
            trip_id = args.get('trip_id')
            company_id = args.get('company_id')
            stop_order = args.get('stop_order')
            notes = args.get('notes', '')

            if not trip_id or not company_id:
                return {"content": [{"type": "text", "text": "Error: trip_id and company_id are required"}]}

            # Get company details for the stop
            company = self.supabase.table('companies').select(
                'name, public_name, addresses, city, latitude, longitude'
            ).eq('company_id', company_id).execute()

            if not company.data:
                return {"content": [{"type": "text", "text": f"Company {company_id} not found"}]}

            comp = company.data[0]

            # Get current stop count if stop_order not provided
            if not stop_order:
                stops = self.supabase.table('trip_stops').select('id', count='exact').eq('trip_id', trip_id).execute()
                stop_order = (stops.count or 0) + 1

            # Create stop
            stop_data = {
                'trip_id': trip_id,
                'company_id': company_id,
                'stop_order': stop_order,
                'company_name': comp.get('public_name') or comp.get('name'),
                'address': comp.get('addresses'),
                'city': comp.get('city'),
                'latitude': comp.get('latitude'),
                'longitude': comp.get('longitude'),
                'notes': notes,
                'status': 'pending'
            }

            result = self.supabase.table('trip_stops').insert(stop_data).execute()

            if result.data:
                company_name = comp.get('public_name') or comp.get('name')
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Added stop #{stop_order} to trip:\n**{company_name}**\n{comp.get('addresses', '')}, {comp.get('city', '')}"
                    }]
                }
            else:
                return {"content": [{"type": "text", "text": "Error adding trip stop"}]}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error adding trip stop: {str(e)}"}]}

    async def get_trips(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get planned trips"""
        try:
            date_filter = args.get('date')  # 'today', 'tomorrow', 'week', or specific date
            status = args.get('status', 'planned')

            q = self.supabase.table('trips').select('*, trip_stops(id, company_name, stop_order, status)')

            if status:
                q = q.eq('status', status)

            # Date filtering
            today = datetime.now().strftime('%Y-%m-%d')
            if date_filter == 'today':
                q = q.eq('trip_date', today)
            elif date_filter == 'tomorrow':
                tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                q = q.eq('trip_date', tomorrow)
            elif date_filter == 'week':
                week_end = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                q = q.gte('trip_date', today).lte('trip_date', week_end)
            elif date_filter:
                q = q.eq('trip_date', date_filter)
            else:
                q = q.gte('trip_date', today)

            q = q.order('trip_date').limit(10)

            result = q.execute()

            if not result.data:
                return {"content": [{"type": "text", "text": "No trips found"}]}

            text = "**Planned Trips:**\n\n"
            for trip in result.data:
                stops = trip.get('trip_stops') or []
                text += f"**{trip['name']}** (ID: {trip['id']})\n"
                text += f"  Date: {trip['trip_date']}\n"
                text += f"  Stops: {len(stops)}\n"

                if stops:
                    for stop in sorted(stops, key=lambda x: x.get('stop_order', 0)):
                        status_icon = "✓" if stop.get('status') == 'completed' else "○"
                        text += f"    {status_icon} {stop['stop_order']}. {stop['company_name']}\n"

                text += "\n"

            return {"content": [{"type": "text", "text": text}]}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error getting trips: {str(e)}"}]}

    # ==================== TASK TOOLS ====================

    async def create_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new sales task"""
        try:
            title = args.get('title')
            description = args.get('description', '')
            task_type = args.get('task_type', 'follow_up')  # call, email, meeting, follow_up, demo, etc.
            priority = args.get('priority', 3)  # 1-5, 1 is highest
            due_date = args.get('due_date')  # 'today', 'tomorrow', or YYYY-MM-DD
            company_id = args.get('company_id')

            if not title:
                return {"content": [{"type": "text", "text": "Error: task title is required"}]}

            # Parse due date
            if due_date == 'today':
                due_date = datetime.now().strftime('%Y-%m-%d')
            elif due_date == 'tomorrow':
                due_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            elif not due_date:
                due_date = datetime.now().strftime('%Y-%m-%d')

            task_data = {
                'title': title,
                'description': description,
                'task_type': task_type,
                'priority': priority,
                'status': 'pending',
                'due_date': due_date,
                'category': 'follow_up',
                'created_by': 'whatsapp_agent',
                'notes': 'Created via WhatsApp Claude Agent'
            }

            # Link to company if provided
            if company_id:
                # Check if it's a prospect or company
                prospect = self.supabase.table('prospects').select('id').eq('id', company_id).execute()
                if prospect.data:
                    task_data['prospect_id'] = company_id

            result = self.supabase.table('sales_tasks').insert(task_data).execute()

            if result.data:
                task_id = result.data[0]['id']
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Task created!\n\n**{title}**\nType: {task_type}\nPriority: {priority}\nDue: {due_date}\nTask ID: {task_id}"
                    }]
                }
            else:
                return {"content": [{"type": "text", "text": "Error creating task"}]}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error creating task: {str(e)}"}]}

    async def get_tasks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get pending tasks"""
        try:
            status = args.get('status', 'pending')
            due_filter = args.get('due')  # 'today', 'overdue', 'week'
            limit = args.get('limit', 20)

            q = self.supabase.table('sales_tasks').select(
                'id, title, task_type, priority, status, due_date'
            )

            if status:
                q = q.eq('status', status)

            today = datetime.now().strftime('%Y-%m-%d')
            if due_filter == 'today':
                q = q.eq('due_date', today)
            elif due_filter == 'overdue':
                q = q.lt('due_date', today).neq('status', 'completed')
            elif due_filter == 'week':
                week_end = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                q = q.gte('due_date', today).lte('due_date', week_end)

            q = q.order('due_date').order('priority').limit(limit)

            result = q.execute()

            if not result.data:
                return {"content": [{"type": "text", "text": "No tasks found"}]}

            text = f"**Tasks** ({len(result.data)} found)\n\n"
            for task in result.data:
                priority_emoji = "🔴" if task['priority'] == 1 else "🟡" if task['priority'] <= 3 else "⚪"
                text += f"{priority_emoji} **{task['title']}**\n"
                text += f"   Type: {task['task_type']} | Due: {task['due_date']} | ID: {task['id']}\n\n"

            return {"content": [{"type": "text", "text": text}]}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error getting tasks: {str(e)}"}]}

    # ==================== PROSPECT TOOLS ====================

    async def search_prospects(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search prospects in the sales pipeline"""
        try:
            query_text = args.get('query', '')
            status = args.get('status')  # lead, contacted, qualified, proposal, negotiation, won, lost
            limit = args.get('limit', 10)

            q = self.supabase.table('prospects').select(
                'id, name, status, email, phone, address, city, notes'
            )

            if query_text:
                q = q.or_(f"name.ilike.%{query_text}%,email.ilike.%{query_text}%")
            if status:
                q = q.eq('status', status)

            q = q.limit(limit)

            result = q.execute()

            if not result.data:
                return {"content": [{"type": "text", "text": f"No prospects found matching '{query_text}'"}]}

            text = f"**Prospects** ({len(result.data)} found)\n\n"
            for p in result.data:
                text += f"**{p['name']}** (ID: {p['id']})\n"
                text += f"  Status: {p.get('status', 'N/A')}\n"
                text += f"  {p.get('address', '')}, {p.get('city', '')}\n"
                text += f"  Email: {p.get('email', 'N/A')}\n\n"

            return {"content": [{"type": "text", "text": text}]}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error searching prospects: {str(e)}"}]}


def create_crm_mcp_server():
    """Create the MCP server with all CRM tools"""

    if not CLAUDE_SDK_AVAILABLE:
        raise ImportError("claude-agent-sdk is required. Install with: pip install claude-agent-sdk")

    tools_instance = CRMAgentTools()

    # Define tools using the @tool decorator pattern
    @tool("search_companies", "Search for companies by name, city, or category", {
        "query": str,
        "city": str,
        "category": str,
        "limit": int
    })
    async def search_companies(args):
        return await tools_instance.search_companies(args)

    @tool("get_company_details", "Get detailed information about a specific company including invoices and alerts", {
        "company_id": int
    })
    async def get_company_details(args):
        return await tools_instance.get_company_details(args)

    @tool("update_company_notes", "Add or update notes for a company", {
        "company_id": int,
        "note": str,
        "append": bool
    })
    async def update_company_notes(args):
        return await tools_instance.update_company_notes(args)

    @tool("get_invoice_summary", "Get invoice and revenue summary for a company or overall", {
        "company_id": int,
        "year": str
    })
    async def get_invoice_summary(args):
        return await tools_instance.get_invoice_summary(args)

    @tool("get_alerts", "Get customer alerts like overdue customers, at-risk accounts, dormant customers", {
        "type": str,
        "priority": str,
        "city": str,
        "limit": int
    })
    async def get_alerts(args):
        return await tools_instance.get_alerts(args)

    @tool("create_trip", "Create a new sales trip/route for visiting customers", {
        "name": str,
        "date": str,
        "notes": str
    })
    async def create_trip(args):
        return await tools_instance.create_trip(args)

    @tool("add_trip_stop", "Add a company as a stop to an existing trip", {
        "trip_id": int,
        "company_id": int,
        "stop_order": int,
        "notes": str
    })
    async def add_trip_stop(args):
        return await tools_instance.add_trip_stop(args)

    @tool("get_trips", "Get planned sales trips and routes", {
        "date": str,
        "status": str
    })
    async def get_trips(args):
        return await tools_instance.get_trips(args)

    @tool("create_task", "Create a new sales task (call, email, meeting, follow-up, etc.)", {
        "title": str,
        "description": str,
        "task_type": str,
        "priority": int,
        "due_date": str,
        "company_id": int
    })
    async def create_task(args):
        return await tools_instance.create_task(args)

    @tool("get_tasks", "Get pending sales tasks", {
        "status": str,
        "due": str,
        "limit": int
    })
    async def get_tasks(args):
        return await tools_instance.get_tasks(args)

    @tool("search_prospects", "Search prospects in the sales pipeline", {
        "query": str,
        "status": str,
        "limit": int
    })
    async def search_prospects(args):
        return await tools_instance.search_prospects(args)

    # Create the MCP server
    return create_sdk_mcp_server(
        name="crm-tools",
        version="1.0.0",
        tools=[
            search_companies,
            get_company_details,
            update_company_notes,
            get_invoice_summary,
            get_alerts,
            create_trip,
            add_trip_stop,
            get_trips,
            create_task,
            get_tasks,
            search_prospects
        ]
    )


class ClaudeCRMAgentFallback:
    """
    Fallback CRM Agent using direct Anthropic API with tool calling.
    Used when Claude Agent SDK is not available.
    """

    def __init__(self):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")

        if not os.getenv('ANTHROPIC_API_KEY'):
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")

        self.tools_instance = CRMAgentTools()
        self.system_prompt = """You are Kelsy, a helpful CRM assistant for a coffee/beverage distribution company.
You help sales representatives manage their customer relationships via WhatsApp.

You can help with:
- Searching for companies/customers
- Looking up company details and invoices
- Adding notes to companies
- Checking customer alerts (overdue, at-risk)
- Creating and viewing trips/routes
- Managing tasks

Keep responses brief and mobile-friendly. Use bullet points when listing multiple items.
If a user mentions a company name, search for it first to get details.

IMPORTANT: Do NOT mention outstanding balances, payment status, or unpaid invoices. We don't track this data - all invoices are considered paid. Just focus on revenue totals and order counts."""

        # Define tools for Anthropic API
        self.tools = [
            {
                "name": "search_companies",
                "description": "Search for companies by name, city, or category",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query for company name"},
                        "city": {"type": "string", "description": "Filter by city"},
                        "limit": {"type": "integer", "description": "Max results (default 10)"}
                    }
                }
            },
            {
                "name": "get_company_details",
                "description": "Get detailed information about a company including invoices and alerts",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "company_id": {"type": "integer", "description": "The company ID"}
                    },
                    "required": ["company_id"]
                }
            },
            {
                "name": "update_company_notes",
                "description": "Add a note to a company",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "company_id": {"type": "integer", "description": "The company ID"},
                        "note": {"type": "string", "description": "The note to add"}
                    },
                    "required": ["company_id", "note"]
                }
            },
            {
                "name": "get_alerts",
                "description": "Get customer alerts (overdue, at-risk, dormant customers)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "Alert type: PATTERN_DISRUPTION, HIGH_VALUE_AT_RISK, DORMANT_CUSTOMER"},
                        "priority": {"type": "string", "description": "Priority: HIGH, MEDIUM, LOW"},
                        "city": {"type": "string", "description": "Filter by city"},
                        "limit": {"type": "integer", "description": "Max results"}
                    }
                }
            },
            {
                "name": "get_tasks",
                "description": "Get pending sales tasks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Task status: pending, completed"},
                        "due": {"type": "string", "description": "Filter: today, overdue, week"}
                    }
                }
            },
            {
                "name": "create_task",
                "description": "Create a new sales task",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "task_type": {"type": "string", "description": "Type: call, email, meeting, follow_up"},
                        "due_date": {"type": "string", "description": "Due date: today, tomorrow, or YYYY-MM-DD"},
                        "company_id": {"type": "integer", "description": "Link to company (optional)"}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "get_trips",
                "description": "Get planned sales trips/routes",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Filter: today, tomorrow, week"}
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Execute a tool and return the result"""
        tool_map = {
            "search_companies": self.tools_instance.search_companies,
            "get_company_details": self.tools_instance.get_company_details,
            "update_company_notes": self.tools_instance.update_company_notes,
            "get_alerts": self.tools_instance.get_alerts,
            "get_tasks": self.tools_instance.get_tasks,
            "create_task": self.tools_instance.create_task,
            "get_trips": self.tools_instance.get_trips,
        }

        if tool_name in tool_map:
            result = await tool_map[tool_name](tool_input)
            # Extract text from result
            if isinstance(result, dict) and "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        return item.get("text", "")
            return str(result)
        return f"Unknown tool: {tool_name}"

    async def process_message(self, message: str, conversation_history: List[Dict] = None) -> str:
        """Process a message using direct Anthropic API with tool calling"""
        try:
            messages = []

            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-6:]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # Add current message
            messages.append({"role": "user", "content": message})

            # Initial API call
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages
            )

            # Process tool calls in a loop
            max_iterations = 5
            iteration = 0

            while response.stop_reason == "tool_use" and iteration < max_iterations:
                iteration += 1

                # Extract tool use blocks
                tool_results = []
                assistant_content = response.content

                for block in response.content:
                    if block.type == "tool_use":
                        tool_result = await self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result
                        })

                # Add assistant response and tool results to messages
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})

                # Continue the conversation
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system=self.system_prompt,
                    tools=self.tools,
                    messages=messages
                )

            # Extract final text response
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            return final_text or "I processed your request. Is there anything else I can help with?"

        except Exception as e:
            print(f"Claude API error: {e}")
            return f"Sorry, I encountered an error: {str(e)[:100]}. Please try again."


class ClaudeCRMAgent:
    """Main Claude CRM Agent class for handling WhatsApp messages"""

    def __init__(self):
        # Try full SDK first, fall back to direct API
        self.use_sdk = CLAUDE_SDK_AVAILABLE
        self.fallback_agent = None

        if not os.getenv('ANTHROPIC_API_KEY'):
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")

        if self.use_sdk:
            try:
                self.mcp_server = create_crm_mcp_server()
                print("Using Claude Agent SDK")
            except Exception as e:
                print(f"SDK initialization failed, using fallback: {e}")
                self.use_sdk = False

        if not self.use_sdk:
            self.fallback_agent = ClaudeCRMAgentFallback()
            print("Using Anthropic API fallback")

        self.system_prompt = """You are a helpful CRM assistant for a coffee/beverage distribution company.
You help sales representatives manage their customer relationships via WhatsApp.

You have access to tools to:
- Search and view company/customer information
- Update notes on companies
- Check customer alerts (overdue, at-risk customers)
- Create and manage sales trips/routes
- Create and view tasks
- Search prospects in the pipeline

When users ask you to do something:
1. Use the appropriate tool to accomplish the task
2. Provide a clear, concise summary of what you did
3. If you need more information, ask for it

Keep responses brief and mobile-friendly since users are on WhatsApp.
Use bullet points and short paragraphs.

If a user mentions a company name, search for it first to get the company_id before performing other operations."""

    async def process_message(self, message: str, conversation_history: List[Dict] = None) -> str:
        """
        Process a WhatsApp message and return a response

        Args:
            message: The user's message
            conversation_history: Optional list of previous messages for context

        Returns:
            The agent's response text
        """
        # Use fallback if SDK not available
        if not self.use_sdk and self.fallback_agent:
            return await self.fallback_agent.process_message(message, conversation_history)

        try:
            # Build the prompt with conversation history if provided
            full_prompt = message
            if conversation_history:
                context = "\n".join([
                    f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
                    for m in conversation_history[-5:]  # Last 5 messages for context
                ])
                full_prompt = f"Previous conversation:\n{context}\n\nCurrent message: {message}"

            # Create async generator for streaming input (required for MCP)
            async def message_generator():
                yield {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": full_prompt
                    }
                }

            # Run the agent query
            result_text = ""

            async for msg in query(
                prompt=message_generator(),
                options=ClaudeAgentOptions(
                    system_prompt=self.system_prompt,
                    mcp_servers={"crm-tools": self.mcp_server},
                    allowed_tools=[
                        "mcp__crm-tools__search_companies",
                        "mcp__crm-tools__get_company_details",
                        "mcp__crm-tools__update_company_notes",
                        "mcp__crm-tools__get_invoice_summary",
                        "mcp__crm-tools__get_alerts",
                        "mcp__crm-tools__create_trip",
                        "mcp__crm-tools__add_trip_stop",
                        "mcp__crm-tools__get_trips",
                        "mcp__crm-tools__create_task",
                        "mcp__crm-tools__get_tasks",
                        "mcp__crm-tools__search_prospects"
                    ],
                    max_turns=10,
                    permission_mode="bypassPermissions"
                )
            ):
                # Extract the final result
                if hasattr(msg, 'result'):
                    result_text = msg.result
                elif hasattr(msg, 'type') and msg.type == 'assistant':
                    if hasattr(msg, 'message') and hasattr(msg.message, 'content'):
                        for block in msg.message.content:
                            if hasattr(block, 'text'):
                                result_text = block.text

            return result_text or "I processed your request but didn't generate a response. Please try again."

        except Exception as e:
            error_msg = str(e)
            print(f"Claude CRM Agent error: {error_msg}")

            # Try fallback on error
            if self.fallback_agent:
                print("Trying fallback agent...")
                return await self.fallback_agent.process_message(message, conversation_history)

            # Return user-friendly error
            if "API key" in error_msg.lower():
                return "Sorry, there's a configuration issue with the AI service. Please contact support."
            elif "rate limit" in error_msg.lower():
                return "I'm receiving too many requests right now. Please try again in a moment."
            else:
                return f"Sorry, I encountered an error processing your request. Please try again or rephrase your message."


# Convenience function for simple usage
async def process_whatsapp_message(message: str, conversation_history: List[Dict] = None) -> str:
    """
    Process a WhatsApp message using the Claude CRM Agent

    Args:
        message: The user's WhatsApp message
        conversation_history: Optional conversation history for context

    Returns:
        The agent's response
    """
    agent = ClaudeCRMAgent()
    return await agent.process_message(message, conversation_history)


# Test function
async def test_agent():
    """Test the Claude CRM Agent"""
    print("Testing Claude CRM Agent...\n")

    test_messages = [
        "Search for companies in Ghent",
        "Show me my overdue customer alerts",
        "What tasks do I have for today?",
    ]

    agent = ClaudeCRMAgent()

    for msg in test_messages:
        print(f"User: {msg}")
        response = await agent.process_message(msg)
        print(f"Agent: {response}\n")
        print("-" * 50)


if __name__ == "__main__":
    # Run test
    asyncio.run(test_agent())
