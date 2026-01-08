-- Migration: Create company_attachments table for storing image metadata
-- Images are stored in Supabase Storage bucket 'company-attachments'
-- This table stores metadata and links to the storage files

CREATE TABLE IF NOT EXISTS company_attachments (
    id BIGSERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    storage_path TEXT NOT NULL,
    description TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient lookup by company
CREATE INDEX IF NOT EXISTS idx_company_attachments_company_id
ON company_attachments(company_id);

-- Index for ordering by creation date
CREATE INDEX IF NOT EXISTS idx_company_attachments_created_at
ON company_attachments(created_at DESC);
