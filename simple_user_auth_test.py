"""
Simple test using the user authentication flow we just completed
This will do a quick user login and test the working endpoints
"""

import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import requests
import json
from duano_client import create_client


class SimpleCallbackHandler(BaseHTTPRequestHandler):
    """Simple callback handler"""
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h1>Success! You can close this window.</h1>")
        
        self.server.callback_received = True
    
    def log_message(self, format, *args):
        pass


def quick_user_auth():
    """Quick user authentication"""
    print("🔐 Quick User Authentication")
    print("=" * 30)
    
    # Start server
    server = HTTPServer(('localhost', 5001), SimpleCallbackHandler)
    server.auth_code = None
    server.callback_received = False
    
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Create auth URL
    params = {
        'response_type': 'code',
        'client_id': '3',
        'redirect_uri': 'http://localhost:5001/oauth/callback',
        'scope': 'read write'
    }
    
    auth_url = f"https://yugen.douano.com/authorize?" + urllib.parse.urlencode(params)
    
    print(f"🌐 Opening browser for login...")
    print(f"   If browser doesn't open: {auth_url}")
    
    webbrowser.open(auth_url)
    
    # Wait for callback
    print("⏳ Waiting for login...")
    start_time = time.time()
    while not server.callback_received and (time.time() - start_time) < 60:
        time.sleep(1)
    
    server.shutdown()
    
    if not server.auth_code:
        print("❌ No authorization code received")
        return None
    
    print(f"✅ Got authorization code: {server.auth_code[:30]}...")
    
    # Exchange for token
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': '3',
        'client_secret': 'KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC',
        'code': server.auth_code,
        'redirect_uri': 'http://localhost:5001/oauth/callback'
    }
    
    print("🔄 Exchanging code for token...")
    
    response = requests.post(
        'https://yugen.douano.com/oauth/token',
        data=token_data,
        timeout=30
    )
    
    if response.status_code == 200:
        token_info = response.json()
        access_token = token_info['access_token']
        print(f"✅ Got access token: {access_token[:30]}...")
        return access_token
    else:
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def test_with_user_token(access_token):
    """Test API endpoints with user token"""
    print(f"\n🧪 Testing with User Token")
    print("=" * 30)
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test the endpoints that worked before
    test_endpoints = [
        "/api/public/v1/core/company-categories",
        "/api/public/v1/crm/crm-contact-persons"
    ]
    
    for endpoint in test_endpoints:
        print(f"\n🔍 Testing: {endpoint}")
        
        try:
            response = requests.get(
                f"https://yugen.douano.com{endpoint}",
                headers=headers,
                timeout=15
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   🎉 SUCCESS!")
                
                try:
                    data = response.json()
                    print(f"   📊 Data structure: {type(data)}")
                    
                    if isinstance(data, dict):
                        print(f"   📊 Keys: {list(data.keys())}")
                        
                        # Show sample data
                        if 'result' in data and 'data' in data['result']:
                            items = data['result']['data']
                            total = data['result'].get('total', len(items))
                            print(f"   📊 Total items: {total}")
                            
                            if items:
                                print(f"   📋 Sample item:")
                                print(f"      {json.dumps(items[0], indent=6)}")
                                
                                # Show specific info based on endpoint
                                if 'company-categories' in endpoint:
                                    print(f"   🏢 Company Categories:")
                                    for cat in items[:5]:
                                        print(f"      • {cat.get('name', 'N/A')} (ID: {cat.get('id')})")
                                
                                elif 'crm-contact-persons' in endpoint:
                                    print(f"   👥 Contact Persons:")
                                    for contact in items[:3]:
                                        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                                        print(f"      • {name or 'No name'} - {contact.get('email', 'No email')}")
                        else:
                            print(f"   📄 Raw data: {str(data)[:300]}...")
                    
                except json.JSONDecodeError as e:
                    print(f"   📄 Non-JSON response: {response.text[:200]}...")
                    
            else:
                print(f"   ❌ Status: {response.status_code}")
                print(f"   📄 Error: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")


def main():
    """Main function"""
    print("🎯 Simple User Authentication Test")
    print("Testing the DOUANO API with user login tokens")
    print("=" * 50)
    
    # Get user token
    access_token = quick_user_auth()
    
    if not access_token:
        print("❌ Failed to get user token")
        return
    
    # Test with user token
    test_with_user_token(access_token)
    
    print(f"\n🎉 SUMMARY")
    print("=" * 20)
    print("✅ User authentication flow works")
    print("✅ Can obtain user access tokens")
    print("🔍 API endpoints should work with user tokens")
    print("💡 The key is using Authorization Code flow instead of Client Credentials")


if __name__ == "__main__":
    main()
