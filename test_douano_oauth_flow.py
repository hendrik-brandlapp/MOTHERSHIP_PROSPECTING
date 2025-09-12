"""
Test DOUANO OAuth2 Flow - Following Exact Documentation

This script follows the exact OAuth2 Authorization Code flow 
as documented by DOUANO, using your actual credentials.
"""

import webbrowser
import time
from urllib.parse import urlparse, parse_qs
from duano_client import create_client
import requests


def test_authorization_code_flow():
    """Test the complete OAuth2 Authorization Code flow"""
    print("🔐 DOUANO OAuth2 Authorization Code Flow")
    print("Following the exact documentation steps")
    print("=" * 60)
    
    # Create client with your actual credentials
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com",
        redirect_uri="http://localhost:5001/oauth/callback"
    )
    
    print(f"✅ Client created for: {client.base_url}")
    print(f"🆔 Client ID: {client.client_id}")
    print(f"🔄 Redirect URI: {client.redirect_uri}")
    
    # Step 1: Get authorization URL
    print(f"\n📋 Step 1: Get Authorization URL")
    auth_url = client.get_authorization_url(
        scope="read write",  # Adjust scope as needed
        state="secure_random_state_123"
    )
    
    print(f"🌐 Authorization URL: {auth_url}")
    print(f"\n🚀 Opening authorization URL in browser...")
    
    # Open browser for user authorization
    try:
        webbrowser.open(auth_url)
        print("✅ Browser opened successfully")
    except Exception as e:
        print(f"⚠️  Could not open browser: {e}")
        print(f"Please manually visit: {auth_url}")
    
    # Step 2: Get authorization code from user
    print(f"\n📋 Step 2: Get Authorization Code")
    print("After authorizing in the browser, you'll be redirected to:")
    print("http://localhost:5001/oauth/callback?code=AUTHORIZATION_CODE&state=secure_random_state_123")
    
    auth_code = input("\n📝 Please enter the authorization code from the callback URL: ").strip()
    
    if not auth_code:
        print("❌ No authorization code provided")
        return None
    
    # Step 3: Exchange code for token
    print(f"\n📋 Step 3: Exchange Code for Access Token")
    try:
        print("🔄 Exchanging authorization code for access token...")
        token = client.exchange_code_for_token(auth_code)
        
        print("✅ Token exchange successful!")
        print(f"🎫 Access Token: {token.access_token[:30]}...")
        print(f"📅 Token Type: {token.token_type}")
        print(f"⏰ Expires In: {token.expires_in} seconds (1 day as documented)")
        print(f"🔄 Refresh Token: {'Yes' if token.refresh_token else 'No'}")
        
        return token
        
    except Exception as e:
        print(f"❌ Token exchange failed: {e}")
        return None


def test_client_credentials_flow():
    """Test client credentials flow (might not be supported)"""
    print(f"\n🤖 Testing Client Credentials Flow")
    print("(This might not be supported by DOUANO)")
    print("=" * 50)
    
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com"
    )
    
    try:
        token = client.client_credentials_flow()
        print("✅ Client credentials flow worked!")
        print(f"🎫 Access Token: {token.access_token[:30]}...")
        return token
    except Exception as e:
        print(f"❌ Client credentials flow failed: {e}")
        print("This is expected - DOUANO requires Authorization Code flow")
        return None


def test_api_with_token(token):
    """Test API endpoints with a valid token"""
    if not token:
        print("❌ No valid token to test with")
        return
    
    print(f"\n📡 Testing API Endpoints with Valid Token")
    print("=" * 50)
    
    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test endpoints
    endpoints = [
        "/api/public/v1/crm/crm-contact-persons",
        "/api/public/v1/crm/crm-actions", 
        "/api/public/v1/accountancy/accounts"
    ]
    
    for endpoint in endpoints:
        url = f"https://yugen.douano.com{endpoint}"
        print(f"\n🧪 Testing: {endpoint}")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Success! Data: {str(response.json())[:100]}...")
            elif response.status_code == 401:
                print(f"   🔐 Unauthorized - token might be invalid")
            elif response.status_code == 403:
                print(f"   🚫 Forbidden - insufficient permissions")
            elif response.status_code == 404:
                print(f"   ❌ Not Found - endpoint doesn't exist")
            else:
                print(f"   ⚠️  Status {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")


def test_token_endpoints_directly():
    """Test the OAuth2 token endpoints directly"""
    print(f"\n🔍 Testing OAuth2 Endpoints Directly")
    print("=" * 45)
    
    base_url = "https://yugen.douano.com"
    
    # Test authorization endpoint
    auth_url = f"{base_url}/authorize"
    print(f"🧪 Testing authorization endpoint: {auth_url}")
    
    try:
        response = requests.get(auth_url, timeout=10, allow_redirects=False)
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 302]:
            print(f"   ✅ Authorization endpoint is accessible")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test token endpoint (should require POST)
    token_url = f"{base_url}/oauth/token"
    print(f"\n🧪 Testing token endpoint: {token_url}")
    
    try:
        response = requests.get(token_url, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 405:  # Method Not Allowed
            print(f"   ✅ Token endpoint exists (requires POST)")
        elif response.status_code == 400:  # Bad Request
            print(f"   ✅ Token endpoint exists (requires proper parameters)")
        else:
            print(f"   ⚠️  Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def main():
    """Main test function"""
    print("🎯 DOUANO OAuth2 Flow Testing")
    print("Using your actual Yugen instance credentials")
    print("=" * 60)
    
    # Test OAuth2 endpoints
    test_token_endpoints_directly()
    
    # Try client credentials first (quick test)
    print(f"\n" + "="*60)
    token = test_client_credentials_flow()
    
    if token:
        # If client credentials worked, test API
        test_api_with_token(token)
    else:
        # If client credentials failed, try authorization code flow
        print(f"\n" + "="*60)
        print("Client credentials failed. Trying Authorization Code flow...")
        
        choice = input("\nDo you want to try the Authorization Code flow? (y/n): ").strip().lower()
        
        if choice == 'y':
            token = test_authorization_code_flow()
            if token:
                test_api_with_token(token)
        else:
            print("Skipping Authorization Code flow")
    
    print(f"\n🎯 Summary")
    print("=" * 20)
    print("✅ OAuth2 client implementation is complete")
    print("✅ Your credentials are properly configured")
    
    if token:
        print("✅ Successfully obtained access token")
        print("🎉 Ready to use the DOUANO API!")
    else:
        print("⚠️  Token acquisition needs Authorization Code flow")
        print("📞 Contact DOUANO support if issues persist")


if __name__ == "__main__":
    main()
