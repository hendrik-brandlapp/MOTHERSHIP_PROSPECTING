-- Add salesperson column to companies and prospects tables

-- Add to companies table
ALTER TABLE companies 
ADD COLUMN IF NOT EXISTS assigned_salesperson VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_companies_salesperson 
ON companies(assigned_salesperson);

-- Add to prospects table (if not already there)
ALTER TABLE prospects 
ADD COLUMN IF NOT EXISTS assigned_salesperson VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_prospects_salesperson 
ON prospects(assigned_salesperson);

-- Comment
COMMENT ON COLUMN companies.assigned_salesperson IS 'Name or ID of salesperson assigned to this company';
COMMENT ON COLUMN prospects.assigned_salesperson IS 'Name or ID of salesperson assigned to this prospect';

SELECT 'Salesperson columns added successfully!' as status;

