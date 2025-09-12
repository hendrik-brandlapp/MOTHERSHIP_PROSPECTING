"""
Quick test script for DUANO API connection

This script tests the OAuth2 authentication and basic API connectivity
using the credentials from your screenshot.
"""

import sys
from duano_client import create_client, DuanoAPIError, AuthenticationError


def test_client_credentials():
    """Test OAuth2 client credentials flow with multiple base URLs"""
    print("🔐 Testing OAuth2 Client Credentials Flow")
    print("=" * 50)
    
    # Try different possible base URLs
    base_urls = [
        "https://api.duano.com",
        "https://duano.com/api",
        "https://app.duano.com",
        "https://api.duano.io",
        "https://duano.io/api",
        "https://duano-api.com",
        "https://api.duano.be",  # Belgium domain (common for EU companies)
        "https://duano.be/api",
        "http://localhost:8000",  # Local development
    ]
    
    for base_url in base_urls:
        print(f"\n🧪 Trying base URL: {base_url}")
        
        try:
            # Create client with your actual credentials
            client = create_client(
                client_id="3",
                client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
                base_url=base_url,
                debug=False  # Disable debug for cleaner output
            )
            
            print("✅ Client created successfully")
            print(f"🆔 Client ID: {client.client_id}")
            
            # Test authentication
            print("🔄 Attempting OAuth2 authentication...")
            token = client.client_credentials_flow()
            
            print("✅ Authentication successful!")
            print(f"🎫 Access Token: {token.access_token[:20]}...")
            print(f"📅 Token Type: {token.token_type}")
            print(f"⏰ Expires In: {token.expires_in} seconds")
            
            return client
            
        except AuthenticationError as e:
            if "Failed to resolve" in str(e) or "nodename nor servname" in str(e):
                print(f"  ❌ Domain not found: {base_url}")
            else:
                print(f"  ❌ Auth error: {str(e)[:100]}...")
        except Exception as e:
            if "Failed to resolve" in str(e) or "nodename nor servname" in str(e):
                print(f"  ❌ Domain not found: {base_url}")
            else:
                print(f"  ❌ Error: {str(e)[:100]}...")
    
    print("\n❌ No working base URL found")
    print("💡 This might mean:")
    print("   1. DUANO API is not publicly accessible")
    print("   2. You need VPN access to reach the API")
    print("   3. The API domain is different from what we tried")
    print("   4. The API requires different authentication")
    
    return None


def test_api_endpoints(client):
    """Test various API endpoints"""
    print("\n📡 Testing API Endpoints")
    print("=" * 30)
    
    # List of common API endpoints to test
    test_endpoints = [
        ('/api/v1/user', 'User info'),
        ('/api/v1/me', 'Current user'),
        ('/user', 'User profile'),
        ('/me', 'Profile'),
        ('/health', 'Health check'),
        ('/status', 'Status'),
        ('/api/health', 'API Health'),
        ('/api/status', 'API Status'),
        ('/ping', 'Ping'),
        ('/api/ping', 'API Ping'),
    ]
    
    successful_endpoints = []
    
    for endpoint, description in test_endpoints:
        try:
            print(f"🧪 Testing {endpoint} ({description})...")
            response = client.get(endpoint)
            
            if response.success:
                print(f"  ✅ Success: {response.status_code}")
                print(f"  📊 Data: {str(response.data)[:100]}...")
                successful_endpoints.append((endpoint, description))
            else:
                print(f"  ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:100]}...")
    
    return successful_endpoints


def test_data_modules(client):
    """Test the data modules (sales, orders, clients, products)"""
    print("\n📊 Testing Data Modules")
    print("=" * 25)
    
    modules = [
        (client.sales, 'Sales', [
            ('get_sales_summary', 'Sales Summary'),
            ('get_sales_by_period', 'Sales by Period'),
            ('get_top_products', 'Top Products'),
        ]),
        (client.orders, 'Orders', [
            ('list_orders', 'List Orders'),
        ]),
        (client.clients, 'Clients', [
            ('list_clients', 'List Clients'),
        ]),
        (client.products, 'Products', [
            ('list_products', 'List Products'),
        ]),
    ]
    
    successful_calls = []
    
    for module, module_name, methods in modules:
        print(f"\n🔍 Testing {module_name} Module:")
        
        for method_name, description in methods:
            try:
                print(f"  🧪 Testing {method_name} ({description})...")
                method = getattr(module, method_name)
                
                # Call with minimal parameters
                if method_name in ['get_top_products']:
                    result = method(limit=5)
                elif method_name in ['list_orders', 'list_clients', 'list_products']:
                    result = method(limit=5)
                else:
                    result = method()
                
                print(f"    ✅ Success: {str(result)[:100]}...")
                successful_calls.append((module_name, method_name, description))
                
            except Exception as e:
                print(f"    ❌ Error: {str(e)[:100]}...")
    
    return successful_calls


def main():
    """Main test function"""
    print("🚀 DUANO API Connection Test")
    print("Using credentials from your screenshot")
    print("=" * 60)
    
    # Test OAuth2 authentication
    client = test_client_credentials()
    
    if not client:
        print("\n❌ Cannot continue without successful authentication")
        sys.exit(1)
    
    # Test API endpoints
    successful_endpoints = test_api_endpoints(client)
    
    # Test data modules
    successful_calls = test_data_modules(client)
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 20)
    
    if successful_endpoints:
        print(f"✅ Working endpoints ({len(successful_endpoints)}):")
        for endpoint, desc in successful_endpoints:
            print(f"  • {endpoint} - {desc}")
    else:
        print("❌ No working endpoints found")
    
    if successful_calls:
        print(f"\n✅ Working module calls ({len(successful_calls)}):")
        for module, method, desc in successful_calls:
            print(f"  • {module}.{method} - {desc}")
    else:
        print("\n❌ No working module calls found")
    
    # Next steps
    print(f"\n🎯 Next Steps:")
    if successful_endpoints:
        print("1. ✅ OAuth2 authentication is working")
        print("2. ✅ API connection is established")
        if successful_calls:
            print("3. ✅ Some data modules are working")
            print("4. 🔧 Fine-tune endpoints based on actual DUANO API documentation")
        else:
            print("3. 🔧 Update endpoint URLs to match actual DUANO API structure")
            print("4. 📖 Check DUANO API documentation for correct endpoints")
    else:
        print("1. ✅ OAuth2 authentication is working")
        print("2. 🔧 Update base URL or endpoint paths")
        print("3. 📖 Verify DUANO API documentation for correct endpoints")
    
    print("\n🎉 Test completed!")


if __name__ == "__main__":
    main()
