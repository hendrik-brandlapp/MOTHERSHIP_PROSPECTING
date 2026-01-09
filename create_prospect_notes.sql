-- Migration: Create prospect_notes table for note blocks
-- Each note block can have text and optionally linked images
-- Images are stored in Supabase Storage bucket 'prospect-attachments'

CREATE TABLE IF NOT EXISTS prospect_notes (
    id BIGSERIAL PRIMARY KEY,
    prospect_id UUID NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    note_text TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient lookup by prospect
CREATE INDEX IF NOT EXISTS idx_prospect_notes_prospect_id
ON prospect_notes(prospect_id);

-- Index for ordering by creation date
CREATE INDEX IF NOT EXISTS idx_prospect_notes_created_at
ON prospect_notes(created_at DESC);

-- Create prospect_attachments table for storing image metadata
CREATE TABLE IF NOT EXISTS prospect_attachments (
    id BIGSERIAL PRIMARY KEY,
    prospect_id UUID NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    note_id BIGINT REFERENCES prospect_notes(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    storage_path TEXT NOT NULL,
    description TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient lookup by prospect
CREATE INDEX IF NOT EXISTS idx_prospect_attachments_prospect_id
ON prospect_attachments(prospect_id);

-- Index for efficient lookup by note
CREATE INDEX IF NOT EXISTS idx_prospect_attachments_note_id
ON prospect_attachments(note_id);

-- Index for ordering by creation date
CREATE INDEX IF NOT EXISTS idx_prospect_attachments_created_at
ON prospect_attachments(created_at DESC);
