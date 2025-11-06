"""
Quick test to verify Twilio credentials
"""
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')

print(f"Testing with Account SID: {account_sid}")
print(f"Auth Token exists: {bool(auth_token)}")
print(f"Auth Token length: {len(auth_token) if auth_token else 0}")

try:
    # Try to initialize Twilio client
    client = Client(account_sid, auth_token)
    
    # Try to fetch account info
    account = client.api.accounts(account_sid).fetch()
    
    print(f"\n✅ SUCCESS! Credentials are valid!")
    print(f"Account Status: {account.status}")
    print(f"Account Name: {account.friendly_name}")
    
    # Try to list recent messages
    messages = client.messages.list(limit=1)
    print(f"\n✅ Can access messages! Found {len(messages)} message(s)")
    
except Exception as e:
    print(f"\n❌ FAILED! Error: {str(e)}")
    print("\nPlease verify:")
    print("1. Account SID is correct")
    print("2. Auth Token is correct and not expired")
    print("3. Credentials are from the same Twilio account")

