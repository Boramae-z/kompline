-- 001_scan_tables.sql
-- Scan 요청 테이블
CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    repo_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN ('QUEUED', 'PROCESSING', 'REPORT_GENERATING', 'COMPLETED', 'FAILED')),
    report_url TEXT,
    report_markdown TEXT
);

-- Scan과 Document 연결 테이블
CREATE TABLE IF NOT EXISTS scan_documents (
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    document_id UUID NOT NULL,
    PRIMARY KEY (scan_id, document_id)
);

-- 개별 검증 결과 테이블
CREATE TABLE IF NOT EXISTS scan_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    compliance_item_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PASS', 'FAIL', 'ERROR')),
    reasoning TEXT,
    evidence TEXT,
    worker_id TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
CREATE INDEX IF NOT EXISTS idx_scan_results_status ON scan_results(status);
CREATE INDEX IF NOT EXISTS idx_scan_results_scan_id ON scan_results(scan_id);
