-- COMPREHENSIVE TASK MANAGEMENT SYSTEM
-- Run this in your Supabase SQL editor to create the complete task system

-- Create enhanced tasks table
CREATE TABLE IF NOT EXISTS sales_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Task categorization
    task_type VARCHAR(50) NOT NULL DEFAULT 'general' CHECK (task_type IN (
        'call', 'email', 'meeting', 'follow_up', 'demo', 'proposal', 
        'contract', 'onboarding', 'support', 'research', 'general'
    )),
    category VARCHAR(50) DEFAULT 'sales' CHECK (category IN (
        'sales', 'marketing', 'support', 'admin', 'research', 'follow_up'
    )),
    
    -- Priority and status
    priority INTEGER DEFAULT 3 CHECK (priority >= 1 AND priority <= 5), -- 1=highest, 5=lowest
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
        'pending', 'in_progress', 'completed', 'cancelled', 'overdue'
    )),
    
    -- Scheduling
    due_date DATE,
    due_time TIME,
    scheduled_date DATE,
    scheduled_time TIME,
    estimated_duration INTEGER, -- minutes
    
    -- Relationships
    prospect_id UUID REFERENCES prospects(id) ON DELETE SET NULL,
    assigned_to VARCHAR(100), -- salesperson name/id
    created_by VARCHAR(100),
    
    -- Progress tracking
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    completed_at TIMESTAMPTZ,
    
    -- Additional data
    notes TEXT,
    tags JSONB DEFAULT '[]',
    attachments JSONB DEFAULT '[]',
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create task comments/updates table
CREATE TABLE IF NOT EXISTS task_comments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    task_id UUID REFERENCES sales_tasks(id) ON DELETE CASCADE,
    comment TEXT NOT NULL,
    comment_type VARCHAR(20) DEFAULT 'comment' CHECK (comment_type IN (
        'comment', 'status_change', 'priority_change', 'assignment', 'completion'
    )),
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create task templates table
CREATE TABLE IF NOT EXISTS task_templates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) DEFAULT 'sales',
    priority INTEGER DEFAULT 3,
    estimated_duration INTEGER,
    default_notes TEXT,
    tags JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default task templates
INSERT INTO task_templates (name, description, task_type, category, priority, estimated_duration, default_notes, tags) VALUES
('Cold Call Follow-up', 'Follow up on initial cold call contact', 'call', 'sales', 2, 15, 'Call to discuss their interest and next steps', '["follow-up", "cold-call"]'),
('Demo Scheduling', 'Schedule product demonstration', 'meeting', 'sales', 2, 30, 'Book demo session and send calendar invite', '["demo", "meeting"]'),
('Proposal Preparation', 'Prepare and send proposal', 'proposal', 'sales', 1, 120, 'Create customized proposal based on client needs', '["proposal", "high-priority"]'),
('Contract Review', 'Review and finalize contract terms', 'contract', 'sales', 1, 60, 'Review contract details with legal team', '["contract", "legal"]'),
('Onboarding Call', 'Welcome new customer and start onboarding', 'call', 'support', 2, 45, 'Welcome call and setup next steps', '["onboarding", "welcome"]'),
('Quarterly Check-in', 'Regular customer health check', 'call', 'support', 3, 30, 'Check customer satisfaction and identify opportunities', '["check-in", "retention"]'),
('Market Research', 'Research prospect company and industry', 'research', 'research', 3, 60, 'Gather company information and industry insights', '["research", "preparation"]'),
('Email Follow-up', 'Send follow-up email after meeting', 'email', 'follow_up', 3, 10, 'Send summary and next steps via email', '["email", "follow-up"]')
ON CONFLICT DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_sales_tasks_status ON sales_tasks(status);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_priority ON sales_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_due_date ON sales_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_assigned_to ON sales_tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_prospect_id ON sales_tasks(prospect_id);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_task_type ON sales_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_category ON sales_tasks(category);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_created_at ON sales_tasks(created_at);

CREATE INDEX IF NOT EXISTS idx_task_comments_task_id ON task_comments(task_id);
CREATE INDEX IF NOT EXISTS idx_task_comments_created_at ON task_comments(created_at);

-- Enable Row Level Security
ALTER TABLE sales_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_templates ENABLE ROW LEVEL SECURITY;

-- Create policies (allowing all operations for demo - customize for production)
CREATE POLICY "Enable all operations for anon users on sales_tasks" ON sales_tasks FOR ALL USING (true);
CREATE POLICY "Enable all operations for anon users on task_comments" ON task_comments FOR ALL USING (true);
CREATE POLICY "Enable all operations for anon users on task_templates" ON task_templates FOR ALL USING (true);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_sales_tasks_updated_at ON sales_tasks;
CREATE TRIGGER update_sales_tasks_updated_at
    BEFORE UPDATE ON sales_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to automatically mark overdue tasks
CREATE OR REPLACE FUNCTION mark_overdue_tasks()
RETURNS void AS $$
BEGIN
    UPDATE sales_tasks 
    SET status = 'overdue'
    WHERE status = 'pending' 
    AND due_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- Create view for task analytics
CREATE OR REPLACE VIEW task_analytics AS
SELECT 
    status,
    task_type,
    category,
    priority,
    COUNT(*) as count,
    ROUND(AVG(progress_percentage), 2) as avg_progress,
    COUNT(CASE WHEN due_date < CURRENT_DATE AND status != 'completed' THEN 1 END) as overdue_count
FROM sales_tasks 
GROUP BY status, task_type, category, priority
ORDER BY priority, status;

-- Create view for daily task summary
CREATE OR REPLACE VIEW daily_task_summary AS
SELECT 
    CURRENT_DATE as date,
    COUNT(*) as total_tasks,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_tasks,
    COUNT(CASE WHEN status = 'overdue' THEN 1 END) as overdue_tasks,
    COUNT(CASE WHEN due_date = CURRENT_DATE THEN 1 END) as due_today,
    ROUND(
        COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / 
        NULLIF(COUNT(*), 0), 2
    ) as completion_rate
FROM sales_tasks;

-- Create function to get upcoming tasks
CREATE OR REPLACE FUNCTION get_upcoming_tasks(days_ahead INTEGER DEFAULT 7)
RETURNS TABLE (
    id UUID,
    title VARCHAR(255),
    due_date DATE,
    priority INTEGER,
    task_type VARCHAR(50),
    prospect_name VARCHAR(255),
    days_until_due INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        st.id,
        st.title,
        st.due_date,
        st.priority,
        st.task_type,
        p.name as prospect_name,
        (st.due_date - CURRENT_DATE) as days_until_due
    FROM sales_tasks st
    LEFT JOIN prospects p ON st.prospect_id = p.id
    WHERE st.due_date BETWEEN CURRENT_DATE AND (CURRENT_DATE + days_ahead)
    AND st.status IN ('pending', 'in_progress')
    ORDER BY st.due_date, st.priority;
END;
$$ LANGUAGE plpgsql;

-- Add table comments
COMMENT ON TABLE sales_tasks IS 'Comprehensive task management system for sales team';
COMMENT ON TABLE task_comments IS 'Comments and updates for tasks';
COMMENT ON TABLE task_templates IS 'Reusable task templates for common activities';

-- Final verification
SELECT 'Task management system created successfully!' as status;

-- Show sample data structure
SELECT 'Task types available:' as info;
SELECT 'call, email, meeting, follow_up, demo, proposal, contract, onboarding, support, research, general' as available_task_types;

SELECT 'System ready for task management!' as final_status;
