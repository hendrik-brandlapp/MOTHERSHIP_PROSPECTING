-- Migration: No-Code Task Automation System
-- Creates tables for storing and executing automation rules

-- =====================================================
-- AUTOMATION RULES TABLE
-- Stores the IF/THEN automation rules created by users
-- =====================================================
CREATE TABLE IF NOT EXISTS automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Ownership
    created_by VARCHAR(100) NOT NULL,
    is_global BOOLEAN DEFAULT FALSE,  -- If true, applies to all users

    -- Rule state
    is_enabled BOOLEAN DEFAULT FALSE,
    is_draft BOOLEAN DEFAULT TRUE,

    -- Trigger configuration
    trigger_type VARCHAR(50) NOT NULL CHECK (trigger_type IN (
        'status_change',      -- Prospect status changes
        'time_based',         -- X days after event
        'field_change'        -- Specific field changes
    )),
    trigger_config JSONB NOT NULL,
    /* Example trigger_config structures:
       status_change: {"from_status": null, "to_status": "customer"}
       time_based: {"event": "last_contact", "days_offset": 7, "status_filter": ["first_contact"]}
       field_change: {"field": "assigned_to", "change_type": "set"}
    */

    -- Additional conditions (optional filters)
    conditions JSONB DEFAULT '[]',
    /* Example: [
        {"field": "region", "operator": "equals", "value": "Antwerp"},
        {"field": "priority_level", "operator": ">=", "value": 3}
    ] */

    -- Actions to perform
    actions JSONB NOT NULL DEFAULT '[]',
    /* Example: [
        {
            "type": "create_task",
            "config": {
                "title_template": "Follow up with {{prospect_name}}",
                "description_template": "Check in after first contact",
                "task_type": "call",
                "priority": 2,
                "due_date_offset_days": 3,
                "assigned_to": "{{current_user}}"
            }
        },
        {
            "type": "update_prospect_status",
            "config": {"new_status": "follow_up"}
        }
    ] */

    -- Execution tracking
    last_executed_at TIMESTAMPTZ,
    execution_count INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for automation_rules
CREATE INDEX IF NOT EXISTS idx_automation_rules_enabled ON automation_rules(is_enabled);
CREATE INDEX IF NOT EXISTS idx_automation_rules_trigger_type ON automation_rules(trigger_type);
CREATE INDEX IF NOT EXISTS idx_automation_rules_created_by ON automation_rules(created_by);
CREATE INDEX IF NOT EXISTS idx_automation_rules_is_global ON automation_rules(is_global);

-- =====================================================
-- AUTOMATION EXECUTIONS TABLE
-- Logs every execution of an automation rule
-- =====================================================
CREATE TABLE IF NOT EXISTS automation_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_rule_id UUID REFERENCES automation_rules(id) ON DELETE CASCADE,
    prospect_id UUID,

    -- What triggered this execution
    trigger_event JSONB NOT NULL,
    /* Example: {
        "type": "status_change",
        "from_status": "first_contact",
        "to_status": "customer",
        "triggered_by": "sales_rep_name"
    } */

    -- Execution result
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
        'pending', 'success', 'partial', 'failed', 'skipped'
    )),

    -- What was created/modified
    actions_executed JSONB DEFAULT '[]',
    /* Example: [
        {"type": "create_task", "task_id": "uuid", "success": true},
        {"type": "update_prospect_status", "success": true, "new_status": "follow_up"}
    ] */

    error_message TEXT,

    -- Timestamps
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for automation_executions
CREATE INDEX IF NOT EXISTS idx_automation_executions_rule ON automation_executions(automation_rule_id);
CREATE INDEX IF NOT EXISTS idx_automation_executions_prospect ON automation_executions(prospect_id);
CREATE INDEX IF NOT EXISTS idx_automation_executions_status ON automation_executions(status);
CREATE INDEX IF NOT EXISTS idx_automation_executions_executed_at ON automation_executions(executed_at DESC);

-- =====================================================
-- TIME-BASED AUTOMATION QUEUE
-- Queue for time-based triggers that need future evaluation
-- =====================================================
CREATE TABLE IF NOT EXISTS time_based_automation_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_rule_id UUID REFERENCES automation_rules(id) ON DELETE CASCADE,
    prospect_id UUID NOT NULL,

    -- When this should be evaluated
    scheduled_at TIMESTAMPTZ NOT NULL,

    -- Reference event info
    reference_event VARCHAR(50) NOT NULL,  -- 'created_at', 'last_contact_date', 'status_changed_at'
    reference_date DATE NOT NULL,

    -- Processing status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
        'pending', 'processed', 'cancelled', 'failed'
    )),
    processed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for time_based_automation_queue
CREATE INDEX IF NOT EXISTS idx_time_queue_scheduled ON time_based_automation_queue(scheduled_at, status);
CREATE INDEX IF NOT EXISTS idx_time_queue_prospect ON time_based_automation_queue(prospect_id);
CREATE INDEX IF NOT EXISTS idx_time_queue_rule ON time_based_automation_queue(automation_rule_id);
CREATE INDEX IF NOT EXISTS idx_time_queue_status ON time_based_automation_queue(status);

-- =====================================================
-- AUTOMATION EXECUTION LOCK
-- Prevents duplicate executions for the same trigger event
-- =====================================================
CREATE TABLE IF NOT EXISTS automation_execution_lock (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_rule_id UUID NOT NULL,
    prospect_id UUID NOT NULL,
    lock_key VARCHAR(255) NOT NULL,  -- Unique key for this trigger instance
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint prevents duplicate executions
    UNIQUE(automation_rule_id, prospect_id, lock_key)
);

-- Index for cleanup of old locks
CREATE INDEX IF NOT EXISTS idx_execution_lock_created ON automation_execution_lock(created_at);

-- =====================================================
-- ROW LEVEL SECURITY POLICIES
-- =====================================================
ALTER TABLE automation_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_based_automation_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_execution_lock ENABLE ROW LEVEL SECURITY;

-- Allow all operations for anon users (adjust based on your auth setup)
CREATE POLICY "Enable all for anon on automation_rules"
    ON automation_rules FOR ALL USING (true);
CREATE POLICY "Enable all for anon on automation_executions"
    ON automation_executions FOR ALL USING (true);
CREATE POLICY "Enable all for anon on time_based_automation_queue"
    ON time_based_automation_queue FOR ALL USING (true);
CREATE POLICY "Enable all for anon on automation_execution_lock"
    ON automation_execution_lock FOR ALL USING (true);

-- =====================================================
-- HELPER FUNCTION: Clean up old execution locks
-- Run periodically to remove locks older than 30 days
-- =====================================================
CREATE OR REPLACE FUNCTION cleanup_old_execution_locks()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM automation_execution_lock
    WHERE created_at < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
