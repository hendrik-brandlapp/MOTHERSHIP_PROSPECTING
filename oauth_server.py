"""
Simple OAuth2 callback server for testing DUANO API authentication

This server helps handle the OAuth2 callback when testing the authorization code flow.
Run this server, then use the authorization code flow example.
"""

import os
import sys
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
import threading
import time


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth2 callback requests"""
    
    def do_GET(self):
        """Handle GET request for OAuth2 callback"""
        # Parse the URL
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        # Check if this is the OAuth callback
        if parsed_url.path == '/oauth/callback':
            # Extract authorization code and state
            auth_code = query_params.get('code', [None])[0]
            state = query_params.get('state', [None])[0]
            error = query_params.get('error', [None])[0]
            
            if error:
                # Handle error
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                html = f"""
                <html>
                <head><title>OAuth2 Error</title></head>
                <body>
                    <h1>❌ OAuth2 Error</h1>
                    <p><strong>Error:</strong> {error}</p>
                    <p><strong>Description:</strong> {query_params.get('error_description', ['Unknown error'])[0]}</p>
                    <p>You can close this window and try again.</p>
                </body>
                </html>
                """
                self.wfile.write(html.encode())
                
                # Store the error globally
                self.server.oauth_result = {'error': error}
                
            elif auth_code:
                # Success - got authorization code
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                html = f"""
                <html>
                <head><title>OAuth2 Success</title></head>
                <body>
                    <h1>✅ Authorization Successful!</h1>
                    <p><strong>Authorization Code:</strong> <code>{auth_code}</code></p>
                    <p><strong>State:</strong> {state}</p>
                    <p>You can close this window. The authorization code has been captured.</p>
                    <script>
                        // Auto-close after 3 seconds
                        setTimeout(function() {{
                            window.close();
                        }}, 3000);
                    </script>
                </body>
                </html>
                """
                self.wfile.write(html.encode())
                
                # Store the result globally
                self.server.oauth_result = {
                    'code': auth_code,
                    'state': state
                }
                
            else:
                # Missing authorization code
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                html = """
                <html>
                <head><title>OAuth2 Error</title></head>
                <body>
                    <h1>❌ Missing Authorization Code</h1>
                    <p>The OAuth2 callback did not include an authorization code.</p>
                    <p>You can close this window and try again.</p>
                </body>
                </html>
                """
                self.wfile.write(html.encode())
                
                self.server.oauth_result = {'error': 'missing_code'}
        else:
            # Handle other requests
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <html>
            <head><title>OAuth2 Callback Server</title></head>
            <body>
                <h1>🔐 OAuth2 Callback Server</h1>
                <p>This server is running and waiting for OAuth2 callbacks.</p>
                <p>Use the <code>/oauth/callback</code> endpoint for OAuth2 redirects.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        if '/oauth/callback' in format % args:
            print(f"OAuth2 callback received: {format % args}")


class OAuthServer:
    """Simple OAuth2 callback server"""
    
    def __init__(self, host='localhost', port=5001):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        
    def start(self):
        """Start the OAuth2 callback server"""
        try:
            self.server = HTTPServer((self.host, self.port), OAuthCallbackHandler)
            self.server.oauth_result = None
            
            print(f"🚀 OAuth2 callback server starting on http://{self.host}:{self.port}")
            print(f"📋 Callback URL: http://{self.host}:{self.port}/oauth/callback")
            print("⏳ Waiting for OAuth2 callback...")
            
            # Start server in a separate thread
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def stop(self):
        """Stop the OAuth2 callback server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("🛑 OAuth2 callback server stopped")
    
    def wait_for_callback(self, timeout=300):
        """
        Wait for OAuth2 callback
        
        Args:
            timeout: Timeout in seconds (default: 5 minutes)
            
        Returns:
            Dictionary with callback result or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.server and hasattr(self.server, 'oauth_result') and self.server.oauth_result:
                return self.server.oauth_result
            time.sleep(1)
        
        return None


def interactive_oauth_flow():
    """Interactive OAuth2 flow with callback server"""
    print("🔐 Interactive OAuth2 Flow with DUANO API")
    print("=" * 50)
    
    # Start callback server
    server = OAuthServer()
    if not server.start():
        return
    
    try:
        # Import after server starts to avoid import issues
        from duano_client import create_client
        
        # Create client
        client = create_client(
            client_id="3",
            client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
            redirect_uri="http://localhost:5001/oauth/callback"
        )
        
        # Get authorization URL
        auth_url = client.get_authorization_url(
            scope="read write",
            state="secure_random_state"
        )
        
        print(f"\n🌐 Opening authorization URL in browser...")
        print(f"URL: {auth_url}")
        
        # Open browser
        webbrowser.open(auth_url)
        
        # Wait for callback
        print("\n⏳ Waiting for OAuth2 callback (timeout: 5 minutes)...")
        result = server.wait_for_callback(timeout=300)
        
        if result:
            if 'error' in result:
                print(f"❌ OAuth2 error: {result['error']}")
            elif 'code' in result:
                print(f"✅ Authorization code received: {result['code']}")
                
                # Exchange code for token
                try:
                    print("🔄 Exchanging code for access token...")
                    token = client.exchange_code_for_token(result['code'])
                    
                    print(f"🎉 Success! Access token obtained:")
                    print(f"  Token: {token.access_token[:20]}...")
                    print(f"  Type: {token.token_type}")
                    print(f"  Expires in: {token.expires_in} seconds")
                    print(f"  Refresh token: {'Yes' if token.refresh_token else 'No'}")
                    
                    # Test API call
                    print("\n🧪 Testing API call...")
                    try:
                        response = client.test_connection()
                        if response:
                            print("✅ API connection successful!")
                        else:
                            print("❌ API connection failed")
                    except Exception as e:
                        print(f"❌ API test failed: {e}")
                    
                except Exception as e:
                    print(f"❌ Token exchange failed: {e}")
        else:
            print("⏰ Timeout waiting for OAuth2 callback")
    
    finally:
        server.stop()


def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == 'server':
        # Just run the server
        server = OAuthServer()
        if server.start():
            try:
                print("Press Ctrl+C to stop the server")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping server...")
                server.stop()
    else:
        # Run interactive flow
        interactive_oauth_flow()


if __name__ == "__main__":
    main()
