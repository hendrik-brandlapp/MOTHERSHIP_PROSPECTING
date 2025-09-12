-- Migration script to add tagging functionality to existing prospects table
-- Run this in your Supabase SQL editor if you already have the prospects table

-- Add new columns for tagging and enrichment status
ALTER TABLE prospects 
ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '{"city": [], "keywords": [], "custom": []}',
ADD COLUMN IF NOT EXISTS search_query TEXT,
ADD COLUMN IF NOT EXISTS enrichment_status VARCHAR(50) DEFAULT 'pending' CHECK (enrichment_status IN ('pending', 'in_progress', 'completed', 'failed', 'no_data'));

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_prospects_tags ON prospects USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_prospects_search_query ON prospects USING gin(to_tsvector('english', search_query));
CREATE INDEX IF NOT EXISTS idx_prospects_enrichment_status ON prospects(enrichment_status);

-- Update existing records to have the default tags structure
UPDATE prospects 
SET tags = '{"city": [], "keywords": [], "custom": []}'::jsonb 
WHERE tags IS NULL;

-- Extract city information from existing addresses and add as tags
UPDATE prospects 
SET tags = jsonb_set(
    tags, 
    '{city}', 
    CASE 
        WHEN address ILIKE '%Antwerpen%' OR address ILIKE '%Antwerp%' THEN '["Antwerpen"]'::jsonb
        WHEN address ILIKE '%Gent%' OR address ILIKE '%Ghent%' THEN '["Gent"]'::jsonb
        WHEN address ILIKE '%Brussels%' OR address ILIKE '%Brussel%' THEN '["Brussels"]'::jsonb
        WHEN address ILIKE '%Brugge%' OR address ILIKE '%Bruges%' THEN '["Brugge"]'::jsonb
        WHEN address ILIKE '%Leuven%' THEN '["Leuven"]'::jsonb
        ELSE '[]'::jsonb
    END
)
WHERE address IS NOT NULL AND tags->>'city' = '[]';

COMMIT;
