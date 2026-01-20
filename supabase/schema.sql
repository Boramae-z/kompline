
-- Create Scans Table
CREATE TABLE IF NOT EXISTS scans (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    repo_url TEXT NOT NULL,
    status TEXT DEFAULT 'QUEUED', -- QUEUED, PROCESSING, COMPLETED, FAILED
    report_url TEXT,
    artifact_type TEXT DEFAULT 'code_repository'
);

-- Create Scan Results Table
CREATE TABLE IF NOT EXISTS scan_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    compliance_item_id BIGINT REFERENCES compliance_items(id), -- Assuming compliance_items.id is BIGINT/INT
    status TEXT DEFAULT 'PENDING', -- PENDING, PASS, FAIL, ERROR
    reasoning TEXT,
    evidence TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Junction Table for Scans <-> Documents
CREATE TABLE IF NOT EXISTS scan_documents (
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    document_id BIGINT REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (scan_id, document_id)
);

-- [NEW] Repositories Table
CREATE TABLE IF NOT EXISTS repositories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    description TEXT,
    last_scan_at TIMESTAMPTZ
);

-- Realtime
alter publication supabase_realtime add table scans;
alter publication supabase_realtime add table scan_results;
-- alter publication supabase_realtime add table repositories; -- Optional
