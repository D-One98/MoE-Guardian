-- ============================================================================
-- MoE-GUARDIAN — Migration 001: Organization Memberships & PostgreSQL RLS
-- ============================================================================

CREATE TABLE IF NOT EXISTS organization_memberships (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    org_id VARCHAR(64) NOT NULL,
    role VARCHAR(64) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at_utc VARCHAR(64) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_org_memberships_user_org
    ON organization_memberships (user_id, org_id);

-- Enable Row-Level Security (RLS) Defence-in-Depth across tenant-scoped tables
ALTER TABLE brand_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE approved_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_palettes ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_ingestion_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_snapshots ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_brand_rules ON brand_rules;
CREATE POLICY tenant_isolation_brand_rules ON brand_rules
    USING (org_id = COALESCE(NULLIF(current_setting('app.current_org_id', true), ''), (auth.jwt() ->> 'org_id')));

DROP POLICY IF EXISTS tenant_isolation_approved_facts ON approved_facts;
CREATE POLICY tenant_isolation_approved_facts ON approved_facts
    USING (org_id = COALESCE(NULLIF(current_setting('app.current_org_id', true), ''), (auth.jwt() ->> 'org_id')));

DROP POLICY IF EXISTS tenant_isolation_brand_palettes ON brand_palettes;
CREATE POLICY tenant_isolation_brand_palettes ON brand_palettes
    USING (org_id = COALESCE(NULLIF(current_setting('app.current_org_id', true), ''), (auth.jwt() ->> 'org_id')));

DROP POLICY IF EXISTS tenant_isolation_ingestion_batches ON brand_ingestion_batches;
CREATE POLICY tenant_isolation_ingestion_batches ON brand_ingestion_batches
    USING (org_id = COALESCE(NULLIF(current_setting('app.current_org_id', true), ''), (auth.jwt() ->> 'org_id')));

DROP POLICY IF EXISTS tenant_isolation_audit_records ON audit_records;
CREATE POLICY tenant_isolation_audit_records ON audit_records
    USING (org_id = COALESCE(NULLIF(current_setting('app.current_org_id', true), ''), (auth.jwt() ->> 'org_id')));

DROP POLICY IF EXISTS tenant_isolation_review_snapshots ON review_snapshots;
CREATE POLICY tenant_isolation_review_snapshots ON review_snapshots
    USING (org_id = COALESCE(NULLIF(current_setting('app.current_org_id', true), ''), (auth.jwt() ->> 'org_id')));