-- Migration: Create company_notes table for note blocks
-- Each note block can have text and optionally linked images
-- Images are linked via the note_id in company_attachments

CREATE TABLE IF NOT EXISTS company_notes (
    id BIGSERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    note_text TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient lookup by company
CREATE INDEX IF NOT EXISTS idx_company_notes_company_id
ON company_notes(company_id);

-- Index for ordering by creation date
CREATE INDEX IF NOT EXISTS idx_company_notes_created_at
ON company_notes(created_at DESC);

-- Add note_id column to company_attachments to link images to notes
ALTER TABLE company_attachments
ADD COLUMN IF NOT EXISTS note_id BIGINT REFERENCES company_notes(id) ON DELETE CASCADE;

-- Index for efficient lookup by note
CREATE INDEX IF NOT EXISTS idx_company_attachments_note_id
ON company_attachments(note_id);
