-- Add visited tag functionality to prospects
-- Run this in your Supabase SQL editor

-- Add a visited column to track if a prospect has been visited
ALTER TABLE prospects 
ADD COLUMN IF NOT EXISTS visited_at TIMESTAMPTZ NULL,
ADD COLUMN IF NOT EXISTS visited_by VARCHAR(100) NULL;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_prospects_visited_at ON prospects(visited_at);
CREATE INDEX IF NOT EXISTS idx_prospects_visited_by ON prospects(visited_by);

-- Add a function to automatically add visited tag when prospect is viewed
CREATE OR REPLACE FUNCTION add_visited_tag_to_prospect(prospect_id_param UUID, user_name VARCHAR DEFAULT 'User')
RETURNS void AS $$
BEGIN
    -- Update the visited timestamp and user
    UPDATE prospects 
    SET 
        visited_at = NOW(),
        visited_by = user_name,
        tags = CASE 
            WHEN tags IS NULL THEN 
                jsonb_build_object(
                    'city', COALESCE(tags->'city', '[]'::jsonb),
                    'keywords', COALESCE(tags->'keywords', '[]'::jsonb),
                    'custom', COALESCE(tags->'custom', '[]'::jsonb),
                    'system', jsonb_build_array('visited')
                )
            WHEN tags->'system' IS NULL THEN 
                tags || jsonb_build_object('system', jsonb_build_array('visited'))
            WHEN NOT (tags->'system' @> '"visited"'::jsonb) THEN
                tags || jsonb_build_object('system', (tags->'system') || '"visited"'::jsonb)
            ELSE tags
        END,
        updated_at = NOW()
    WHERE id = prospect_id_param;
END;
$$ LANGUAGE plpgsql;

-- Add a function to check if a prospect has been visited
CREATE OR REPLACE FUNCTION is_prospect_visited(prospect_id_param UUID)
RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM prospects 
        WHERE id = prospect_id_param 
        AND visited_at IS NOT NULL
    );
END;
$$ LANGUAGE plpgsql;

-- Create a view for visited prospects analytics
CREATE OR REPLACE VIEW visited_prospects_analytics AS
SELECT 
    DATE_TRUNC('day', visited_at) as visit_date,
    visited_by,
    COUNT(*) as visits_count,
    COUNT(DISTINCT id) as unique_prospects_visited
FROM prospects 
WHERE visited_at IS NOT NULL
GROUP BY DATE_TRUNC('day', visited_at), visited_by
ORDER BY visit_date DESC;

-- Comment on the new functionality
COMMENT ON COLUMN prospects.visited_at IS 'Timestamp when the prospect was last visited/viewed in detail';
COMMENT ON COLUMN prospects.visited_by IS 'User who last visited/viewed the prospect';
COMMENT ON FUNCTION add_visited_tag_to_prospect IS 'Automatically adds visited tag and updates visit tracking';
COMMENT ON FUNCTION is_prospect_visited IS 'Checks if a prospect has been visited';
COMMENT ON VIEW visited_prospects_analytics IS 'Analytics view for prospect visit tracking';

-- Success message
SELECT 'Visited tag functionality added successfully!' as status;
