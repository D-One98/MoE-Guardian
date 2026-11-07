-- ============================================================================
-- MoE-GUARDIAN — Migration 002: Child-Table & Membership RLS Hardening
-- ============================================================================

ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_findings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_org_memberships ON organization_memberships;
CREATE POLICY tenant_isolation_org_memberships ON organization_memberships
    USING (
        org_id = COALESCE(NULLIF(current_setting('app.current_org_id', true), ''), (auth.jwt() ->> 'org_id'))
        OR user_id = COALESCE(NULLIF(current_setting('app.current_user_id', true), ''), (auth.jwt() ->> 'sub'))
    );

DROP POLICY IF EXISTS tenant_isolation_audit_findings ON audit_findings;
CREATE POLICY tenant_isolation_audit_findings ON audit_findings
    USING (
        EXISTS (
            SELECT 1
            FROM audit_records ar
            WHERE ar.audit_id = audit_findings.audit_id
              AND ar.org_id = COALESCE(NULLIF(current_setting('app.current_org_id', true), ''), (auth.jwt() ->> 'org_id'))
        )
    );