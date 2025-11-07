-- SAFE PIPELINE MIGRATION: Complete fix for prospects status constraint issue
-- This script safely handles the migration even if previous attempts failed

-- Step 1: Check current state
SELECT 'Current prospects count:' as info, COUNT(*) as count FROM prospects;
SELECT 'Current status distribution:' as info, status, COUNT(*) FROM prospects GROUP BY status ORDER BY status;

-- Step 2: Add new columns safely (won't fail if they already exist)
DO $$ BEGIN
    ALTER TABLE prospects ADD COLUMN IF NOT EXISTS region VARCHAR(100);
    ALTER TABLE prospects ADD COLUMN IF NOT EXISTS prospect_type VARCHAR(100);
    ALTER TABLE prospects ADD COLUMN IF NOT EXISTS contact_later_date DATE;
    ALTER TABLE prospects ADD COLUMN IF NOT EXISTS contact_later_reason TEXT;
    ALTER TABLE prospects ADD COLUMN IF NOT EXISTS unqualified_reason VARCHAR(100);
    ALTER TABLE prospects ADD COLUMN IF NOT EXISTS unqualified_details TEXT;
    ALTER TABLE prospects ADD COLUMN IF NOT EXISTS last_contact_date DATE;
    ALTER TABLE prospects ADD COLUMN IF NOT EXISTS next_action TEXT;
    ALTER TABLE prospects ADD COLUMN IF NOT EXISTS priority_level INTEGER DEFAULT 3 CHECK (priority_level >= 1 AND priority_level <= 5);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Some columns may already exist, continuing...';
END $$;

-- Step 3: Create new tables safely
CREATE TABLE IF NOT EXISTS prospect_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_id UUID REFERENCES prospects(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL DEFAULT 'contact_later',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    scheduled_date DATE NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS unqualified_reasons (
    id SERIAL PRIMARY KEY,
    reason_code VARCHAR(50) UNIQUE NOT NULL,
    reason_text VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0
);

-- Step 4: Insert unqualified reasons (safe with ON CONFLICT)
INSERT INTO unqualified_reasons (reason_code, reason_text, description, sort_order) VALUES
('no_fridge_space', 'No Fridge space & no place for extra fridge', 'Lacks refrigeration capacity', 1),
('no_fit', 'No fit', 'Product or service does not match their needs', 2),
('not_convinced', 'Not convinced by product', 'Skeptical about product quality or benefits', 3),
('too_expensive', 'Too expensive', 'Price point is beyond their budget', 4),
('prefers_competition', 'Likes competition more', 'Already satisfied with competitor products', 5),
('unclear', 'Unclear', 'Reason for rejection is not clear or specified', 6)
ON CONFLICT (reason_code) DO NOTHING;

-- Step 5: Create indexes safely
CREATE INDEX IF NOT EXISTS idx_prospect_tasks_prospect_id ON prospect_tasks(prospect_id);
CREATE INDEX IF NOT EXISTS idx_prospect_tasks_scheduled_date ON prospect_tasks(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_prospect_tasks_completed ON prospect_tasks(completed);
CREATE INDEX IF NOT EXISTS idx_prospects_region ON prospects(region);
CREATE INDEX IF NOT EXISTS idx_prospects_prospect_type ON prospects(prospect_type);
CREATE INDEX IF NOT EXISTS idx_prospects_contact_later_date ON prospects(contact_later_date);
CREATE INDEX IF NOT EXISTS idx_prospects_unqualified_reason ON prospects(unqualified_reason);
CREATE INDEX IF NOT EXISTS idx_prospects_priority_level ON prospects(priority_level);

-- Step 6: Enable RLS safely
ALTER TABLE prospect_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE unqualified_reasons ENABLE ROW LEVEL SECURITY;

-- Step 7: Create policies safely
DROP POLICY IF EXISTS "Enable all operations for anon users on tasks" ON prospect_tasks;
CREATE POLICY "Enable all operations for anon users on tasks" ON prospect_tasks FOR ALL USING (true);

-- Step 8: CRITICAL FIX - Handle data migration BEFORE adding constraint
-- First, ensure all NULL statuses become 'new_leads'
UPDATE prospects SET status = 'new_leads' WHERE status IS NULL;

-- Then map old statuses to new ones
UPDATE prospects SET status = CASE
    WHEN status = 'new' THEN 'new_leads'
    WHEN status = 'contacted' THEN 'first_contact'
    WHEN status = 'qualified' THEN 'follow_up'
    WHEN status = 'converted' THEN 'customer'
    WHEN status NOT IN ('new_leads', 'first_contact', 'meeting_planned', 'follow_up', 'customer', 'ex_customer', 'contact_later', 'unqualified') THEN 'new_leads'
    ELSE status  -- Keep existing valid statuses
END;

-- Step 9: Drop any existing constraint
ALTER TABLE prospects DROP CONSTRAINT IF EXISTS prospects_status_check;

-- Step 10: Add the correct constraint
ALTER TABLE prospects ADD CONSTRAINT prospects_status_check
CHECK (status IN (
    'new_leads', 'first_contact', 'meeting_planned', 'follow_up',
    'customer', 'ex_customer', 'contact_later', 'unqualified'
));

-- Step 11: Create or replace pipeline stats view
CREATE OR REPLACE VIEW prospect_pipeline_stats AS
SELECT
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM prospects
WHERE status IS NOT NULL
GROUP BY status
ORDER BY
    CASE status
        WHEN 'new_leads' THEN 1
        WHEN 'first_contact' THEN 2
        WHEN 'meeting_planned' THEN 3
        WHEN 'follow_up' THEN 4
        WHEN 'customer' THEN 5
        WHEN 'ex_customer' THEN 6
        WHEN 'contact_later' THEN 7
        WHEN 'unqualified' THEN 8
        ELSE 9
    END;

-- Step 12: Create update function if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Step 13: Create triggers
DROP TRIGGER IF EXISTS update_prospects_updated_at ON prospects;
CREATE TRIGGER update_prospects_updated_at
    BEFORE UPDATE ON prospects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_prospect_tasks_updated_at ON prospect_tasks;
CREATE TRIGGER update_prospect_tasks_updated_at
    BEFORE UPDATE ON prospect_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Step 14: Add table comments
COMMENT ON TABLE prospects IS 'Enhanced prospects table with comprehensive pipeline management';
COMMENT ON TABLE prospect_tasks IS 'Tasks and reminders for prospect follow-up';
COMMENT ON TABLE unqualified_reasons IS 'Predefined reasons for marking prospects as unqualified';

-- Step 15: Final verification
SELECT 'Migration completed successfully!' as status;
SELECT 'Final status distribution:' as info, status, COUNT(*) as count
FROM prospects
GROUP BY status
ORDER BY
    CASE status
        WHEN 'new_leads' THEN 1
        WHEN 'first_contact' THEN 2
        WHEN 'meeting_planned' THEN 3
        WHEN 'follow_up' THEN 4
        WHEN 'customer' THEN 5
        WHEN 'ex_customer' THEN 6
        WHEN 'contact_later' THEN 7
        WHEN 'unqualified' THEN 8
        ELSE 9
    END;
