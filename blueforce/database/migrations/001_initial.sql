CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS laboratories (
    id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS virtual_devices (
    id TEXT PRIMARY KEY, lab_id TEXT NOT NULL REFERENCES laboratories(id) ON DELETE CASCADE,
    name TEXT NOT NULL, device_type TEXT NOT NULL, signal_dbm INTEGER NOT NULL,
    connected INTEGER NOT NULL, pairing TEXT NOT NULL, discoverable INTEGER NOT NULL,
    encrypted INTEGER NOT NULL, battery INTEGER NOT NULL, risk TEXT NOT NULL,
    history_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS simulation_sessions (
    id TEXT PRIMARY KEY, lab_id TEXT NOT NULL REFERENCES laboratories(id),
    scenario TEXT NOT NULL, seed INTEGER, status TEXT NOT NULL,
    started_at TEXT NOT NULL, ended_at TEXT, summary_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS simulation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES simulation_sessions(id),
    timestamp TEXT NOT NULL, event_type TEXT NOT NULL, severity TEXT NOT NULL,
    message TEXT NOT NULL, data_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS security_alerts (
    id TEXT PRIMARY KEY, session_id TEXT, lab_id TEXT NOT NULL,
    timestamp TEXT NOT NULL, rule TEXT NOT NULL, severity TEXT NOT NULL,
    confidence REAL NOT NULL, explanation TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0,
    data_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY, lab_id TEXT NOT NULL, title TEXT NOT NULL,
    classification TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL, timeline_json TEXT NOT NULL DEFAULT '[]',
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY, lab_id TEXT NOT NULL, format TEXT NOT NULL,
    path TEXT NOT NULL, created_at TEXT NOT NULL, summary_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS configuration_profiles (
    id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, config_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_devices_lab ON virtual_devices(lab_id);
CREATE INDEX IF NOT EXISTS idx_events_session ON simulation_events(session_id);
CREATE INDEX IF NOT EXISTS idx_alerts_lab ON security_alerts(lab_id);
