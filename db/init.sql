-- SEO Autopilot — PostgreSQL schema for canonical data store

-- Tenants (agencies)
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Clients (agency's clients)
CREATE TABLE IF NOT EXISTS clients (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    name        TEXT NOT NULL,
    sheet_url   TEXT,
    sheet_id    TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Sheet column → domain field mappings
CREATE TABLE IF NOT EXISTS sheet_mappings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    tab_name    TEXT NOT NULL DEFAULT 'Keywords',
    mappings    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(client_id, tab_name)
);

-- Versioned snapshots of sheet data
CREATE TABLE IF NOT EXISTS sheet_snapshots (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    tab_name    TEXT NOT NULL DEFAULT 'Keywords',
    source      TEXT NOT NULL CHECK (source IN ('upload', 'poll', 'webhook', 'csv_import')),
    data        JSONB NOT NULL,
    checksum    TEXT NOT NULL,
    row_count   INTEGER NOT NULL DEFAULT 0,
    user_id     UUID,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_client
    ON sheet_snapshots(client_id, created_at DESC);

-- Sync audit trail (immutable log)
CREATE TABLE IF NOT EXISTS sync_audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id),
    snapshot_id     UUID REFERENCES sheet_snapshots(id),
    action          TEXT NOT NULL CHECK (action IN ('import', 'reconcile', 'conflict', 'rollback', 'error')),
    rows_inserted   INTEGER DEFAULT 0,
    rows_updated    INTEGER DEFAULT 0,
    rows_deleted    INTEGER DEFAULT 0,
    conflicts       JSONB,
    error           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Pending sync conflicts for manual resolution
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id),
    row_key         TEXT NOT NULL,
    sheet_value     JSONB,
    postgres_value  JSONB,
    resolution      TEXT DEFAULT 'pending' CHECK (resolution IN ('pending', 'accepted_sheet', 'accepted_db', 'manual')),
    resolved_at     TIMESTAMPTZ,
    resolved_by     UUID,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Per-client sync state (last poll, staleness)
CREATE TABLE IF NOT EXISTS sync_state (
    client_id        UUID PRIMARY KEY REFERENCES clients(id) ON DELETE CASCADE,
    last_snapshot_id UUID REFERENCES sheet_snapshots(id),
    last_polled_at   TIMESTAMPTZ,
    is_stale         BOOLEAN DEFAULT false,
    next_poll_at     TIMESTAMPTZ DEFAULT now()
);

-- Canonical ranking data
CREATE TABLE IF NOT EXISTS client_rankings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    keyword     TEXT NOT NULL,
    position    INTEGER,
    target_url  TEXT,
    change      INTEGER,
    source      TEXT DEFAULT 'sheet',
    updated_at  TIMESTAMPTZ DEFAULT now(),
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(client_id, keyword)
);

CREATE INDEX IF NOT EXISTS idx_rankings_client
    ON client_rankings(client_id, keyword);
