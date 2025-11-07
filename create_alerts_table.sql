-- Create customer_alerts table for storing and tracking alerts
CREATE TABLE IF NOT EXISTS customer_alerts (
    id BIGSERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    public_name TEXT,
    email TEXT,
    
    -- Alert details
    alert_type TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW')),
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    
    -- Metrics (stored as JSONB for flexibility)
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'dismissed', 'actioned', 'resolved')),
    actioned_at TIMESTAMP WITH TIME ZONE,
    actioned_by TEXT,
    dismissed_at TIMESTAMP WITH TIME ZONE,
    dismissed_by TEXT,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    first_detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Analysis metadata
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_company_id FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_alerts_company_id ON customer_alerts(company_id);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON customer_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_priority ON customer_alerts(priority);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON customer_alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON customer_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_company_status ON customer_alerts(company_id, status);

-- Create composite index for common queries
CREATE INDEX IF NOT EXISTS idx_alerts_active_priority ON customer_alerts(status, priority, created_at DESC) 
WHERE status = 'active';

-- Add GIN index for JSONB metrics searching
CREATE INDEX IF NOT EXISTS idx_alerts_metrics ON customer_alerts USING GIN (metrics);

-- Enable Row Level Security
ALTER TABLE customer_alerts ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (adjust based on your auth setup)
-- Allow all operations for authenticated users
CREATE POLICY "Allow all operations for authenticated users" 
ON customer_alerts 
FOR ALL 
USING (true) 
WITH CHECK (true);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_alerts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_update_alerts_timestamp ON customer_alerts;
CREATE TRIGGER trigger_update_alerts_timestamp
    BEFORE UPDATE ON customer_alerts
    FOR EACH ROW
    EXECUTE FUNCTION update_alerts_updated_at();

-- Create view for active alerts with summary stats
CREATE OR REPLACE VIEW active_alerts_summary AS
SELECT 
    COUNT(*) as total_active,
    COUNT(*) FILTER (WHERE priority = 'HIGH') as high_priority,
    COUNT(*) FILTER (WHERE priority = 'MEDIUM') as medium_priority,
    COUNT(*) FILTER (WHERE priority = 'LOW') as low_priority,
    alert_type,
    COUNT(*) as count_by_type
FROM customer_alerts
WHERE status = 'active'
GROUP BY alert_type;

-- Add comments for documentation
COMMENT ON TABLE customer_alerts IS 'Stores customer alerts for pattern disruptions, at-risk customers, and other business intelligence';
COMMENT ON COLUMN customer_alerts.alert_type IS 'Type of alert: PATTERN_DISRUPTION, HIGH_VALUE_AT_RISK, DORMANT_CUSTOMER, etc.';
COMMENT ON COLUMN customer_alerts.priority IS 'Alert priority level: HIGH, MEDIUM, LOW';
COMMENT ON COLUMN customer_alerts.status IS 'Current status: active, dismissed, actioned, resolved';
COMMENT ON COLUMN customer_alerts.metrics IS 'Alert-specific metrics stored as JSON (e.g., days_since_last_order, lifetime_value)';
COMMENT ON COLUMN customer_alerts.first_detected_at IS 'When this specific alert was first detected for this company';
COMMENT ON COLUMN customer_alerts.last_detected_at IS 'When this alert was last confirmed during analysis';

-- Grant permissions (adjust as needed)
-- GRANT ALL ON customer_alerts TO authenticated;
-- GRANT USAGE, SELECT ON SEQUENCE customer_alerts_id_seq TO authenticated;

