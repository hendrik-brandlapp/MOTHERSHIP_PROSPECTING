"""
Check DOUANO Environment Settings

Based on the Postman screenshot showing "Douano Public" environment,
let's check if we need specific environment configurations.
"""

import requests
import json
from duano_client import create_client


def test_different_base_urls():
    """Test different base URL patterns that might be environment-specific"""
    print("🌍 Testing Different Environment Base URLs")
    print("=" * 50)
    
    # Get token with current setup
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com"
    )
    
    token = client.client_credentials_flow()
    print(f"✅ Token obtained: {token.access_token[:30]}...")
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Try different base URL patterns
    base_urls = [
        "https://yugen.douano.com",
        "https://api.yugen.douano.com",
        "https://yugen-api.douano.com", 
        "https://public.yugen.douano.com",
        "https://yugen.douano.com/public",
        "https://yugen.douano.com/api",
        "https://prod.yugen.douano.com",
        "https://app.yugen.douano.com"
    ]
    
    test_endpoint = "/api/public/v1/core/company-categories"
    
    for base_url in base_urls:
        full_url = f"{base_url}{test_endpoint}"
        print(f"\n🧪 Testing: {base_url}")
        print(f"   Full URL: {full_url}")
        
        try:
            response = requests.get(full_url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   🎉 SUCCESS! Found working base URL!")
                try:
                    data = response.json()
                    print(f"   📊 Data: {str(data)[:150]}...")
                    return base_url
                except:
                    print(f"   📄 Non-JSON response")
            elif response.status_code == 404:
                print(f"   ❌ Not found")
            elif response.status_code == 500:
                print(f"   🔥 Server error (same issue)")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   🌐 Connection failed (domain doesn't exist)")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    return None


def check_postman_environment_variables():
    """Check what environment variables Postman might be using"""
    print(f"\n📋 Checking Postman Environment Variables")
    print("=" * 50)
    
    print("From your Postman screenshot, I can see:")
    print("✅ Environment: 'Douano Public'")
    print("✅ Language: 'Python - Requests'")
    print("✅ Layout: 'Double Column'")
    
    print(f"\n💡 Common Postman Environment Variables:")
    print("- {{base_url}} or {{baseUrl}}")
    print("- {{api_url}} or {{apiUrl}}")
    print("- {{host}} or {{hostname}}")
    print("- {{environment}} or {{env}}")
    print("- {{client_id}} and {{client_secret}}")
    print("- {{access_token}} or {{token}}")
    
    print(f"\n🔍 Let's check if there are environment-specific endpoints...")


def test_with_postman_headers():
    """Test with headers that Postman might be adding automatically"""
    print(f"\n🔧 Testing with Postman-like Configuration")
    print("=" * 50)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    # Headers that Postman might add for the "Douano Public" environment
    postman_headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'PostmanRuntime/7.32.3',
        'Postman-Token': 'generated-uuid-here',
        'Host': 'yugen.douano.com',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    endpoint = "/api/public/v1/core/company-categories"
    url = f"https://yugen.douano.com{endpoint}"
    
    print(f"🧪 Testing with Postman-style headers:")
    for key, value in postman_headers.items():
        if key == 'Authorization':
            print(f"   {key}: Bearer {value.split()[-1][:20]}...")
        else:
            print(f"   {key}: {value}")
    
    try:
        response = requests.get(url, headers=postman_headers, timeout=15)
        print(f"\n   📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   🎉 SUCCESS with Postman headers!")
            try:
                data = response.json()
                print(f"   📊 Data: {str(data)[:200]}...")
                return True
            except:
                print(f"   📄 Non-JSON response")
        else:
            print(f"   ❌ Still getting status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}...")
    
    return False


def check_oauth_token_scopes():
    """Check if our OAuth token has the right scopes"""
    print(f"\n🔐 Checking OAuth Token Details")
    print("=" * 40)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    print(f"🎫 Token Information:")
    print(f"   Access Token: {token.access_token[:50]}...")
    print(f"   Token Type: {token.token_type}")
    print(f"   Expires In: {token.expires_in} seconds")
    print(f"   Scope: {token.scope if token.scope else 'None specified'}")
    
    # Try to decode JWT token (if it's a JWT)
    if token.access_token.count('.') == 2:
        print(f"\n🔍 JWT Token detected - checking claims...")
        try:
            import base64
            
            # Split JWT parts
            header, payload, signature = token.access_token.split('.')
            
            # Decode payload (add padding if needed)
            payload += '=' * (4 - len(payload) % 4)
            decoded_payload = base64.urlsafe_b64decode(payload)
            
            payload_data = json.loads(decoded_payload)
            print(f"   📋 Token Claims:")
            
            for key, value in payload_data.items():
                if key in ['sub', 'aud', 'iss', 'exp', 'iat', 'scope', 'scopes']:
                    print(f"     {key}: {value}")
            
            # Check if we have the right scopes
            if 'scope' in payload_data or 'scopes' in payload_data:
                scopes = payload_data.get('scope', payload_data.get('scopes', ''))
                print(f"   🔍 Available scopes: {scopes}")
            else:
                print(f"   ⚠️  No scope information in token")
                
        except Exception as e:
            print(f"   ❌ Could not decode JWT: {e}")
    else:
        print(f"   📄 Opaque token (not JWT)")


def test_environment_specific_endpoints():
    """Test if there are environment-specific endpoint patterns"""
    print(f"\n🌍 Testing Environment-Specific Endpoints")
    print("=" * 50)
    
    client = create_client()
    token = client.client_credentials_flow()
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test different endpoint patterns that might be environment-specific
    endpoint_patterns = [
        "/api/public/v1/core/company-categories",  # Current
        "/api/v1/core/company-categories",         # Without 'public'
        "/public/v1/core/company-categories",      # Without 'api'
        "/v1/core/company-categories",             # Minimal
        "/api/douano/v1/core/company-categories",  # With 'douano'
        "/api/prod/v1/core/company-categories",    # Production
        "/api/live/v1/core/company-categories",    # Live
    ]
    
    for endpoint in endpoint_patterns:
        url = f"https://yugen.douano.com{endpoint}"
        print(f"\n🧪 Testing: {endpoint}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   🎉 WORKING ENDPOINT FOUND!")
                try:
                    data = response.json()
                    print(f"   📊 Data: {str(data)[:150]}...")
                    return endpoint
                except:
                    print(f"   📄 Non-JSON response")
            elif response.status_code != 500 and response.status_code != 404:
                print(f"   ⚠️  Different status - might be close!")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    return None


def main():
    """Main function to check environment settings"""
    print("🔍 DOUANO Environment Settings Check")
    print("Based on your Postman screenshot showing 'Douano Public' environment")
    print("=" * 70)
    
    # Check Postman environment variables
    check_postman_environment_variables()
    
    # Test different base URLs
    working_base_url = test_different_base_urls()
    
    if working_base_url:
        print(f"\n🎉 Found working base URL: {working_base_url}")
        return
    
    # Test with Postman-style headers
    postman_works = test_with_postman_headers()
    
    if postman_works:
        print(f"\n🎉 Postman headers work!")
        return
    
    # Check OAuth token details
    check_oauth_token_scopes()
    
    # Test environment-specific endpoints
    working_endpoint = test_environment_specific_endpoints()
    
    if working_endpoint:
        print(f"\n🎉 Found working endpoint pattern: {working_endpoint}")
        return
    
    print(f"\n🤔 Environment Analysis Summary")
    print("=" * 40)
    print("✅ OAuth2 authentication working perfectly")
    print("❌ All tested environment configurations still return 500 errors")
    print("🔍 The 'Douano Public' environment in Postman might have:")
    print("   - Different base URL variables")
    print("   - Special headers or authentication")
    print("   - Different endpoint structure")
    
    print(f"\n💡 Next Steps:")
    print("1. Check Postman environment variables (click the eye icon)")
    print("2. Export Postman environment settings")
    print("3. Compare with our current configuration")
    print("4. Contact DOUANO with environment details")


if __name__ == "__main__":
    main()
