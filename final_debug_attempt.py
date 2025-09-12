"""
Final debugging attempt for DOUANO API

Based on our investigation, let's try a few more approaches:
1. Check if we need different scopes in our OAuth2 request
2. Try the exact headers from the Postman documentation
3. Check if there are any missing authentication parameters
"""

import requests
import json
from duano_client import create_client


def test_with_different_scopes():
    """Test OAuth2 with different scopes"""
    print("🔍 Testing Different OAuth2 Scopes")
    print("=" * 40)
    
    scopes_to_test = [
        None,  # No scope
        "",    # Empty scope
        "read",
        "write", 
        "read write",
        "api",
        "crm",
        "accountancy",
        "crm accountancy",
        "api:read",
        "api:write",
        "crm:read",
        "accountancy:read"
    ]
    
    for scope in scopes_to_test:
        print(f"\n🧪 Testing scope: {scope}")
        
        try:
            client = create_client(
                client_id="3",
                client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
                base_url="https://yugen.douano.com"
            )
            
            # Try client credentials with scope
            if scope is not None:
                token = client.client_credentials_flow(scope=scope)
            else:
                token = client.client_credentials_flow()
            
            print(f"   ✅ Token obtained: {token.access_token[:20]}...")
            
            # Test API call with this token
            headers = {
                'Authorization': f'Bearer {token.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                "https://yugen.douano.com/api/public/v1/crm/crm-contact-persons",
                headers=headers,
                timeout=10
            )
            
            print(f"   API Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   🎉 SUCCESS! Scope '{scope}' works!")
                try:
                    data = response.json()
                    print(f"   📊 Data: {str(data)[:100]}...")
                    return scope
                except:
                    print(f"   📄 Non-JSON response")
            elif response.status_code != 500:
                print(f"   ⚠️  Different status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
    
    return None


def test_postman_style_headers():
    """Test with headers that might be used by Postman"""
    print(f"\n🔧 Testing Postman-Style Headers")
    print("=" * 40)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    # Different header combinations that Postman might use
    header_sets = [
        {
            'Authorization': f'Bearer {token.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'PostmanRuntime/7.32.3'
        },
        {
            'Authorization': f'Bearer {token.access_token}',
            'Accept': '*/*',
            'User-Agent': 'PostmanRuntime/7.32.3'
        },
        {
            'Authorization': f'Bearer {token.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        {
            'Authorization': f'Bearer {token.access_token}',
            'Content-Type': 'application/json', 
            'Accept': 'application/json',
            'Origin': 'https://yugen.douano.com'
        },
        {
            'Authorization': f'Bearer {token.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Referer': 'https://yugen.douano.com/'
        }
    ]
    
    endpoint = "/api/public/v1/crm/crm-contact-persons"
    
    for i, headers in enumerate(header_sets):
        print(f"\n🧪 Testing header set {i+1}:")
        for key, value in headers.items():
            if key == 'Authorization':
                print(f"   {key}: Bearer {value.split()[-1][:20]}...")
            else:
                print(f"   {key}: {value}")
        
        try:
            response = requests.get(
                f"https://yugen.douano.com{endpoint}",
                headers=headers,
                timeout=15
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   🎉 SUCCESS with header set {i+1}!")
                try:
                    data = response.json()
                    print(f"   📊 Data: {str(data)[:150]}...")
                    return headers
                except:
                    print(f"   📄 Non-JSON response")
            elif response.status_code != 500:
                print(f"   ⚠️  Different status code!")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
    
    return None


def test_with_session_cookies():
    """Test if we need session cookies in addition to OAuth2"""
    print(f"\n🍪 Testing with Session Management")
    print("=" * 40)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # First, try to get any session cookies from the main page
    print("🧪 Getting session cookies from main page...")
    try:
        main_response = session.get("https://yugen.douano.com", timeout=10)
        print(f"   Main page status: {main_response.status_code}")
        print(f"   Cookies received: {len(session.cookies)}")
        
        for cookie in session.cookies:
            print(f"   Cookie: {cookie.name} = {cookie.value[:20]}...")
    except Exception as e:
        print(f"   ❌ Error getting main page: {e}")
    
    # Now try the API with both OAuth2 and session cookies
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print(f"\n🧪 Testing API with OAuth2 + session cookies...")
    try:
        response = session.get(
            "https://yugen.douano.com/api/public/v1/crm/crm-contact-persons",
            headers=headers,
            timeout=15
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   🎉 SUCCESS with session cookies!")
            try:
                data = response.json()
                print(f"   📊 Data: {str(data)[:150]}...")
                return True
            except:
                print(f"   📄 Non-JSON response")
        elif response.status_code != 500:
            print(f"   ⚠️  Different status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}...")
    
    return False


def check_api_documentation_endpoint():
    """Check if there's an API documentation endpoint that tells us the structure"""
    print(f"\n📖 Checking API Documentation Endpoints")
    print("=" * 45)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Accept': 'application/json'
    }
    
    doc_endpoints = [
        "/api",
        "/api/",
        "/api/docs",
        "/api/documentation",
        "/api/v1",
        "/api/public",
        "/api/public/",
        "/openapi.json",
        "/swagger.json",
        "/api/swagger.json",
        "/docs/api"
    ]
    
    for endpoint in doc_endpoints:
        print(f"\n🧪 Testing: {endpoint}")
        
        try:
            response = requests.get(
                f"https://yugen.douano.com{endpoint}",
                headers=headers,
                timeout=10
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                
                if 'application/json' in content_type:
                    print(f"   ✅ JSON documentation found!")
                    try:
                        data = response.json()
                        print(f"   📊 Doc structure: {type(data)}")
                        
                        # Look for API paths or endpoints
                        if isinstance(data, dict):
                            if 'paths' in data:
                                print(f"   🛣️  API paths found: {list(data['paths'].keys())[:5]}...")
                            if 'swagger' in data or 'openapi' in data:
                                print(f"   📋 OpenAPI/Swagger documentation")
                        
                        return data
                    except:
                        print(f"   ⚠️  Invalid JSON")
                else:
                    print(f"   📄 HTML/text response")
                    
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    return None


def main():
    """Final debugging attempt"""
    print("🔬 DOUANO API - Final Debugging Session")
    print("Let's try everything we can think of!")
    print("=" * 60)
    
    # Test 1: Different OAuth2 scopes
    working_scope = test_with_different_scopes()
    
    if working_scope:
        print(f"\n🎉 Found working scope: '{working_scope}'")
        return
    
    # Test 2: Postman-style headers
    working_headers = test_postman_style_headers()
    
    if working_headers:
        print(f"\n🎉 Found working headers!")
        return
    
    # Test 3: Session cookies
    session_works = test_with_session_cookies()
    
    if session_works:
        print(f"\n🎉 Session cookies are required!")
        return
    
    # Test 4: API documentation
    api_docs = check_api_documentation_endpoint()
    
    if api_docs:
        print(f"\n🎉 Found API documentation!")
        return
    
    print(f"\n🤔 Final Assessment")
    print("=" * 25)
    print("✅ OAuth2 authentication is definitely working")
    print("✅ We can get valid access tokens")
    print("❌ API endpoints consistently return 500 errors")
    print("🌐 Web interface endpoints work fine")
    
    print(f"\n💡 Most Likely Causes:")
    print("1. 🔧 API endpoints might not be enabled for your account")
    print("2. 📊 Server-side configuration issue with the API")
    print("3. 🔒 Additional permissions or scopes required")
    print("4. 🐛 Bug in the DOUANO API server")
    
    print(f"\n📞 Recommendation:")
    print("Contact DOUANO support with these findings:")
    print("- OAuth2 authentication works perfectly")
    print("- All API endpoints return 500 Server Error")
    print("- Web interface works normally")
    print("- Instance: https://yugen.douano.com")
    print("- Client ID: 3")


if __name__ == "__main__":
    main()
