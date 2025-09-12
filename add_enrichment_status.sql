-- Add enrichment status column to track AI enrichment process
-- Run this in your Supabase SQL editor

-- Add enrichment status column
ALTER TABLE prospects 
ADD COLUMN IF NOT EXISTS enrichment_status VARCHAR(50) DEFAULT 'pending' 
CHECK (enrichment_status IN ('pending', 'in_progress', 'completed', 'failed', 'no_data'));

-- Create index for the new column
CREATE INDEX IF NOT EXISTS idx_prospects_enrichment_status ON prospects(enrichment_status);

-- Update existing prospects to have appropriate status based on their current data
UPDATE prospects 
SET enrichment_status = CASE 
    WHEN enriched_data IS NOT NULL 
         AND enriched_data != '{}'::jsonb 
         AND (
             (enriched_data->>'vat' IS NOT NULL AND enriched_data->>'vat' != '' AND enriched_data->>'vat' != 'empty') OR
             (enriched_data->>'email' IS NOT NULL AND enriched_data->>'email' != '' AND enriched_data->>'email' != 'empty') OR
             (enriched_data->>'phone' IS NOT NULL AND enriched_data->>'phone' != '' AND enriched_data->>'phone' != 'empty') OR
             (enriched_data->>'site' IS NOT NULL AND enriched_data->>'site' != '' AND enriched_data->>'site' != 'empty')
         )
    THEN 'completed'
    WHEN enriched_data IS NOT NULL AND enriched_data != '{}'::jsonb
    THEN 'no_data'
    ELSE 'pending'
END
WHERE enrichment_status = 'pending';

COMMIT;
