-- Supabase setup script for prospect management
-- Run this in your Supabase SQL editor to create the prospects table

-- Create the prospects table
CREATE TABLE IF NOT EXISTS prospects (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    website VARCHAR(500),
    status VARCHAR(50) DEFAULT 'new' CHECK (status IN ('new', 'contacted', 'qualified', 'converted')),
    enriched_data JSONB DEFAULT '{}',
    google_place_id VARCHAR(255),
    notes TEXT,
    tags JSONB DEFAULT '{"city": [], "keywords": [], "custom": []}',
    search_query TEXT,
    enrichment_status VARCHAR(50) DEFAULT 'pending' CHECK (enrichment_status IN ('pending', 'in_progress', 'completed', 'failed', 'no_data')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_prospects_status ON prospects(status);
CREATE INDEX IF NOT EXISTS idx_prospects_created_at ON prospects(created_at);
CREATE INDEX IF NOT EXISTS idx_prospects_name ON prospects USING gin(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_prospects_tags ON prospects USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_prospects_search_query ON prospects USING gin(to_tsvector('english', search_query));
CREATE INDEX IF NOT EXISTS idx_prospects_enrichment_status ON prospects(enrichment_status);

-- Enable Row Level Security (RLS)
ALTER TABLE prospects ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Enable all operations for authenticated users" ON prospects;
DROP POLICY IF EXISTS "Enable all operations for anon users" ON prospects;

-- Create a policy that allows all operations for anon users (for this demo)
-- In production, you should implement proper user authentication
CREATE POLICY "Enable all operations for anon users" ON prospects
    FOR ALL USING (true);

-- Alternative: If you want to restrict to specific operations, use this instead:
-- CREATE POLICY "Enable insert for anon users" ON prospects FOR INSERT WITH CHECK (true);
-- CREATE POLICY "Enable select for anon users" ON prospects FOR SELECT USING (true);
-- CREATE POLICY "Enable update for anon users" ON prospects FOR UPDATE USING (true);
-- CREATE POLICY "Enable delete for anon users" ON prospects FOR DELETE USING (true);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to automatically update updated_at on row updates
CREATE TRIGGER update_prospects_updated_at BEFORE UPDATE ON prospects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data (optional)
INSERT INTO prospects (name, address, website, status, enriched_data) VALUES
('Sample Company 1', '123 Main St, Brussels, Belgium', 'https://example1.com', 'new', '{"vat": "BE0123456789", "email": "info@example1.com"}'),
('Sample Company 2', '456 Oak Ave, Antwerp, Belgium', 'https://example2.com', 'contacted', '{"vat": "BE0987654321", "phone": "+32 123 456 789"}')
ON CONFLICT DO NOTHING;
