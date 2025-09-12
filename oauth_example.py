"""
OAuth2 Authentication Examples for DUANO API

This file demonstrates different OAuth2 flows for authenticating with the DUANO API.
"""

import os
import webbrowser
from urllib.parse import urlparse, parse_qs
from duano_client import create_client, DuanoClient


def client_credentials_example():
    """
    Example using Client Credentials flow (server-to-server authentication)
    This is the most common flow for API integrations
    """
    print("=== Client Credentials Flow Example ===")
    
    # Create client with your credentials
    client = create_client(
        client_id="3",  # Your client ID from the screenshot
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",  # Your client secret
        debug=True
    )
    
    try:
        # The client will automatically perform client credentials flow when making first request
        print("🔐 Authenticating with client credentials...")
        token = client.client_credentials_flow()
        
        print(f"✅ Authentication successful!")
        print(f"Access Token: {token.access_token[:20]}...")
        print(f"Token Type: {token.token_type}")
        print(f"Expires In: {token.expires_in} seconds")
        
        # Now you can make API calls
        print("\n📊 Testing API call...")
        # This will automatically use the token we just obtained
        response = client.get('/api/v1/user')  # Adjust endpoint as needed
        print(f"API Response: {response.data}")
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")


def authorization_code_example():
    """
    Example using Authorization Code flow (user authentication)
    This requires user interaction through a web browser
    """
    print("\n=== Authorization Code Flow Example ===")
    
    client = create_client(
        client_id="3",
        client_secret="KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC",
        redirect_uri="http://localhost:5001/oauth/callback"
    )
    
    try:
        # Step 1: Get authorization URL
        auth_url = client.get_authorization_url(
            scope="read write",  # Adjust scopes as needed
            state="random_state_string"  # For security
        )
        
        print(f"🌐 Please visit this URL to authorize the application:")
        print(auth_url)
        print("\nOpening in browser...")
        
        # Open browser (optional)
        webbrowser.open(auth_url)
        
        # Step 2: User would be redirected to redirect_uri with authorization code
        # For this example, we'll simulate getting the code
        print("\n⏳ After authorization, you'll be redirected to:")
        print("http://localhost:5001/oauth/callback?code=AUTHORIZATION_CODE&state=random_state_string")
        
        # In a real application, you'd extract the code from the callback
        auth_code = input("\n📝 Please enter the authorization code from the callback URL: ")
        
        if auth_code.strip():
            # Step 3: Exchange code for token
            print("🔄 Exchanging authorization code for access token...")
            token = client.exchange_code_for_token(auth_code.strip())
            
            print(f"✅ Authorization successful!")
            print(f"Access Token: {token.access_token[:20]}...")
            print(f"Refresh Token: {token.refresh_token[:20] if token.refresh_token else 'None'}...")
            
            # Now you can make API calls
            print("\n📊 Testing API call...")
            response = client.get('/api/v1/user')
            print(f"API Response: {response.data}")
        else:
            print("❌ No authorization code provided")
            
    except Exception as e:
        print(f"❌ Authorization failed: {e}")


def token_refresh_example():
    """
    Example of refreshing an access token
    """
    print("\n=== Token Refresh Example ===")
    
    client = create_client()
    
    # Simulate having an expired token with refresh token
    from duano_client import OAuthToken
    from datetime import datetime, timedelta
    
    # Create an expired token
    expired_token = OAuthToken(
        access_token="expired_token",
        expires_in=3600,
        refresh_token="your_refresh_token_here",
        created_at=datetime.now() - timedelta(hours=2)  # 2 hours ago
    )
    
    client.current_token = expired_token
    
    try:
        print("🔄 Token is expired, attempting refresh...")
        print(f"Token expired: {expired_token.is_expired}")
        
        # This would normally refresh automatically when making a request
        if expired_token.refresh_token:
            new_token = client.refresh_access_token()
            print(f"✅ Token refreshed successfully!")
            print(f"New Access Token: {new_token.access_token[:20]}...")
        else:
            print("❌ No refresh token available")
            
    except Exception as e:
        print(f"❌ Token refresh failed: {e}")


def manual_token_example():
    """
    Example of setting a token manually (if you already have one)
    """
    print("\n=== Manual Token Example ===")
    
    client = create_client()
    
    # If you already have an access token, you can set it directly
    access_token = input("📝 Enter your access token (or press Enter to skip): ")
    
    if access_token.strip():
        client.set_access_token(access_token.strip())
        print("✅ Token set manually")
        
        try:
            # Test the token
            print("🧪 Testing token...")
            response = client.get('/api/v1/user')
            print(f"✅ Token is valid! Response: {response.data}")
        except Exception as e:
            print(f"❌ Token test failed: {e}")
    else:
        print("⏭️ Skipping manual token example")


def complete_workflow_example():
    """
    Complete workflow example showing how to use the client in a real application
    """
    print("\n=== Complete Workflow Example ===")
    
    client = create_client()
    
    try:
        # The client will automatically handle authentication
        print("🚀 Starting complete workflow...")
        
        # Test connection (this will trigger authentication)
        if client.test_connection():
            print("✅ Connected to DUANO API")
            
            # Now you can use all the modules
            print("\n📊 Getting sales summary...")
            # Note: These endpoints are examples - adjust based on actual DUANO API
            try:
                sales = client.sales.get_sales_summary()
                print(f"Sales data: {sales}")
            except Exception as e:
                print(f"Sales endpoint not available: {e}")
            
            print("\n📦 Getting orders...")
            try:
                orders = client.orders.list_orders(limit=5)
                print(f"Orders: {orders}")
            except Exception as e:
                print(f"Orders endpoint not available: {e}")
            
            print("\n👥 Getting clients...")
            try:
                clients = client.clients.list_clients(limit=5)
                print(f"Clients: {clients}")
            except Exception as e:
                print(f"Clients endpoint not available: {e}")
            
        else:
            print("❌ Failed to connect to DUANO API")
            
    except Exception as e:
        print(f"❌ Workflow failed: {e}")


def main():
    """Run OAuth2 examples"""
    print("🔐 DUANO API OAuth2 Authentication Examples")
    print("=" * 60)
    
    print("\nAvailable examples:")
    print("1. Client Credentials Flow (Recommended for server-to-server)")
    print("2. Authorization Code Flow (For user authentication)")
    print("3. Token Refresh Example")
    print("4. Manual Token Example")
    print("5. Complete Workflow Example")
    print("6. Run all examples")
    
    choice = input("\nSelect example (1-6): ").strip()
    
    if choice == "1":
        client_credentials_example()
    elif choice == "2":
        authorization_code_example()
    elif choice == "3":
        token_refresh_example()
    elif choice == "4":
        manual_token_example()
    elif choice == "5":
        complete_workflow_example()
    elif choice == "6":
        client_credentials_example()
        authorization_code_example()
        token_refresh_example()
        manual_token_example()
        complete_workflow_example()
    else:
        print("❌ Invalid choice")
        return
    
    print("\n🎉 OAuth2 examples completed!")


if __name__ == "__main__":
    main()
