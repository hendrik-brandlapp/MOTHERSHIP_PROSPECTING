-- Migration: Create trip_stop_notes table for notes on route stops
-- Each note block can have text and optionally linked images
-- Images are stored in Supabase Storage bucket 'trip-attachments'

CREATE TABLE IF NOT EXISTS trip_stop_notes (
    id BIGSERIAL PRIMARY KEY,
    trip_stop_id UUID NOT NULL REFERENCES trip_stops(id) ON DELETE CASCADE,
    note_text TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient lookup by trip stop
CREATE INDEX IF NOT EXISTS idx_trip_stop_notes_trip_stop_id
ON trip_stop_notes(trip_stop_id);

-- Index for ordering by creation date
CREATE INDEX IF NOT EXISTS idx_trip_stop_notes_created_at
ON trip_stop_notes(created_at DESC);

-- Create trip_stop_attachments table for storing image metadata
CREATE TABLE IF NOT EXISTS trip_stop_attachments (
    id BIGSERIAL PRIMARY KEY,
    trip_stop_id UUID NOT NULL REFERENCES trip_stops(id) ON DELETE CASCADE,
    note_id BIGINT REFERENCES trip_stop_notes(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    storage_path TEXT NOT NULL,
    description TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient lookup by trip stop
CREATE INDEX IF NOT EXISTS idx_trip_stop_attachments_trip_stop_id
ON trip_stop_attachments(trip_stop_id);

-- Index for efficient lookup by note
CREATE INDEX IF NOT EXISTS idx_trip_stop_attachments_note_id
ON trip_stop_attachments(note_id);

-- Index for ordering by creation date
CREATE INDEX IF NOT EXISTS idx_trip_stop_attachments_created_at
ON trip_stop_attachments(created_at DESC);
