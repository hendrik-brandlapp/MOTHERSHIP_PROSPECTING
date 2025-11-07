-- Prospect Pipeline Enhancement Migration
-- Run this in your Supabase SQL editor to enhance the prospects table

-- First, add new columns for the enhanced pipeline
ALTER TABLE prospects 
ADD COLUMN IF NOT EXISTS region VARCHAR(100),
ADD COLUMN IF NOT EXISTS prospect_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS contact_later_date DATE,
ADD COLUMN IF NOT EXISTS contact_later_reason TEXT,
ADD COLUMN IF NOT EXISTS unqualified_reason VARCHAR(100),
ADD COLUMN IF NOT EXISTS unqualified_details TEXT,
ADD COLUMN IF NOT EXISTS last_contact_date DATE,
ADD COLUMN IF NOT EXISTS next_action TEXT,
ADD COLUMN IF NOT EXISTS priority_level INTEGER DEFAULT 3 CHECK (priority_level >= 1 AND priority_level <= 5);

-- Update the status constraint to include all new pipeline stages
-- (This is now done AFTER data migration below)

-- Create tasks table for contact later functionality
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

-- Create index for tasks
CREATE INDEX IF NOT EXISTS idx_prospect_tasks_prospect_id ON prospect_tasks(prospect_id);
CREATE INDEX IF NOT EXISTS idx_prospect_tasks_scheduled_date ON prospect_tasks(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_prospect_tasks_completed ON prospect_tasks(completed);

-- Enable RLS for tasks table
ALTER TABLE prospect_tasks ENABLE ROW LEVEL SECURITY;

-- Create policy for tasks table (allowing all operations for demo)
CREATE POLICY "Enable all operations for anon users on tasks" ON prospect_tasks
    FOR ALL USING (true);

-- Create unqualified reasons lookup table
CREATE TABLE IF NOT EXISTS unqualified_reasons (
    id SERIAL PRIMARY KEY,
    reason_code VARCHAR(50) UNIQUE NOT NULL,
    reason_text VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0
);

-- Insert predefined unqualified reasons
INSERT INTO unqualified_reasons (reason_code, reason_text, description, sort_order) VALUES
('no_fridge_space', 'No Fridge space & no place for extra fridge', 'Lacks refrigeration capacity', 1),
('no_fit', 'No fit', 'Product or service does not match their needs', 2),
('not_convinced', 'Not convinced by product', 'Skeptical about product quality or benefits', 3),
('too_expensive', 'Too expensive', 'Price point is beyond their budget', 4),
('prefers_competition', 'Likes competition more', 'Already satisfied with competitor products', 5),
('unclear', 'Unclear', 'Reason for rejection is not clear or specified', 6)
ON CONFLICT (reason_code) DO NOTHING;

-- Update existing prospects to use new status values (map old to new)
-- First, handle NULL values
UPDATE prospects
SET status = 'new_leads'
WHERE status IS NULL;

-- Then update existing status values
UPDATE prospects
SET status = CASE
    WHEN status = 'new' THEN 'new_leads'
    WHEN status = 'contacted' THEN 'first_contact'
    WHEN status = 'qualified' THEN 'follow_up'
    WHEN status = 'converted' THEN 'customer'
    ELSE 'new_leads'  -- Default to new_leads for any other values
END;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_prospects_region ON prospects(region);
CREATE INDEX IF NOT EXISTS idx_prospects_prospect_type ON prospects(prospect_type);
CREATE INDEX IF NOT EXISTS idx_prospects_contact_later_date ON prospects(contact_later_date);
CREATE INDEX IF NOT EXISTS idx_prospects_unqualified_reason ON prospects(unqualified_reason);
CREATE INDEX IF NOT EXISTS idx_prospects_priority_level ON prospects(priority_level);

-- Create a view for pipeline analytics
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

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
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

-- Now add the status constraint after data migration is complete
ALTER TABLE prospects
DROP CONSTRAINT IF EXISTS prospects_status_check;

ALTER TABLE prospects
ADD CONSTRAINT prospects_status_check
CHECK (status IN (
    'new_leads',           -- 🔍 New Leads – nog te contacteren
    'first_contact',       -- 🤝 First Contact – eerste gesprek gehad
    'meeting_planned',     -- 📅 Meeting Planned – afspraak vastgelegd
    'follow_up',           -- ✍️ Follow-up – samples verstuurd of tasting gedaan
    'customer',            -- 🌱 Customer – actieve klant
    'ex_customer',         -- 🔙 Ex-Customer – gestopt met bestellen
    'contact_later',       -- ⏳ Contact Later – interessant, maar nog niet het juiste moment
    'unqualified'          -- ❌ Unqualified – niet relevant
));

COMMENT ON TABLE prospects IS 'Enhanced prospects table with comprehensive pipeline management';
COMMENT ON TABLE prospect_tasks IS 'Tasks and reminders for prospect follow-up';
COMMENT ON TABLE unqualified_reasons IS 'Predefined reasons for marking prospects as unqualified';
