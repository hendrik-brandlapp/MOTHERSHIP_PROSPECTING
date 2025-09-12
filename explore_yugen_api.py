"""
Explore the Yugen DOUANO API to find working endpoints

This script systematically tests different endpoint patterns to discover
what's actually available in your Yugen instance.
"""

from duano_client import create_client, DuanoAPIError, AuthenticationError
import requests


def test_endpoint_patterns():
    """Test different API endpoint patterns"""
    print("🔍 Exploring Yugen DOUANO API Endpoints")
    print("=" * 50)
    
    # Create authenticated client
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com",
        debug=False  # Reduce noise
    )
    
    # Authenticate
    try:
        token = client.client_credentials_flow()
        print(f"✅ Authenticated successfully")
        print(f"🎫 Token: {token.access_token[:30]}...")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return
    
    # Test different endpoint patterns
    endpoints_to_test = [
        # Root endpoints
        ("/", "Root"),
        ("/api", "API Root"),
        ("/api/", "API Root with slash"),
        
        # Version endpoints
        ("/api/v1", "API v1"),
        ("/api/v1/", "API v1 with slash"),
        ("/api/public", "API Public"),
        ("/api/public/", "API Public with slash"),
        ("/api/public/v1", "API Public v1"),
        ("/api/public/v1/", "API Public v1 with slash"),
        
        # Health/Status endpoints
        ("/health", "Health"),
        ("/status", "Status"),
        ("/api/health", "API Health"),
        ("/api/status", "API Status"),
        ("/api/public/health", "Public Health"),
        ("/api/public/status", "Public Status"),
        ("/api/public/v1/health", "Public v1 Health"),
        ("/api/public/v1/status", "Public v1 Status"),
        
        # CRM endpoints (different patterns)
        ("/crm", "CRM Root"),
        ("/api/crm", "API CRM"),
        ("/api/public/crm", "Public CRM"),
        ("/api/public/v1/crm", "Public v1 CRM"),
        ("/api/public/v1/crm/", "Public v1 CRM with slash"),
        
        # Contact endpoints
        ("/api/public/v1/crm/contacts", "CRM Contacts"),
        ("/api/public/v1/crm/contact-persons", "CRM Contact Persons"),
        ("/api/public/v1/crm/crm-contact-persons", "CRM Contact Persons Full"),
        
        # Actions endpoints
        ("/api/public/v1/crm/actions", "CRM Actions"),
        ("/api/public/v1/crm/crm-actions", "CRM Actions Full"),
        
        # Accountancy endpoints
        ("/api/public/v1/accountancy", "Accountancy Root"),
        ("/api/public/v1/accountancy/", "Accountancy Root with slash"),
        ("/api/public/v1/accountancy/accounts", "Accountancy Accounts"),
        ("/api/public/v1/accountancy/bookings", "Accountancy Bookings"),
        
        # User/Auth endpoints
        ("/user", "User"),
        ("/me", "Me"),
        ("/api/user", "API User"),
        ("/api/me", "API Me"),
        ("/api/public/user", "Public User"),
        ("/api/public/me", "Public Me"),
        ("/api/public/v1/user", "Public v1 User"),
        ("/api/public/v1/me", "Public v1 Me"),
    ]
    
    working_endpoints = []
    
    print(f"\n🧪 Testing {len(endpoints_to_test)} endpoint patterns...")
    
    for endpoint, description in endpoints_to_test:
        try:
            response = client.get(endpoint)
            
            if response.success:
                print(f"✅ {endpoint} ({description}) - Status: {response.status_code}")
                working_endpoints.append((endpoint, description, response.status_code))
                
                # Show response preview
                if response.data:
                    data_preview = str(response.data)[:100]
                    print(f"   📊 Data: {data_preview}...")
                    
            else:
                status_code = response.status_code
                if status_code == 404:
                    print(f"❌ {endpoint} ({description}) - 404 Not Found")
                elif status_code == 401:
                    print(f"🔐 {endpoint} ({description}) - 401 Unauthorized")
                elif status_code == 403:
                    print(f"🚫 {endpoint} ({description}) - 403 Forbidden")
                elif status_code >= 500:
                    print(f"🔥 {endpoint} ({description}) - {status_code} Server Error")
                else:
                    print(f"⚠️  {endpoint} ({description}) - {status_code}")
                    
        except Exception as e:
            error_msg = str(e)
            if "500" in error_msg:
                print(f"🔥 {endpoint} ({description}) - Server Error")
            elif "404" in error_msg:
                print(f"❌ {endpoint} ({description}) - Not Found")
            elif "timeout" in error_msg.lower():
                print(f"⏰ {endpoint} ({description}) - Timeout")
            else:
                print(f"❌ {endpoint} ({description}) - Error: {error_msg[:50]}...")
    
    # Summary
    print(f"\n📋 Summary")
    print("=" * 20)
    
    if working_endpoints:
        print(f"✅ Found {len(working_endpoints)} working endpoints:")
        for endpoint, description, status_code in working_endpoints:
            print(f"  • {endpoint} - {description} ({status_code})")
    else:
        print("❌ No working endpoints found")
        
    print(f"\n💡 Next Steps:")
    if working_endpoints:
        print("1. ✅ OAuth2 authentication is working")
        print("2. ✅ Some endpoints are accessible")
        print("3. 🔧 Update client to use working endpoints")
        print("4. 📖 Check DOUANO documentation for correct endpoint structure")
    else:
        print("1. ✅ OAuth2 authentication is working")
        print("2. ❌ API endpoints may be different than documented")
        print("3. 📞 Contact DOUANO support for correct endpoint URLs")
        print("4. 🔧 Check if API access needs to be enabled for your account")
    
    return working_endpoints


def test_direct_http():
    """Test direct HTTP requests to understand response structure"""
    print(f"\n🌐 Testing Direct HTTP Requests")
    print("=" * 40)
    
    # Get a fresh token
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com"
    )
    
    token = client.client_credentials_flow()
    
    # Test with direct requests library
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'DUANO-Python-Client/1.0'
    }
    
    test_urls = [
        "https://yugen.douano.com/",
        "https://yugen.douano.com/api",
        "https://yugen.douano.com/api/public/v1",
        "https://yugen.douano.com/api/public/v1/crm",
    ]
    
    for url in test_urls:
        try:
            print(f"🧪 Testing: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(list(response.headers.items())[:3])}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   JSON: {str(data)[:100]}...")
                except:
                    print(f"   Text: {response.text[:100]}...")
            else:
                print(f"   Error: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   Exception: {str(e)[:100]}...")


def main():
    """Main exploration function"""
    print("🚀 Yugen DOUANO API Explorer")
    print("Discovering available endpoints and structure")
    print("=" * 60)
    
    # Test endpoint patterns
    working_endpoints = test_endpoint_patterns()
    
    # Test direct HTTP if needed
    if not working_endpoints:
        test_direct_http()
    
    print("\n🎯 Exploration Complete!")
    print("Use the working endpoints to update your client configuration.")


if __name__ == "__main__":
    main()
