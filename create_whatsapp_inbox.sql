-- WhatsApp Inbox and Messaging System
-- Run this in your Supabase SQL editor

-- Create whatsapp_messages table
CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- Message identification
    message_sid VARCHAR(100) UNIQUE NOT NULL,
    from_number VARCHAR(50) NOT NULL,
    to_number VARCHAR(50) NOT NULL,
    
    -- Message content
    message_body TEXT,
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN (
        'text', 'audio', 'image', 'video', 'document', 'location'
    )),
    
    -- Media handling
    media_url TEXT,
    media_content_type VARCHAR(100),
    num_media INTEGER DEFAULT 0,
    
    -- Audio/Voice transcription
    transcription TEXT,
    transcription_status VARCHAR(20) DEFAULT 'pending' CHECK (transcription_status IN (
        'pending', 'processing', 'completed', 'failed'
    )),
    
    -- AI Analysis
    ai_analysis JSONB,
    ai_summary TEXT,
    ai_sentiment VARCHAR(20),
    extracted_entities JSONB DEFAULT '{}',
    
    -- Task creation
    task_created BOOLEAN DEFAULT false,
    created_task_id UUID REFERENCES sales_tasks(id) ON DELETE SET NULL,
    task_creation_status VARCHAR(20) DEFAULT 'not_attempted' CHECK (task_creation_status IN (
        'not_attempted', 'processing', 'created', 'failed', 'not_applicable'
    )),
    
    -- Message metadata
    direction VARCHAR(10) DEFAULT 'inbound' CHECK (direction IN ('inbound', 'outbound')),
    status VARCHAR(20) DEFAULT 'received' CHECK (status IN (
        'received', 'read', 'replied', 'archived', 'flagged'
    )),
    
    -- Contact information
    contact_name VARCHAR(255),
    prospect_id UUID REFERENCES prospects(id) ON DELETE SET NULL,
    
    -- Processing flags
    processed BOOLEAN DEFAULT false,
    processing_error TEXT,
    
    -- Timestamps
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_from_number ON whatsapp_messages(from_number);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_to_number ON whatsapp_messages(to_number);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_received_at ON whatsapp_messages(received_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_status ON whatsapp_messages(status);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_processed ON whatsapp_messages(processed);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_prospect_id ON whatsapp_messages(prospect_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_message_type ON whatsapp_messages(message_type);

-- Create conversation threads table
CREATE TABLE IF NOT EXISTS whatsapp_conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone_number VARCHAR(50) UNIQUE NOT NULL,
    contact_name VARCHAR(255),
    prospect_id UUID REFERENCES prospects(id) ON DELETE SET NULL,
    
    -- Conversation metadata
    first_message_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ,
    total_messages INTEGER DEFAULT 0,
    unread_count INTEGER DEFAULT 0,
    
    -- Status
    conversation_status VARCHAR(20) DEFAULT 'active' CHECK (conversation_status IN (
        'active', 'archived', 'blocked'
    )),
    
    -- Notes
    notes TEXT,
    tags JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for conversations
CREATE INDEX IF NOT EXISTS idx_whatsapp_conversations_phone_number ON whatsapp_conversations(phone_number);
CREATE INDEX IF NOT EXISTS idx_whatsapp_conversations_last_message_at ON whatsapp_conversations(last_message_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_conversations_status ON whatsapp_conversations(conversation_status);

-- Enable Row Level Security
ALTER TABLE whatsapp_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_conversations ENABLE ROW LEVEL SECURITY;

-- Create policies (allowing all operations for demo - customize for production)
CREATE POLICY "Enable all operations for anon users on whatsapp_messages" 
    ON whatsapp_messages FOR ALL USING (true);
CREATE POLICY "Enable all operations for anon users on whatsapp_conversations" 
    ON whatsapp_conversations FOR ALL USING (true);

-- Create trigger for updated_at
DROP TRIGGER IF EXISTS update_whatsapp_messages_updated_at ON whatsapp_messages;
CREATE TRIGGER update_whatsapp_messages_updated_at
    BEFORE UPDATE ON whatsapp_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_whatsapp_conversations_updated_at ON whatsapp_conversations;
CREATE TRIGGER update_whatsapp_conversations_updated_at
    BEFORE UPDATE ON whatsapp_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for inbox with conversation summaries
CREATE OR REPLACE VIEW whatsapp_inbox_view AS
SELECT 
    c.id as conversation_id,
    c.phone_number,
    c.contact_name,
    c.prospect_id,
    p.name as prospect_name,
    c.last_message_at,
    c.total_messages,
    c.unread_count,
    c.conversation_status,
    c.tags,
    -- Get the latest message
    (
        SELECT json_build_object(
            'id', m.id,
            'body', m.message_body,
            'type', m.message_type,
            'direction', m.direction,
            'received_at', m.received_at,
            'transcription', m.transcription,
            'ai_summary', m.ai_summary
        )
        FROM whatsapp_messages m
        WHERE m.from_number = c.phone_number OR m.to_number = c.phone_number
        ORDER BY m.received_at DESC
        LIMIT 1
    ) as latest_message
FROM whatsapp_conversations c
LEFT JOIN prospects p ON c.prospect_id = p.id
ORDER BY c.last_message_at DESC;

-- Create function to update conversation on new message
CREATE OR REPLACE FUNCTION update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert conversation
    INSERT INTO whatsapp_conversations (
        phone_number,
        first_message_at,
        last_message_at,
        total_messages
    ) VALUES (
        NEW.from_number,
        NEW.received_at,
        NEW.received_at,
        1
    )
    ON CONFLICT (phone_number) 
    DO UPDATE SET
        last_message_at = NEW.received_at,
        total_messages = whatsapp_conversations.total_messages + 1,
        unread_count = CASE 
            WHEN NEW.direction = 'inbound' THEN whatsapp_conversations.unread_count + 1
            ELSE whatsapp_conversations.unread_count
        END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update conversation
DROP TRIGGER IF EXISTS trigger_update_conversation ON whatsapp_messages;
CREATE TRIGGER trigger_update_conversation
    AFTER INSERT ON whatsapp_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_on_message();

-- Create function to mark messages as read
CREATE OR REPLACE FUNCTION mark_conversation_as_read(p_phone_number VARCHAR(50))
RETURNS void AS $$
BEGIN
    -- Update messages to read
    UPDATE whatsapp_messages
    SET status = 'read'
    WHERE from_number = p_phone_number
    AND status = 'received'
    AND direction = 'inbound';
    
    -- Reset unread count
    UPDATE whatsapp_conversations
    SET unread_count = 0
    WHERE phone_number = p_phone_number;
END;
$$ LANGUAGE plpgsql;

-- Create analytics view
CREATE OR REPLACE VIEW whatsapp_analytics AS
SELECT 
    COUNT(*) as total_messages,
    COUNT(CASE WHEN direction = 'inbound' THEN 1 END) as inbound_messages,
    COUNT(CASE WHEN direction = 'outbound' THEN 1 END) as outbound_messages,
    COUNT(CASE WHEN message_type = 'audio' THEN 1 END) as voice_messages,
    COUNT(CASE WHEN task_created = true THEN 1 END) as tasks_created,
    COUNT(CASE WHEN transcription_status = 'completed' THEN 1 END) as transcriptions_completed,
    COUNT(CASE WHEN processed = true THEN 1 END) as processed_messages,
    COUNT(DISTINCT from_number) as unique_contacts,
    ROUND(AVG(CASE 
        WHEN processed_at IS NOT NULL AND received_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (processed_at - received_at)) 
    END), 2) as avg_processing_time_seconds
FROM whatsapp_messages;

-- Add table comments
COMMENT ON TABLE whatsapp_messages IS 'Stores all WhatsApp messages with AI transcription and analysis';
COMMENT ON TABLE whatsapp_conversations IS 'Conversation threads for WhatsApp contacts';

-- Success message
SELECT 'WhatsApp Inbox system created successfully!' as status;

