"""
Netlify Python Function for WhatsApp Webhook
Receives and processes WhatsApp messages from Twilio
"""
import json
import os
from urllib.parse import parse_qs

# WhatsApp webhook handler
def handler(event, context):
    """Handle incoming WhatsApp webhook from Twilio"""
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/xml'
    }
    
    # Handle preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Only accept POST requests
    if event.get('httpMethod') != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # Parse form data from Twilio
        body = event.get('body', '')
        if event.get('isBase64Encoded'):
            import base64
            body = base64.b64decode(body).decode('utf-8')
        
        # Parse form data
        form_data = parse_qs(body)
        message_data = {key: values[0] if values else '' for key, values in form_data.items()}
        
        # Log the incoming message
        print(f"Received WhatsApp message from: {message_data.get('From', 'unknown')}")
        print(f"Message body: {message_data.get('Body', '')}")
        print(f"Media count: {message_data.get('NumMedia', '0')}")
        
        # Process the message asynchronously
        # For Netlify functions, we need to respond immediately to Twilio
        # and process the message in the background
        
        # Import and use the WhatsApp service
        try:
            # Store in Supabase for processing
            from whatsapp_service import WhatsAppService
            service = WhatsAppService()
            result = service.process_incoming_message(message_data)
            print(f"Message processed: {result}")
        except Exception as process_error:
            # Log but don't fail the webhook
            print(f"Error processing message: {process_error}")
            # Still return success to Twilio
        
        # Return TwiML response (empty is fine)
        twiml_response = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': twiml_response
        }
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        # Still return 200 to Twilio to avoid retries
        return {
            'statusCode': 200,
            'headers': headers,
            'body': '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
        }

