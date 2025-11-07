-- QUICK FIX: Create the basic sales_tasks table structure needed for automated tasks
-- Run this in your Supabase SQL editor

-- First, make sure the sales_tasks table has the right structure
DROP TABLE IF EXISTS sales_tasks CASCADE;

CREATE TABLE sales_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_id UUID REFERENCES prospects(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL DEFAULT 'general',
    category VARCHAR(50) DEFAULT 'sales',
    priority INTEGER DEFAULT 3 CHECK (priority >= 1 AND priority <= 4),
    status VARCHAR(20) DEFAULT 'pending',
    due_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Automated task fields
    is_automated BOOLEAN DEFAULT FALSE,
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_interval_days INTEGER NULL,
    parent_task_id UUID NULL REFERENCES sales_tasks(id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_sales_tasks_prospect_id ON sales_tasks(prospect_id);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_due_date ON sales_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_status ON sales_tasks(status);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_priority ON sales_tasks(priority);

-- Enable Row Level Security
ALTER TABLE sales_tasks ENABLE ROW LEVEL SECURITY;

-- Create a simple RLS policy (adjust as needed)
DROP POLICY IF EXISTS "Enable all operations for authenticated users" ON sales_tasks;
CREATE POLICY "Enable all operations for authenticated users" ON sales_tasks
    FOR ALL USING (true);

-- Success message
SELECT 'Quick fix: sales_tasks table created successfully!' as status;
