# WhatsApp Integration with AI Transcription & Task Creation

This document provides a comprehensive guide to the WhatsApp integration feature that enables:
- Receiving WhatsApp messages via Twilio
- AI-powered transcription of voice notes using OpenAI Whisper
- Intelligent message analysis using GPT-4o-mini
- Automatic task creation in the task database
- Beautiful inbox interface for message management

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Setup Instructions](#setup-instructions)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Features](#features)
6. [Configuration](#configuration)
7. [Testing](#testing)

---

## Architecture Overview

### Components

1. **Twilio WhatsApp Integration**
   - Receives incoming WhatsApp messages via webhook
   - Handles text messages, voice notes, images, and other media

2. **WhatsApp Service (`whatsapp_service.py`)**
   - Core business logic for message processing
   - OpenAI Whisper integration for voice transcription
   - GPT-4o-mini for message analysis and task extraction
   - Supabase database operations

3. **Flask API Endpoints (`app.py`)**
   - `/api/whatsapp/webhook` - Receives Twilio webhooks
   - `/api/whatsapp/inbox` - Get inbox messages
   - `/api/whatsapp/conversation/<phone>` - Get conversation history
   - `/api/whatsapp/send` - Send WhatsApp messages
   - `/api/whatsapp/analytics` - Get analytics data

4. **Inbox UI (`templates/whatsapp_inbox.html`)**
   - Beautiful, responsive inbox interface
   - Real-time message display with AI analysis
   - Sentiment badges and task indicators
   - Message detail modal with full information

### Data Flow

```
WhatsApp Message (from user)
    ↓
Twilio WhatsApp API
    ↓
Your Webhook Endpoint (/api/whatsapp/webhook)
    ↓
WhatsAppService.process_incoming_message()
    ↓
[If Voice Note] → OpenAI Whisper Transcription
    ↓
GPT-4o-mini Analysis (extract summary, sentiment, entities)
    ↓
[If Task Needed] → Create Task in sales_tasks table
    ↓
Store in whatsapp_messages table
    ↓
Display in Inbox UI
```

---

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `twilio>=9.0.0` - Twilio SDK for WhatsApp
- `pydub>=0.25.1` - Audio processing (optional, for future enhancements)

### 2. Set Up Twilio WhatsApp

1. **Create a Twilio Account**
   - Go to [twilio.com](https://www.twilio.com)
   - Sign up and verify your account

2. **Set Up WhatsApp Sandbox** (for testing)
   - In Twilio Console, go to Messaging → Try it out → Send a WhatsApp message
   - Follow instructions to connect your WhatsApp to the sandbox
   - Note your sandbox number (e.g., `whatsapp:+14155238886`)

3. **Get Your Credentials**
   - Account SID: Found in Twilio Console dashboard
   - Auth Token: Found in Twilio Console dashboard
   - WhatsApp Number: Your sandbox number or purchased number

4. **Configure Webhook URL**
   - In Twilio Console → Messaging → Settings → WhatsApp Sandbox Settings
   - Set "When a message comes in" webhook to: `https://your-domain.com/api/whatsapp/webhook`
   - Method: `POST`

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key

# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_WEBHOOK_URL=https://your-domain.com/api/whatsapp/webhook

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### 4. Set Up Database

Run the SQL migration in your Supabase SQL editor:

```bash
# Execute the migration
cat create_whatsapp_inbox.sql
```

This creates:
- `whatsapp_messages` table - Stores all messages with AI analysis
- `whatsapp_conversations` table - Conversation threads
- `whatsapp_inbox_view` - Convenient view for inbox display
- Analytics views and functions

### 5. Deploy Your Application

For the webhook to work, your application must be accessible from the internet.

**Option A: Use ngrok for local testing**
```bash
# Install ngrok (if not already installed)
# Download from https://ngrok.com

# Start your Flask app
python app.py

# In another terminal, start ngrok
ngrok http 5002

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update Twilio webhook to: https://abc123.ngrok.io/api/whatsapp/webhook
```

**Option B: Deploy to production**
- Deploy to services like Heroku, Railway, DigitalOcean, etc.
- Update Twilio webhook URL to your production URL

### 6. Test the Integration

1. Send a text message to your Twilio WhatsApp number
2. Send a voice note
3. Check the inbox at `http://localhost:5002/whatsapp-inbox`
4. Verify messages appear with AI analysis and tasks

---

## Database Schema

### whatsapp_messages Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| message_sid | VARCHAR(100) | Twilio message SID (unique) |
| from_number | VARCHAR(50) | Sender phone number |
| to_number | VARCHAR(50) | Recipient phone number |
| message_body | TEXT | Message text content |
| message_type | VARCHAR(20) | Type: text, audio, image, video, document |
| media_url | TEXT | URL of media file (if applicable) |
| transcription | TEXT | AI transcription of voice notes |
| transcription_status | VARCHAR(20) | Status: pending, processing, completed, failed |
| ai_analysis | JSONB | Full AI analysis result |
| ai_summary | TEXT | Brief summary of message |
| ai_sentiment | VARCHAR(20) | Sentiment: positive, negative, neutral, urgent |
| extracted_entities | JSONB | Extracted entities (people, companies, dates) |
| task_created | BOOLEAN | Whether a task was created |
| created_task_id | UUID | FK to sales_tasks |
| direction | VARCHAR(10) | inbound or outbound |
| status | VARCHAR(20) | received, read, replied, archived |
| prospect_id | UUID | FK to prospects (if linked) |
| processed | BOOLEAN | Whether message has been processed |
| received_at | TIMESTAMPTZ | When message was received |
| processed_at | TIMESTAMPTZ | When message was processed |

### whatsapp_conversations Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| phone_number | VARCHAR(50) | Contact phone number (unique) |
| contact_name | VARCHAR(255) | Contact name (if known) |
| prospect_id | UUID | FK to prospects |
| first_message_at | TIMESTAMPTZ | First message timestamp |
| last_message_at | TIMESTAMPTZ | Last message timestamp |
| total_messages | INTEGER | Total message count |
| unread_count | INTEGER | Unread message count |
| conversation_status | VARCHAR(20) | active, archived, blocked |

---

## API Endpoints

### POST /api/whatsapp/webhook
**Receives incoming WhatsApp messages from Twilio**

Twilio automatically sends these parameters:
- `MessageSid` - Unique message identifier
- `From` - Sender (e.g., whatsapp:+1234567890)
- `To` - Recipient (your WhatsApp number)
- `Body` - Message text
- `NumMedia` - Number of media files
- `MediaUrl0` - URL of first media file
- `MediaContentType0` - MIME type of media

Response: TwiML XML (empty response is OK)

### GET /api/whatsapp/inbox
**Get inbox messages with pagination**

Query Parameters:
- `limit` (default: 50) - Number of messages to return
- `offset` (default: 0) - Pagination offset

Response:
```json
{
  "success": true,
  "messages": [...],
  "count": 25
}
```

### GET /api/whatsapp/conversation/<phone_number>
**Get all messages for a specific phone number**

Response:
```json
{
  "success": true,
  "phone_number": "+1234567890",
  "messages": [...],
  "count": 10
}
```

### POST /api/whatsapp/mark-read
**Mark messages from a phone number as read**

Request Body:
```json
{
  "phone_number": "+1234567890"
}
```

### POST /api/whatsapp/send
**Send a WhatsApp message**

Request Body:
```json
{
  "to_number": "+1234567890",
  "message": "Hello! This is a reply from our system."
}
```

### GET /api/whatsapp/analytics
**Get WhatsApp analytics**

Response:
```json
{
  "success": true,
  "analytics": {
    "total_messages": 150,
    "inbound_messages": 95,
    "outbound_messages": 55,
    "voice_messages": 20,
    "tasks_created": 12,
    "transcriptions_completed": 18,
    "unique_contacts": 35,
    "avg_processing_time_seconds": 2.5
  }
}
```

---

## Features

### 1. Voice Note Transcription

- Automatically transcribes voice notes using OpenAI Whisper
- Supports multiple languages (default: English)
- Transcription status tracking (pending → processing → completed)
- Error handling for failed transcriptions

### 2. AI Message Analysis

Uses GPT-4o-mini to analyze messages and extract:

- **Summary**: Brief 1-2 sentence summary
- **Sentiment**: positive, negative, neutral, or urgent
- **Entities**: People, companies, dates, amounts mentioned
- **Task Requirements**: Whether the message requires action

### 3. Automatic Task Creation

When AI determines a task is needed, it automatically creates a task with:
- **Title**: Auto-generated from message content
- **Description**: Detailed description with original message
- **Type**: call, email, meeting, follow_up, demo, proposal, etc.
- **Priority**: 1-5 (based on urgency)
- **Due Date**: Suggested date (today, tomorrow, or specific date)
- **Tags**: Includes 'whatsapp' and 'auto-generated'
- **Link**: References original WhatsApp message

### 4. Beautiful Inbox UI

- **Dashboard Analytics**: Total messages, voice notes, tasks created, unique contacts
- **Message List**: 
  - Sortable and filterable (All, Voice, Text, With Tasks)
  - Shows sender, preview, type badge, sentiment, task status
  - Click to view full details
- **Message Detail Modal**:
  - Full message content
  - Transcription (for voice notes)
  - AI analysis and summary
  - Task information (if created)
  - Extracted entities
- **Real-time Updates**: Refresh button to load latest messages

### 5. Conversation Threading

- Automatically groups messages by phone number
- Tracks conversation metadata (first/last message, total count, unread)
- Maintains conversation status (active, archived, blocked)

---

## Configuration

### Customizing AI Analysis

Edit `whatsapp_service.py`, method `_analyze_text_message()`:

```python
analysis_prompt = f"""
Analyze the following message and extract:
1. A brief summary (1-2 sentences)
2. Sentiment (positive, negative, neutral, or urgent)
3. Whether this message requires creating a task (yes/no)
...
"""
```

Adjust the prompt to:
- Change sentiment categories
- Add custom entity extraction
- Modify task creation criteria
- Support multiple languages

### Customizing Task Creation

Edit `whatsapp_service.py`, method `_create_task_from_message()`:

```python
task_data = {
    'title': task_info.get('title', 'Task from WhatsApp'),
    'description': task_info.get('description', original_message),
    'task_type': task_info.get('task_type', 'general'),
    'category': 'follow_up',  # Change default category
    'priority': task_info.get('priority', 3),
    ...
}
```

### Webhook Security

For production, add webhook validation in `app.py`:

```python
from twilio.request_validator import RequestValidator

@app.route('/api/whatsapp/webhook', methods=['POST'])
def whatsapp_webhook():
    # Validate webhook is from Twilio
    validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))
    
    signature = request.headers.get('X-Twilio-Signature', '')
    url = request.url
    params = request.form.to_dict()
    
    if not validator.validate(url, params, signature):
        return 'Forbidden', 403
    
    # Continue processing...
```

---

## Testing

### 1. Test Voice Note Transcription

1. Send a voice note to your Twilio WhatsApp number
2. Check the database:
```sql
SELECT id, from_number, transcription, transcription_status 
FROM whatsapp_messages 
WHERE message_type = 'audio' 
ORDER BY received_at DESC 
LIMIT 5;
```

### 2. Test AI Analysis

Send a message like:
> "Hi! I need to schedule a meeting with John Smith from ABC Corp next Tuesday to discuss the proposal. This is urgent."

Expected AI analysis should extract:
- **Summary**: Request to schedule urgent meeting
- **Sentiment**: urgent
- **Entities**: 
  - Person: John Smith
  - Company: ABC Corp
  - Date: next Tuesday
- **Task**: Should create a task with type "meeting", priority 1-2

### 3. Test Task Creation

Check if task was created:
```sql
SELECT t.id, t.title, t.task_type, t.priority, t.due_date, m.message_body
FROM sales_tasks t
JOIN whatsapp_messages m ON m.created_task_id = t.id
ORDER BY t.created_at DESC
LIMIT 5;
```

### 4. Test Inbox UI

1. Navigate to: `http://localhost:5002/whatsapp-inbox`
2. Verify:
   - Analytics cards display correctly
   - Messages appear in table
   - Filter buttons work (All, Voice, Text, With Tasks)
   - Message detail modal opens with full information
   - Sentiment badges display correctly

---

## Troubleshooting

### Messages Not Appearing in Inbox

1. **Check webhook configuration**
   ```bash
   # Verify webhook URL in Twilio Console
   # Make sure it's HTTPS and publicly accessible
   ```

2. **Check Flask logs**
   ```bash
   # Look for errors in console
   python app.py
   ```

3. **Verify Twilio webhook is being called**
   - Go to Twilio Console → Monitor → Logs → WhatsApp
   - Check for webhook errors

### Voice Transcription Failing

1. **Check OpenAI API key**
   ```bash
   echo $OPENAI_API_KEY
   ```

2. **Verify audio format**
   - Twilio sends audio in OGG format by default
   - OpenAI Whisper supports many formats

3. **Check database status**
   ```sql
   SELECT message_sid, transcription_status, processing_error
   FROM whatsapp_messages
   WHERE transcription_status = 'failed';
   ```

### Tasks Not Being Created

1. **Check AI analysis results**
   ```sql
   SELECT ai_analysis, task_creation_status
   FROM whatsapp_messages
   WHERE task_creation_status = 'failed';
   ```

2. **Review processing errors**
   ```sql
   SELECT processing_error
   FROM whatsapp_messages
   WHERE processing_error IS NOT NULL;
   ```

### Webhook Timeout Issues

If processing takes too long (>10 seconds), Twilio may timeout:

1. **Move processing to background task**
   - Use Celery or similar task queue
   - Immediately return 200 response to Twilio
   - Process message asynchronously

2. **Example with threading** (quick fix):
   ```python
   import threading
   
   @app.route('/api/whatsapp/webhook', methods=['POST'])
   def whatsapp_webhook():
       message_data = request.form.to_dict()
       
       # Process in background
       thread = threading.Thread(
           target=lambda: whatsapp_service.process_incoming_message(message_data)
       )
       thread.start()
       
       # Immediately respond to Twilio
       return str(MessagingResponse()), 200
   ```

---

## Future Enhancements

### 1. Real-time Updates with WebSockets
- Add Socket.IO for real-time message updates
- Push notifications for new messages

### 2. Two-way Conversations
- Reply directly from inbox UI
- Template messages for common responses
- Auto-reply configuration

### 3. Advanced AI Features
- Multi-language support
- Sentiment trend analysis
- Intent classification
- Custom entity extraction (products, prices, etc.)

### 4. Integration with CRM
- Link messages to prospects automatically
- Update prospect status based on message sentiment
- Create follow-up reminders

### 5. Analytics Dashboard
- Message volume trends
- Response time metrics
- Task completion rates
- Sentiment analysis over time

---

## Security Best Practices

1. **Validate Twilio Webhooks**
   - Use `RequestValidator` to verify requests are from Twilio
   - Check `X-Twilio-Signature` header

2. **Secure API Endpoints**
   - Add authentication to inbox endpoints
   - Use rate limiting to prevent abuse

3. **Protect Sensitive Data**
   - Store phone numbers encrypted
   - Implement data retention policies
   - Comply with GDPR/privacy regulations

4. **Monitor for Abuse**
   - Set up alerts for unusual activity
   - Implement spam detection
   - Block abusive contacts

---

## Support & Resources

### Documentation
- [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp)
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [Supabase Docs](https://supabase.com/docs)

### Community
- GitHub Issues: Report bugs or feature requests
- Discussions: Ask questions and share ideas

### License
This integration is part of the DOUANO project and follows the same license.

---

## Changelog

### Version 1.0.0 (2025-01-XX)
- Initial release
- WhatsApp message receiving via Twilio
- Voice note transcription with OpenAI Whisper
- AI message analysis with GPT-4o-mini
- Automatic task creation
- Inbox UI with analytics
- Message filtering and search
- Conversation threading

---

**Happy messaging! 🎉**

