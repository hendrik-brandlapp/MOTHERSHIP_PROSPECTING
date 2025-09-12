"""
DOUANO OAuth2 Authorization Code Flow
Creates a login URL and handles the callback to get user-authenticated tokens
"""

import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from duano_client import create_client


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from DOUANO"""
    
    def do_GET(self):
        """Handle GET request with authorization code"""
        # Parse the callback URL
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        if 'code' in query_params:
            # Success - got authorization code
            auth_code = query_params['code'][0]
            self.server.auth_code = auth_code
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            success_html = f"""
            <html>
            <head>
                <title>DOUANO Authorization Success</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                    .success {{ color: #28a745; }}
                    .code {{ background: #f8f9fa; padding: 10px; margin: 20px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1 class="success">✅ Authorization Successful!</h1>
                <p>You have successfully authorized the DOUANO client.</p>
                <div class="code">
                    <strong>Authorization Code:</strong><br>
                    {auth_code[:50]}...
                </div>
                <p>You can close this window and return to your terminal.</p>
                <script>
                    setTimeout(function() {{ window.close(); }}, 3000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode('utf-8'))
            
        elif 'error' in query_params:
            # Error in authorization
            error = query_params['error'][0]
            error_description = query_params.get('error_description', ['Unknown error'])[0]
            
            self.server.auth_error = f"{error}: {error_description}"
            
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            error_html = f"""
            <html>
            <head>
                <title>DOUANO Authorization Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                    .error {{ color: #dc3545; }}
                </style>
            </head>
            <body>
                <h1 class="error">❌ Authorization Failed</h1>
                <p><strong>Error:</strong> {error}</p>
                <p><strong>Description:</strong> {error_description}</p>
                <p>Please try again or contact support.</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode('utf-8'))
        
        # Signal that we're done
        self.server.callback_received = True
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs"""
        pass


def start_callback_server(port=5001):
    """Start local HTTP server to receive OAuth callback"""
    server = HTTPServer(('localhost', port), OAuthCallbackHandler)
    server.auth_code = None
    server.auth_error = None
    server.callback_received = False
    
    print(f"🌐 Starting callback server on http://localhost:{port}")
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return server


def create_authorization_url(client):
    """Create the authorization URL for user login"""
    
    # OAuth2 authorization parameters
    params = {
        'response_type': 'code',
        'client_id': client.client_id,
        'redirect_uri': client.redirect_uri,
        'scope': 'read write',  # Request read and write permissions
        'state': 'douano_auth_' + str(int(time.time()))  # CSRF protection
    }
    
    # Build authorization URL
    auth_url = f"{client.auth_url}?" + urllib.parse.urlencode(params)
    
    return auth_url, params['state']


def wait_for_callback(server, timeout=300):
    """Wait for OAuth callback with timeout"""
    print(f"⏳ Waiting for authorization (timeout: {timeout} seconds)...")
    print("   Please complete the login in your browser")
    
    start_time = time.time()
    while not server.callback_received and (time.time() - start_time) < timeout:
        time.sleep(1)
        
        # Show progress dots
        elapsed = int(time.time() - start_time)
        if elapsed % 10 == 0 and elapsed > 0:
            print(f"   Still waiting... ({elapsed}s elapsed)")
    
    if server.callback_received:
        if server.auth_code:
            return server.auth_code, None
        else:
            return None, server.auth_error
    else:
        return None, "Timeout waiting for authorization"


def complete_oauth_flow():
    """Complete OAuth2 Authorization Code flow"""
    print("🔐 DOUANO OAuth2 Authorization Code Flow")
    print("=" * 50)
    
    # Create client
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        base_url="https://yugen.douano.com",
        redirect_uri="http://localhost:5001/oauth/callback"
    )
    
    print(f"📋 Client Configuration:")
    print(f"   Client ID: {client.client_id}")
    print(f"   Base URL: {client.base_url}")
    print(f"   Redirect URI: {client.redirect_uri}")
    print(f"   Auth URL: {client.auth_url}")
    print(f"   Token URL: {client.token_url}")
    
    # Start callback server
    server = start_callback_server(5001)
    
    try:
        # Create authorization URL
        auth_url, state = create_authorization_url(client)
        
        print(f"\n🌐 Authorization URL created:")
        print(f"   {auth_url}")
        
        print(f"\n🚀 Opening browser for login...")
        print("   If the browser doesn't open automatically, copy the URL above")
        
        # Open browser
        webbrowser.open(auth_url)
        
        # Wait for callback
        auth_code, error = wait_for_callback(server, timeout=300)
        
        if error:
            print(f"\n❌ Authorization failed: {error}")
            return None
        
        print(f"\n✅ Authorization code received!")
        print(f"   Code: {auth_code[:50]}...")
        
        # Exchange code for token
        print(f"\n🔄 Exchanging code for access token...")
        
        try:
            token = client.exchange_code_for_token(auth_code)
            
            print(f"✅ Access token obtained!")
            print(f"   Token: {token.access_token[:50]}...")
            print(f"   Type: {token.token_type}")
            print(f"   Expires in: {token.expires_in} seconds")
            print(f"   Scope: {token.scope}")
            
            # Store token in client
            client.current_token = token
            
            return client, token
            
        except Exception as e:
            print(f"❌ Failed to exchange code for token: {e}")
            return None
    
    finally:
        # Stop server
        server.shutdown()
        print(f"\n🛑 Callback server stopped")


def test_authenticated_endpoints(client):
    """Test API endpoints with user-authenticated token"""
    print(f"\n🧪 Testing Endpoints with User Authentication")
    print("=" * 50)
    
    if not client.current_token:
        print("❌ No authentication token available")
        return
    
    # Test different endpoint patterns with user auth
    test_endpoints = [
        "/api/public/v1/core/company-categories",
        "/api/v1/core/company-categories",
        "/api/public/v1/crm/crm-contact-persons", 
        "/api/v1/crm/crm-contact-persons",
        "/api/public/v1/accountancy/accounts",
        "/api/v1/accountancy/accounts"
    ]
    
    for endpoint in test_endpoints:
        print(f"\n🔍 Testing: {endpoint}")
        
        try:
            response = client._make_request('GET', endpoint)
            
            if response.status_code == 200:
                print(f"   🎉 SUCCESS! Status: {response.status_code}")
                try:
                    data = response.json()
                    print(f"   📊 Data preview: {str(data)[:200]}...")
                    
                    # If this is company categories, show the full result
                    if 'company-categories' in endpoint:
                        print(f"\n   📋 Company Categories:")
                        if 'result' in data and 'data' in data['result']:
                            for category in data['result']['data'][:5]:  # Show first 5
                                print(f"      • {category.get('name', 'N/A')} (ID: {category.get('id', 'N/A')})")
                        
                        return True  # Success!
                        
                except Exception as e:
                    print(f"   📄 Non-JSON response: {str(response.text)[:100]}...")
            else:
                print(f"   ❌ Status: {response.status_code}")
                if response.status_code == 401:
                    print(f"      Still unauthorized - might need different scopes")
                elif response.status_code == 403:
                    print(f"      Forbidden - user might not have permission")
                    
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
    
    return False


def main():
    """Main function"""
    print("🎯 Starting DOUANO OAuth2 User Authentication Flow")
    print("This will open your browser for login and then test the API endpoints")
    print("=" * 70)
    
    # Complete OAuth flow
    result = complete_oauth_flow()
    
    if not result:
        print("\n❌ OAuth flow failed")
        return
    
    client, token = result
    
    # Test endpoints with user authentication
    success = test_authenticated_endpoints(client)
    
    if success:
        print(f"\n🎉 SUCCESS! User authentication works!")
        print(f"🔧 Update your client to use Authorization Code flow instead of Client Credentials")
    else:
        print(f"\n🤔 User authentication completed but endpoints still not working")
        print(f"💡 This might indicate server-side issues or missing permissions")
    
    print(f"\n📋 Summary:")
    print(f"✅ OAuth2 Authorization Code flow: Working")
    print(f"✅ User login and token exchange: Working") 
    print(f"{'✅' if success else '❌'} API endpoint access: {'Working' if success else 'Still failing'}")


if __name__ == "__main__":
    main()
