"""
Quick Start Guide for DUANO API Client

Your client is ready to use! This shows you exactly how to get started.
"""

from duano_client import create_client

def main():
    """Quick start example"""
    print("🚀 DUANO API Client - Quick Start")
    print("=" * 40)
    
    # Create client (automatically uses your Yugen instance)
    client = create_client()
    
    # Or specify explicitly:
    # client = create_client(
    #     client_id="3",
    #     client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
    #     base_url="https://yugen.douano.com"
    # )
    
    try:
        # Test authentication
        print("🔐 Testing authentication...")
        token = client.client_credentials_flow()
        print(f"✅ Authenticated! Token expires in {token.expires_in} seconds")
        
        # When API endpoints are working, you can use:
        
        print("\n👥 CRM Examples (when API is fixed):")
        print("contacts = client.crm.get_contact_persons()")
        print("contact = client.crm.get_contact_person(153)")
        print("actions = client.crm.get_actions(filter_by_status='to_do')")
        
        print("\n💰 Accountancy Examples (when API is fixed):")
        print("accounts = client.accountancy.get_accounts()")
        print("account = client.accountancy.get_account(123)")
        print("booking = client.accountancy.get_booking(456)")
        
        print("\n🎯 Your client is ready!")
        print("Just waiting for the API endpoints to be fixed.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
