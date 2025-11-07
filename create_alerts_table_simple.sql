-- Simple customer alerts table creation
-- Copy and paste this entire file into Supabase SQL Editor

CREATE TABLE IF NOT EXISTS customer_alerts (
    id BIGSERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    public_name TEXT,
    email TEXT,
    
    alert_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    status TEXT NOT NULL DEFAULT 'active',
    actioned_at TIMESTAMP WITH TIME ZONE,
    actioned_by TEXT,
    dismissed_at TIMESTAMP WITH TIME ZONE,
    dismissed_by TEXT,
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    first_detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_alerts_company_id ON customer_alerts(company_id);
CREATE INDEX idx_alerts_type ON customer_alerts(alert_type);
CREATE INDEX idx_alerts_priority ON customer_alerts(priority);
CREATE INDEX idx_alerts_status ON customer_alerts(status);
CREATE INDEX idx_alerts_active_priority ON customer_alerts(status, priority, created_at DESC) WHERE status = 'active';

ALTER TABLE customer_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations for authenticated users" 
ON customer_alerts 
FOR ALL 
USING (true) 
WITH CHECK (true);

-- Done! Your alerts table is ready.

