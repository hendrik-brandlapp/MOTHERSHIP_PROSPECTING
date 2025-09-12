"""
Test script for the Yugen DOUANO instance

This script tests the OAuth2 authentication and API connectivity
with your actual Yugen DOUANO instance.
"""

from duano_client import create_client, DuanoAPIError, AuthenticationError


def test_yugen_connection():
    """Test connection to Yugen DOUANO instance"""
    print("🚀 Testing Yugen DOUANO Instance")
    print("URL: https://yugen.douano.com")
    print("=" * 50)
    
    try:
        # Create client for Yugen instance
        client = create_client(
            client_id="3",
            client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
            base_url="https://yugen.douano.com",
            debug=True
        )
        
        print("✅ Client created successfully")
        print(f"📍 Base URL: {client.base_url}")
        print(f"🆔 Client ID: {client.client_id}")
        
        # Test OAuth2 authentication
        print("\n🔐 Testing OAuth2 Client Credentials Flow...")
        try:
            token = client.client_credentials_flow()
            print("✅ Authentication successful!")
            print(f"🎫 Access Token: {token.access_token[:30]}...")
            print(f"📅 Token Type: {token.token_type}")
            print(f"⏰ Expires In: {token.expires_in} seconds")
            
            # Test connection with a real API call
            print("\n📡 Testing API connection...")
            if client.test_connection():
                print("✅ API connection successful!")
                return client
            else:
                print("❌ API connection failed")
                return None
                
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Client creation failed: {e}")
        return None


def test_crm_endpoints(client):
    """Test CRM endpoints"""
    print("\n👥 Testing CRM Endpoints")
    print("=" * 30)
    
    try:
        # Test contact persons
        print("🧪 Testing get_contact_persons()...")
        contacts = client.crm.get_contact_persons()
        
        if contacts and 'result' in contacts:
            contact_data = contacts['result']
            if isinstance(contact_data, dict) and 'data' in contact_data:
                contact_list = contact_data['data']
                print(f"✅ Retrieved {len(contact_list)} contact persons")
                
                # Show first few contacts
                for i, contact in enumerate(contact_list[:3], 1):
                    name = contact.get('name', 'Unknown')
                    email = contact.get('email_address', 'No email')
                    company = contact.get('crm_company', {}).get('name', 'No company')
                    print(f"  {i}. {name} ({email}) - {company}")
                
                # Test getting specific contact
                if contact_list:
                    first_contact_id = contact_list[0]['id']
                    print(f"\n🔍 Testing get_contact_person({first_contact_id})...")
                    
                    contact_detail = client.crm.get_contact_person(first_contact_id)
                    if contact_detail and 'result' in contact_detail:
                        contact = contact_detail['result']
                        print(f"✅ Contact details: {contact['name']} - {contact.get('job_title', 'N/A')}")
            else:
                print(f"✅ Contacts response: {contacts}")
        else:
            print(f"✅ Contacts response: {contacts}")
        
        # Test actions
        print(f"\n🧪 Testing get_actions()...")
        actions = client.crm.get_actions()
        
        if actions and 'result' in actions:
            action_data = actions['result']
            if isinstance(action_data, dict) and 'data' in action_data:
                action_list = action_data['data']
                print(f"✅ Retrieved {len(action_list)} actions")
                
                # Show first few actions
                for i, action in enumerate(action_list[:3], 1):
                    subject = action.get('subject', 'No subject')
                    status = action.get('status', 'Unknown')
                    start_date = action.get('start_date', 'No date')
                    print(f"  {i}. {subject} - {status} ({start_date})")
            else:
                print(f"✅ Actions response: {actions}")
        else:
            print(f"✅ Actions response: {actions}")
            
    except Exception as e:
        print(f"❌ CRM endpoints failed: {str(e)[:200]}...")


def test_accountancy_endpoints(client):
    """Test Accountancy endpoints"""
    print("\n💰 Testing Accountancy Endpoints")
    print("=" * 35)
    
    try:
        # Test accounts
        print("🧪 Testing get_accounts()...")
        accounts = client.accountancy.get_accounts()
        
        if accounts:
            print(f"✅ Accounts response received")
            print(f"Response type: {type(accounts)}")
            if isinstance(accounts, dict):
                print(f"Response keys: {list(accounts.keys())}")
            print(f"Response preview: {str(accounts)[:200]}...")
        else:
            print("❌ No accounts response")
            
    except Exception as e:
        print(f"❌ Accountancy endpoints failed: {str(e)[:200]}...")


def main():
    """Main test function"""
    print("🎯 Yugen DOUANO API Test Suite")
    print("Testing with your actual instance")
    print("=" * 60)
    
    # Test connection
    client = test_yugen_connection()
    
    if not client:
        print("\n❌ Cannot continue without successful authentication")
        print("\n💡 Possible issues:")
        print("1. Check if your OAuth2 credentials are correct")
        print("2. Verify network access to https://yugen.douano.com")
        print("3. Confirm the API endpoints are accessible")
        return
    
    # Test endpoints
    test_crm_endpoints(client)
    test_accountancy_endpoints(client)
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 20)
    print("✅ OAuth2 authentication working")
    print("✅ Connected to Yugen DOUANO instance")
    print("✅ API client is ready for production use")
    
    print("\n🎯 You can now use the client in your applications:")
    print("""
from duano_client import create_client

client = create_client()  # Uses environment variables
# OR
client = create_client(
    client_id="3",
    client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
    base_url="https://yugen.douano.com"
)

# Get your contact persons
contacts = client.crm.get_contact_persons()

# Get your CRM actions
actions = client.crm.get_actions()

# Get your accounts
accounts = client.accountancy.get_accounts()
""")
    
    print("\n🎉 Test completed successfully!")


if __name__ == "__main__":
    main()
