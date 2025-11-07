#!/usr/bin/env python3
"""
Script to fetch all 2025 sales invoices from Douano API and store them in Supabase.
This extracts raw invoice data and populates the sales_2025 table.
"""

import os
import json
import sys
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Try to import supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("⚠️  Supabase package not available. Install with: pip install supabase")
    SUPABASE_AVAILABLE = False

# Configuration
DOUANO_API_BASE = os.getenv('DOUANO_API_BASE_URL', 'https://yugen.douano.com')
DOUANO_ACCESS_TOKEN = os.getenv('DOUANO_ACCESS_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://gpjoypslbrpvnhqzvacc.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdwam95cHNsYnJwdm5ocXp2YWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM3MDQxNTAsImV4cCI6MjA2OTI4MDE1MH0.u0hGzIKziSPz2i576NhuyCetV6_iQwCoft7FIjDJCiI')


def get_douano_headers():
    """Get headers for Douano API requests."""
    if not DOUANO_ACCESS_TOKEN:
        raise ValueError("DOUANO_ACCESS_TOKEN not found in environment")
    
    return {
        'Authorization': f'Bearer {DOUANO_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }


def fetch_all_2025_invoices():
    """
    Fetch all sales invoices from 2025 using pagination.
    Returns a list of all invoice records.
    """
    all_invoices = []
    page = 1
    per_page = 100
    
    print("📡 Fetching 2025 sales invoices from Douano API...")
    
    while True:
        url = f"{DOUANO_API_BASE}/api/public/v1/trade/sales-invoices"
        params = {
            'per_page': per_page,
            'page': page,
            'filter_by_start_date': '2025-01-01',
            'filter_by_end_date': '2025-12-31',
            'order_by_date': 'desc'
        }
        
        try:
            response = requests.get(url, headers=get_douano_headers(), params=params)
            response.raise_for_status()
            
            data = response.json()
            invoices = data.get('result', {}).get('data', [])
            
            if not invoices:
                print(f"✅ No more invoices found on page {page}")
                break
            
            all_invoices.extend(invoices)
            print(f"📄 Fetched page {page}: {len(invoices)} invoices (Total: {len(all_invoices)})")
            
            # Check if there are more pages
            current_page = data.get('result', {}).get('current_page', page)
            last_page = data.get('result', {}).get('last_page', page)
            
            if current_page >= last_page:
                print(f"✅ Reached last page ({last_page})")
                break
            
            page += 1
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching page {page}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            break
    
    print(f"\n✅ Total invoices fetched: {len(all_invoices)}")
    return all_invoices


def extract_invoice_fields(invoice):
    """Extract key fields from invoice data for easy querying."""
    company = invoice.get('company', {})
    if isinstance(company, dict):
        company_id = company.get('id')
        company_name = company.get('name') or company.get('public_name')
    else:
        company_id = None
        company_name = None
    
    return {
        'invoice_id': invoice.get('id'),
        'invoice_data': invoice,  # Store complete raw data
        'company_id': company_id,
        'company_name': company_name,
        'invoice_number': invoice.get('invoice_number') or invoice.get('number'),
        'invoice_date': invoice.get('date'),
        'due_date': invoice.get('due_date'),
        'total_amount': invoice.get('payable_amount_without_financial_discount') or invoice.get('total_amount'),
        'balance': invoice.get('balance'),
        'is_paid': invoice.get('balance', 0) == 0
    }


def save_to_supabase(invoices):
    """Save invoices to Supabase table."""
    if not SUPABASE_AVAILABLE:
        print("❌ Supabase not available. Cannot save data.")
        return False
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"\n💾 Saving {len(invoices)} invoices to Supabase...")
        
        saved_count = 0
        updated_count = 0
        error_count = 0
        
        for invoice in invoices:
            try:
                record = extract_invoice_fields(invoice)
                
                # Try to insert, if conflict (duplicate invoice_id), update
                # First, check if record exists
                existing = supabase.table('sales_2025').select('id').eq('invoice_id', record['invoice_id']).execute()
                
                if existing.data:
                    # Update existing record
                    record['updated_at'] = datetime.now().isoformat()
                    result = supabase.table('sales_2025').update(record).eq('invoice_id', record['invoice_id']).execute()
                    updated_count += 1
                    if updated_count % 10 == 0:
                        print(f"  📝 Updated {updated_count} records...")
                else:
                    # Insert new record
                    result = supabase.table('sales_2025').insert(record).execute()
                    saved_count += 1
                    if saved_count % 10 == 0:
                        print(f"  💾 Saved {saved_count} records...")
                
            except Exception as e:
                error_count += 1
                print(f"  ❌ Error saving invoice {record.get('invoice_id')}: {e}")
        
        print(f"\n✅ Successfully saved: {saved_count}")
        print(f"📝 Updated: {updated_count}")
        if error_count > 0:
            print(f"❌ Errors: {error_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return False


def save_to_json_backup(invoices, filename='2025_invoices_backup.json'):
    """Save invoices to a JSON file as backup."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(invoices, f, indent=2, ensure_ascii=False, default=str)
        print(f"💾 Backup saved to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving backup: {e}")
        return False


def main():
    """Main execution function."""
    print("=" * 60)
    print("🚀 2025 Sales Invoice Sync Tool")
    print("=" * 60)
    
    # Check configuration
    if not DOUANO_ACCESS_TOKEN:
        print("❌ DOUANO_ACCESS_TOKEN not configured")
        print("Please set it in your .env file or environment variables")
        sys.exit(1)
    
    # Fetch invoices
    invoices = fetch_all_2025_invoices()
    
    if not invoices:
        print("⚠️  No invoices found for 2025")
        return
    
    # Save backup
    print("\n" + "=" * 60)
    save_to_json_backup(invoices)
    
    # Save to Supabase
    print("\n" + "=" * 60)
    if SUPABASE_AVAILABLE:
        save_to_supabase(invoices)
    else:
        print("⚠️  Skipping Supabase sync (package not available)")
    
    print("\n" + "=" * 60)
    print("✅ Sync completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()

