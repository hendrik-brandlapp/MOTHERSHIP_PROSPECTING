"""
Real DUANO API Examples

This file demonstrates how to use the DUANO client with the actual
DOUANO API endpoints for CRM and Accountancy data.
"""

import os
from datetime import datetime, timedelta
from duano_client import create_client, DuanoAPIError


def setup_client():
    """Setup and return a DUANO client instance"""
    # Option 1: Use environment variables
    client = create_client()
    
    # Option 2: Pass OAuth2 credentials directly with your subdomain
    # client = create_client(
    #     client_id="3",
    #     client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
    #     base_url="https://your-subdomain.douano.com",
    #     debug=True
    # )
    
    return client


def crm_examples():
    """Examples of working with CRM data"""
    print("=== CRM Data Examples ===")
    
    client = setup_client()
    
    try:
        # Test connection first
        if not client.test_connection():
            print("❌ Connection test failed")
            return
        
        print("✅ Connected to DOUANO API")
        
        # Get all contact persons
        print("\n👥 Getting contact persons...")
        contacts = client.crm.get_contact_persons()
        
        if contacts and 'result' in contacts:
            contact_data = contacts['result'].get('data', [])
            print(f"Found {len(contact_data)} contact persons")
            
            # Show first few contacts
            for contact in contact_data[:3]:
                print(f"  • {contact['name']} ({contact['email_address']}) - {contact['crm_company']['name']}")
            
            # Get specific contact details
            if contact_data:
                first_contact = contact_data[0]
                contact_id = first_contact['id']
                
                print(f"\n🔍 Getting details for contact {contact_id}...")
                contact_details = client.crm.get_contact_person(contact_id)
                
                if contact_details and 'result' in contact_details:
                    contact = contact_details['result']
                    print(f"Name: {contact['name']}")
                    print(f"Email: {contact['email_address']}")
                    print(f"Phone: {contact.get('phone_number', 'N/A')}")
                    print(f"Company: {contact['crm_company']['name']}")
                    print(f"Job Title: {contact.get('job_title', 'N/A')}")
                    print(f"Active: {contact['is_active']}")
        
        # Get contact persons with filters
        print("\n🔍 Getting active contact persons created since 2023...")
        filtered_contacts = client.crm.get_contact_persons(
            filter_by_created_since="2023-01-01",
            filter_by_is_active=True,
            order_by_name="asc"
        )
        
        if filtered_contacts and 'result' in filtered_contacts:
            filtered_data = filtered_contacts['result'].get('data', [])
            print(f"Found {len(filtered_data)} active contacts since 2023")
        
        # Get CRM actions
        print("\n📅 Getting CRM actions...")
        actions = client.crm.get_actions()
        
        if actions and 'result' in actions:
            action_data = actions['result'].get('data', [])
            print(f"Found {len(action_data)} actions")
            
            # Show action details
            for action in action_data[:3]:
                print(f"  • {action['subject']} - {action['status']} ({action['start_date']})")
                print(f"    Company: {action.get('crm_company', {}).get('name', 'N/A')}")
                print(f"    User: {action['user']['first_name']} {action['user']['last_name']}")
        
        # Get actions with filters
        print("\n📋 Getting pending actions...")
        pending_actions = client.crm.get_actions(
            filter_by_status="to_do",
            order_by_start_date="asc"
        )
        
        if pending_actions and 'result' in pending_actions:
            pending_data = pending_actions['result'].get('data', [])
            print(f"Found {len(pending_data)} pending actions")
    
    except DuanoAPIError as e:
        print(f"❌ CRM API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def accountancy_examples():
    """Examples of working with accountancy data"""
    print("\n=== Accountancy Data Examples ===")
    
    client = setup_client()
    
    try:
        # Get all accounts
        print("\n💰 Getting accounts...")
        accounts = client.accountancy.get_accounts()
        
        if accounts:
            print("✅ Retrieved accounts data")
            print(f"Response: {str(accounts)[:200]}...")
            
            # Try to get specific account if we have account data
            # Note: This depends on the actual response structure
            if isinstance(accounts, dict) and 'result' in accounts:
                account_data = accounts['result']
                if isinstance(account_data, list) and account_data:
                    first_account_id = account_data[0].get('id')
                    if first_account_id:
                        print(f"\n🔍 Getting details for account {first_account_id}...")
                        account_details = client.accountancy.get_account(first_account_id)
                        print(f"Account details: {str(account_details)[:200]}...")
        
        # Get accounts with filters
        print("\n🔍 Getting visible accounts ordered by number...")
        filtered_accounts = client.accountancy.get_accounts(
            filter_by_is_visible=True,
            order_by_number="asc"
        )
        
        if filtered_accounts:
            print("✅ Retrieved filtered accounts")
        
        # Test booking endpoint (if you have a booking ID)
        print("\n📊 Testing booking endpoint...")
        try:
            # This will likely fail without a valid booking ID, but shows the structure
            booking = client.accountancy.get_booking(1)  # Example ID
            print(f"Booking: {booking}")
        except Exception as e:
            print(f"  ℹ️  Booking test (expected to fail): {str(e)[:100]}...")
    
    except DuanoAPIError as e:
        print(f"❌ Accountancy API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def comprehensive_dashboard_example():
    """Example of creating a comprehensive dashboard with DOUANO data"""
    print("\n=== Comprehensive DOUANO Dashboard Example ===")
    
    client = setup_client()
    
    try:
        print("🚀 Building comprehensive DOUANO dashboard...")
        
        dashboard_data = {}
        
        # CRM metrics
        print("  👥 Fetching CRM metrics...")
        dashboard_data['crm'] = {}
        
        # All contacts
        all_contacts = client.crm.get_contact_persons()
        if all_contacts and 'result' in all_contacts:
            dashboard_data['crm']['total_contacts'] = len(all_contacts['result'].get('data', []))
            dashboard_data['crm']['contacts'] = all_contacts['result'].get('data', [])[:5]  # First 5
        
        # Active contacts
        active_contacts = client.crm.get_contact_persons(filter_by_is_active=True)
        if active_contacts and 'result' in active_contacts:
            dashboard_data['crm']['active_contacts'] = len(active_contacts['result'].get('data', []))
        
        # Recent actions
        recent_actions = client.crm.get_actions(order_by_start_date="desc")
        if recent_actions and 'result' in recent_actions:
            dashboard_data['crm']['recent_actions'] = recent_actions['result'].get('data', [])[:5]
        
        # Pending actions
        pending_actions = client.crm.get_actions(filter_by_status="to_do")
        if pending_actions and 'result' in pending_actions:
            dashboard_data['crm']['pending_actions'] = len(pending_actions['result'].get('data', []))
        
        # Accountancy overview
        print("  💰 Fetching accountancy overview...")
        dashboard_data['accountancy'] = {}
        
        accounts = client.accountancy.get_accounts()
        if accounts:
            dashboard_data['accountancy']['accounts'] = accounts
        
        # Display dashboard summary
        print("\n📈 DOUANO DASHBOARD SUMMARY")
        print("=" * 50)
        
        # CRM summary
        crm = dashboard_data.get('crm', {})
        print(f"👥 Total Contacts: {crm.get('total_contacts', 'N/A')}")
        print(f"✅ Active Contacts: {crm.get('active_contacts', 'N/A')}")
        print(f"⏳ Pending Actions: {crm.get('pending_actions', 'N/A')}")
        
        # Recent contacts
        contacts = crm.get('contacts', [])
        if contacts:
            print(f"\n👥 Recent Contacts:")
            for contact in contacts:
                print(f"  • {contact['name']} - {contact['crm_company']['name']}")
        
        # Recent actions
        actions = crm.get('recent_actions', [])
        if actions:
            print(f"\n📅 Recent Actions:")
            for action in actions:
                print(f"  • {action['subject']} ({action['status']})")
        
        # Accountancy summary
        if dashboard_data.get('accountancy', {}).get('accounts'):
            print(f"\n💰 Accountancy: ✅ Connected")
        else:
            print(f"\n💰 Accountancy: ❌ No data")
        
        print("\n✅ Dashboard data successfully compiled!")
        
    except DuanoAPIError as e:
        print(f"❌ Dashboard API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Run all examples"""
    print("🚀 DOUANO API Client Examples")
    print("Based on real API documentation")
    print("=" * 50)
    
    # Check if we have OAuth2 credentials
    if not os.getenv('DUANO_CLIENT_ID') or not os.getenv('DUANO_CLIENT_SECRET'):
        print("⚠️  Warning: DUANO_CLIENT_ID and DUANO_CLIENT_SECRET environment variables not set")
        print("Using default credentials from the provided configuration")
        print("\n💡 Important: Replace 'mijn-douano' with your actual DOUANO subdomain")
        print("\nTo use custom credentials, set these variables:")
        print("export DUANO_CLIENT_ID='your_client_id'")
        print("export DUANO_CLIENT_SECRET='your_client_secret'")
        print("export DUANO_API_BASE_URL='https://your-subdomain.douano.com'")
        print()
    
    # Run all examples
    crm_examples()
    accountancy_examples()
    comprehensive_dashboard_example()
    
    print("\n🎯 Next Steps:")
    print("1. Replace 'mijn-douano' with your actual DOUANO subdomain")
    print("2. Verify your OAuth2 credentials")
    print("3. Check network access to your DOUANO instance")
    print("4. Explore additional API endpoints as needed")
    
    print("\n🎉 All examples completed!")


if __name__ == "__main__":
    main()
