-- Create trips table for route planning
CREATE TABLE IF NOT EXISTS trips (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    trip_date DATE NOT NULL,
    start_location VARCHAR(500) NOT NULL,
    start_time TIME NOT NULL,
    start_lat DECIMAL(10, 8),
    start_lng DECIMAL(11, 8),
    status VARCHAR(50) DEFAULT 'planned',
    total_distance_km DECIMAL(10, 2),
    estimated_duration_minutes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    notes TEXT
);

-- Create trip_stops table for individual stops on a trip
CREATE TABLE IF NOT EXISTS trip_stops (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    company_id VARCHAR(255),
    company_name VARCHAR(500) NOT NULL,
    address VARCHAR(500),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    stop_order INTEGER NOT NULL,
    estimated_arrival TIME,
    actual_arrival TIME,
    duration_minutes INTEGER DEFAULT 30,
    notes TEXT,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_trips_date ON trips(trip_date);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trip_stops_trip_id ON trip_stops(trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_stops_order ON trip_stops(trip_id, stop_order);

-- Enable Row Level Security
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_stops ENABLE ROW LEVEL SECURITY;

-- Create policies for trips (allow all operations for now - adjust based on your auth)
CREATE POLICY "Enable read access for all users" ON trips
    FOR SELECT USING (true);

CREATE POLICY "Enable insert access for all users" ON trips
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update access for all users" ON trips
    FOR UPDATE USING (true);

CREATE POLICY "Enable delete access for all users" ON trips
    FOR DELETE USING (true);

-- Create policies for trip_stops
CREATE POLICY "Enable read access for all users" ON trip_stops
    FOR SELECT USING (true);

CREATE POLICY "Enable insert access for all users" ON trip_stops
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update access for all users" ON trip_stops
    FOR UPDATE USING (true);

CREATE POLICY "Enable delete access for all users" ON trip_stops
    FOR DELETE USING (true);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_trips_updated_at BEFORE UPDATE ON trips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

