"""
WhatsApp Service for handling messages, transcriptions, and AI analysis
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, Optional, List, Any
from openai import OpenAI
from supabase import create_client, Client

class WhatsAppService:
    def __init__(self):
        """Initialize WhatsApp service with OpenAI and Supabase clients"""
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def process_incoming_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming WhatsApp message
        
        Args:
            message_data: Dictionary containing message information from Twilio
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Extract message details
            message_sid = message_data.get('MessageSid')
            from_number = message_data.get('From', '').replace('whatsapp:', '')
            to_number = message_data.get('To', '').replace('whatsapp:', '')
            message_body = message_data.get('Body', '')
            num_media = int(message_data.get('NumMedia', 0))
            
            # Determine message type
            message_type = 'text'
            media_url = None
            media_content_type = None
            
            if num_media > 0:
                media_url = message_data.get('MediaUrl0')
                media_content_type = message_data.get('MediaContentType0', '')
                
                if 'audio' in media_content_type:
                    message_type = 'audio'
                elif 'image' in media_content_type:
                    message_type = 'image'
                elif 'video' in media_content_type:
                    message_type = 'video'
                else:
                    message_type = 'document'
            
            # Store message in database
            message_record = {
                'message_sid': message_sid,
                'from_number': from_number,
                'to_number': to_number,
                'message_body': message_body,
                'message_type': message_type,
                'media_url': media_url,
                'media_content_type': media_content_type,
                'num_media': num_media,
                'direction': 'inbound',
                'status': 'received',
                'received_at': datetime.utcnow().isoformat(),
                'processed': False
            }
            
            result = self.supabase.table('whatsapp_messages').insert(message_record).execute()
            message_id = result.data[0]['id'] if result.data else None
            
            # Process based on message type
            if message_type == 'audio' and media_url:
                # Transcribe audio asynchronously
                self._transcribe_audio(message_id, media_url)
            elif message_type == 'text' and message_body:
                # Analyze text message
                self._analyze_text_message(message_id, message_body)
            
            return {
                'success': True,
                'message_id': message_id,
                'message_type': message_type
            }
            
        except Exception as e:
            print(f"Error processing incoming message: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _transcribe_audio(self, message_id: str, media_url: str) -> Optional[str]:
        """
        Transcribe audio message using OpenAI Whisper
        
        Args:
            message_id: Database ID of the message
            media_url: URL of the audio file
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            from twilio.rest import Client
            
            # Update status to processing
            self.supabase.table('whatsapp_messages').update({
                'transcription_status': 'processing'
            }).eq('id', message_id).execute()
            
            # Get Twilio credentials
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            
            # Debug logging
            print(f"DEBUG: TWILIO_ACCOUNT_SID exists: {bool(account_sid)}")
            print(f"DEBUG: TWILIO_AUTH_TOKEN exists: {bool(auth_token)}")
            
            if not account_sid or not auth_token:
                raise Exception(f"Twilio credentials not configured - SID: {bool(account_sid)}, Token: {bool(auth_token)}")
            
            # Use Twilio SDK to fetch media properly
            print(f"DEBUG: Using Twilio SDK to fetch media from: {media_url}")
            
            # Initialize Twilio client
            twilio_client = Client(account_sid, auth_token)
            
            # Extract message SID and media SID from URL
            # URL format: https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages/{MessageSid}/Media/{MediaSid}
            url_parts = media_url.split('/')
            message_sid = url_parts[-3] if len(url_parts) >= 3 else None
            media_sid = url_parts[-1] if len(url_parts) >= 1 else None
            
            print(f"DEBUG: Message SID: {message_sid}, Media SID: {media_sid}")
            
            if not message_sid or not media_sid:
                raise Exception(f"Could not extract SIDs from media URL: {media_url}")
            
            # Fetch media metadata using Twilio SDK
            media = twilio_client.messages(message_sid).media(media_sid).fetch()
            
            print(f"DEBUG: Media fetched - Content Type: {media.content_type}")
            
            # Build authenticated download URL using Twilio's format
            # The SDK gives us the URI, we need to download the actual content
            download_url = f"https://api.twilio.com{media.uri.replace('.json', '')}"
            
            print(f"DEBUG: Downloading from: {download_url}")
            
            # Use the Twilio client's HTTP client for authenticated requests
            # This uses the same auth session as the SDK
            import base64
            auth_string = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
            
            response = requests.get(
                download_url,
                headers={
                    'Authorization': f'Basic {auth_string}',
                    'User-Agent': 'python-requests'
                },
                timeout=30
            )
            
            print(f"DEBUG: Download response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"DEBUG: Response headers: {response.headers}")
                print(f"DEBUG: Response text: {response.text[:500]}")
                raise Exception(f"Failed to download audio: {response.status_code} - {response.text}")
            
            # Detect file extension from content type or URL
            content_type = response.headers.get('Content-Type', '')
            if 'ogg' in content_type or 'ogg' in media_url:
                extension = 'ogg'
            elif 'mp3' in content_type or 'mp3' in media_url:
                extension = 'mp3'
            elif 'mp4' in content_type or 'mp4' in media_url:
                extension = 'mp4'
            elif 'mpeg' in content_type or 'mpeg' in media_url:
                extension = 'mpeg'
            else:
                extension = 'ogg'  # Default for WhatsApp
            
            # Save temporarily
            temp_file = f"/tmp/{message_id}.{extension}"
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            print(f"Audio file downloaded: {len(response.content)} bytes, type: {content_type}")
            
            # Transcribe using OpenAI (use newer model for better quality)
            with open(temp_file, 'rb') as audio_file:
                transcription = self.openai_client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",  # Updated to newer model
                    file=audio_file,
                    response_format="text"
                )
            
            # Handle both string and object responses
            if hasattr(transcription, 'text'):
                transcription_text = transcription.text
            else:
                transcription_text = str(transcription)
            
            # Update message with transcription
            self.supabase.table('whatsapp_messages').update({
                'transcription': transcription_text,
                'transcription_status': 'completed',
                'message_body': transcription_text  # Also set as message body for processing
            }).eq('id', message_id).execute()
            
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            # Now analyze the transcribed text
            self._analyze_text_message(message_id, transcription_text)
            
            return transcription_text
            
        except Exception as e:
            print(f"Error transcribing audio: {str(e)}")
            self.supabase.table('whatsapp_messages').update({
                'transcription_status': 'failed',
                'processing_error': str(e)
            }).eq('id', message_id).execute()
            return None
    
    def _analyze_text_message(self, message_id: str, text: str) -> Dict[str, Any]:
        """
        Analyze text message using OpenAI and extract task information
        
        Args:
            message_id: Database ID of the message
            text: Text to analyze
            
        Returns:
            Analysis results
        """
        try:
            # Create AI analysis prompt
            analysis_prompt = f"""
Analyze the following message and extract:
1. A brief summary (1-2 sentences)
2. Sentiment (positive, negative, neutral, or urgent)
3. Whether this message requires creating a task (yes/no)
4. If a task should be created, extract:
   - Task title
   - Task description
   - Task priority (1-5, where 1 is highest)
   - Task type (call, email, meeting, follow_up, demo, proposal, contract, support, research, general)
   - Due date (if mentioned, otherwise suggest "today" or "tomorrow")
5. Any entities mentioned (person names, company names, dates, amounts, etc.)

Message: "{text}"

Respond in JSON format:
{{
    "summary": "brief summary",
    "sentiment": "positive|negative|neutral|urgent",
    "requires_task": true|false,
    "task_info": {{
        "title": "task title",
        "description": "detailed description",
        "priority": 1-5,
        "task_type": "type",
        "suggested_due_date": "today|tomorrow|specific date",
        "notes": "additional notes"
    }},
    "entities": {{
        "people": [],
        "companies": [],
        "dates": [],
        "amounts": []
    }}
}}
"""
            
            # Call OpenAI API for analysis
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that analyzes messages and extracts actionable information. Always respond with valid JSON."},
                    {"role": "user", "content": analysis_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            
            # Update message with analysis
            self.supabase.table('whatsapp_messages').update({
                'ai_analysis': analysis_result,
                'ai_summary': analysis_result.get('summary'),
                'ai_sentiment': analysis_result.get('sentiment'),
                'extracted_entities': analysis_result.get('entities', {}),
                'processed': True,
                'processed_at': datetime.utcnow().isoformat()
            }).eq('id', message_id).execute()
            
            # Create task if needed
            if analysis_result.get('requires_task') and analysis_result.get('task_info'):
                self._create_task_from_message(message_id, analysis_result['task_info'], text)
            else:
                self.supabase.table('whatsapp_messages').update({
                    'task_creation_status': 'not_applicable'
                }).eq('id', message_id).execute()
            
            return analysis_result
            
        except Exception as e:
            print(f"Error analyzing message: {str(e)}")
            self.supabase.table('whatsapp_messages').update({
                'processing_error': str(e),
                'processed': True,
                'processed_at': datetime.utcnow().isoformat()
            }).eq('id', message_id).execute()
            return {}
    
    def _create_task_from_message(self, message_id: str, task_info: Dict[str, Any], original_message: str):
        """
        Create a task in the database from message analysis
        
        Args:
            message_id: ID of the message
            task_info: Extracted task information
            original_message: Original message text
        """
        try:
            # Update status
            self.supabase.table('whatsapp_messages').update({
                'task_creation_status': 'processing'
            }).eq('id', message_id).execute()
            
            # Get message details to link prospect if possible
            message = self.supabase.table('whatsapp_messages').select('*').eq('id', message_id).execute()
            
            if not message.data:
                raise Exception("Message not found")
            
            message_data = message.data[0]
            prospect_id = message_data.get('prospect_id')
            
            # Determine due date
            suggested_due = task_info.get('suggested_due_date', 'today')
            if suggested_due == 'today':
                due_date = datetime.utcnow().date().isoformat()
            elif suggested_due == 'tomorrow':
                from datetime import timedelta
                due_date = (datetime.utcnow().date() + timedelta(days=1)).isoformat()
            else:
                due_date = suggested_due
            
            # Create task
            task_data = {
                'title': task_info.get('title', 'Task from WhatsApp'),
                'description': task_info.get('description', original_message),
                'task_type': task_info.get('task_type', 'general'),
                'category': 'follow_up',
                'priority': task_info.get('priority', 3),
                'status': 'pending',
                'due_date': due_date,
                'prospect_id': prospect_id,
                'notes': f"Created from WhatsApp message.\n\nOriginal message: {original_message}\n\n{task_info.get('notes', '')}",
                'tags': json.dumps(['whatsapp', 'auto-generated']),
                'created_by': 'WhatsApp AI Agent'
            }
            
            result = self.supabase.table('sales_tasks').insert(task_data).execute()
            
            if result.data:
                task_id = result.data[0]['id']
                
                # Update message with created task
                self.supabase.table('whatsapp_messages').update({
                    'task_created': True,
                    'created_task_id': task_id,
                    'task_creation_status': 'created'
                }).eq('id', message_id).execute()
                
                print(f"Task created successfully: {task_id}")
                return task_id
            
        except Exception as e:
            print(f"Error creating task: {str(e)}")
            self.supabase.table('whatsapp_messages').update({
                'task_creation_status': 'failed',
                'processing_error': str(e)
            }).eq('id', message_id).execute()
            return None
    
    def get_inbox_messages(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get inbox messages with pagination
        
        Args:
            limit: Number of messages to retrieve
            offset: Offset for pagination
            
        Returns:
            List of messages
        """
        try:
            result = self.supabase.table('whatsapp_messages')\
                .select('*')\
                .order('received_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching inbox messages: {str(e)}")
            return []
    
    def get_conversation_history(self, phone_number: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a specific phone number
        
        Args:
            phone_number: Phone number to get conversation for
            
        Returns:
            List of messages in chronological order
        """
        try:
            result = self.supabase.table('whatsapp_messages')\
                .select('*')\
                .or_(f'from_number.eq.{phone_number},to_number.eq.{phone_number}')\
                .order('received_at', desc=False)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching conversation history: {str(e)}")
            return []
    
    def mark_as_read(self, phone_number: str):
        """
        Mark all messages from a phone number as read
        
        Args:
            phone_number: Phone number to mark as read
        """
        try:
            self.supabase.rpc('mark_conversation_as_read', {
                'p_phone_number': phone_number
            }).execute()
        except Exception as e:
            print(f"Error marking messages as read: {str(e)}")
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Get WhatsApp analytics
        
        Returns:
            Dictionary with analytics data
        """
        try:
            result = self.supabase.table('whatsapp_analytics').select('*').execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            print(f"Error fetching analytics: {str(e)}")
            return {}
    
    def send_message(self, to_number: str, message: str) -> bool:
        """
        Send a WhatsApp message (requires Twilio configuration)
        
        Args:
            to_number: Recipient phone number
            message: Message text
            
        Returns:
            True if successful
        """
        try:
            from twilio.rest import Client
            
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
            
            if not all([account_sid, auth_token, from_number]):
                raise ValueError("Twilio credentials not configured")
            
            client = Client(account_sid, auth_token)
            
            # Format phone numbers
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            # Send message
            message = client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            
            # Store outbound message
            self.supabase.table('whatsapp_messages').insert({
                'message_sid': message.sid,
                'from_number': from_number.replace('whatsapp:', ''),
                'to_number': to_number.replace('whatsapp:', ''),
                'message_body': message.body,
                'message_type': 'text',
                'direction': 'outbound',
                'status': 'sent',
                'received_at': datetime.utcnow().isoformat(),
                'processed': True
            }).execute()
            
            return True
            
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            return False

