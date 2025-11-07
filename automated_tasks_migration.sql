-- Add automated task functionality to sales_tasks table
-- Run this in your Supabase SQL editor

-- Add columns for recurring tasks and automation
ALTER TABLE sales_tasks 
ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS recurring_interval_days INTEGER NULL,
ADD COLUMN IF NOT EXISTS parent_task_id UUID NULL REFERENCES sales_tasks(id),
ADD COLUMN IF NOT EXISTS is_automated BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS automation_trigger VARCHAR(50) NULL;

-- Add index for recurring tasks
CREATE INDEX IF NOT EXISTS idx_sales_tasks_recurring ON sales_tasks(is_recurring, recurring_interval_days);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_parent ON sales_tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_sales_tasks_automated ON sales_tasks(is_automated, automation_trigger);

-- Add comments for new columns
COMMENT ON COLUMN sales_tasks.is_recurring IS 'Whether this task repeats automatically';
COMMENT ON COLUMN sales_tasks.recurring_interval_days IS 'Number of days between recurring instances';
COMMENT ON COLUMN sales_tasks.parent_task_id IS 'Reference to original task for recurring instances';
COMMENT ON COLUMN sales_tasks.is_automated IS 'Whether this task was created automatically';
COMMENT ON COLUMN sales_tasks.automation_trigger IS 'What triggered the automated task creation (e.g., status_change_to_customer)';

-- Create a function to automatically create recurring tasks
CREATE OR REPLACE FUNCTION create_recurring_task_instance(original_task_id UUID)
RETURNS UUID AS $$
DECLARE
    original_task RECORD;
    new_task_id UUID;
    new_due_date DATE;
BEGIN
    -- Get the original recurring task
    SELECT * INTO original_task FROM sales_tasks WHERE id = original_task_id AND is_recurring = TRUE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Original recurring task not found or not marked as recurring';
    END IF;
    
    -- Calculate new due date
    new_due_date := CURRENT_DATE + INTERVAL '1 day' * original_task.recurring_interval_days;
    
    -- Create new task instance
    INSERT INTO sales_tasks (
        prospect_id, title, description, task_type, category, priority, 
        due_date, status, created_at, updated_at, is_automated, 
        automation_trigger, parent_task_id
    ) VALUES (
        original_task.prospect_id,
        original_task.title,
        original_task.description,
        original_task.task_type,
        original_task.category,
        original_task.priority,
        new_due_date,
        'pending',
        NOW(),
        NOW(),
        TRUE,
        'recurring_task',
        original_task_id
    ) RETURNING id INTO new_task_id;
    
    RETURN new_task_id;
END;
$$ LANGUAGE plpgsql;

-- Create a function to handle completed recurring tasks
CREATE OR REPLACE FUNCTION handle_recurring_task_completion()
RETURNS TRIGGER AS $$
BEGIN
    -- If a recurring task is completed, create the next instance
    IF NEW.status = 'completed' AND OLD.status != 'completed' AND NEW.is_recurring = TRUE THEN
        PERFORM create_recurring_task_instance(NEW.id);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for recurring task completion
DROP TRIGGER IF EXISTS trigger_recurring_task_completion ON sales_tasks;
CREATE TRIGGER trigger_recurring_task_completion
    AFTER UPDATE ON sales_tasks
    FOR EACH ROW
    EXECUTE FUNCTION handle_recurring_task_completion();

-- Success message
SELECT 'Automated tasks system added successfully!' as status;
