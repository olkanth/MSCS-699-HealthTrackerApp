
CREATE DATABASE dbHealthTracker;
-- \c dbHealthTracker
-- =====================================================================
-- users: login + role for every person who touches the system
-- =====================================================================
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_users_role CHECK (role IN ('patient', 'provider', 'admin', 'it_staff'))
);

-- =====================================================================
-- providers: doctors / nurses / care coordinators
-- =====================================================================
CREATE TABLE IF NOT EXISTS providers (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    specialty       VARCHAR(100),
    npi_number      VARCHAR(20) UNIQUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- patients: core patient profile
-- =====================================================================
CREATE TABLE IF NOT EXISTS patients (
    id                   SERIAL PRIMARY KEY,
    user_id              INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    first_name           VARCHAR(100) NOT NULL,
    last_name            VARCHAR(100) NOT NULL,
    date_of_birth        DATE NOT NULL,
    gender               VARCHAR(20),
    mrn                  VARCHAR(20) NOT NULL UNIQUE,
    primary_provider_id  INTEGER REFERENCES providers(id) ON DELETE SET NULL,
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_patients_dob CHECK (date_of_birth <= CURRENT_DATE)
);

-- =====================================================================
-- vital_signs: time-stamped readings collected per patient
-- =====================================================================
CREATE TABLE IF NOT EXISTS vital_signs (
    id             SERIAL PRIMARY KEY,
    patient_id     INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    heart_rate     SMALLINT,
    systolic_bp    SMALLINT,
    diastolic_bp   SMALLINT,
    spo2           SMALLINT,
    temperature    NUMERIC(4,1),
    recorded_at    TIMESTAMP NOT NULL,
    source         VARCHAR(50) DEFAULT 'device',
    CONSTRAINT chk_vitals_hr CHECK (heart_rate IS NULL OR heart_rate BETWEEN 20 AND 300),
    CONSTRAINT chk_vitals_spo2 CHECK (spo2 IS NULL OR spo2 BETWEEN 0 AND 100),
    CONSTRAINT chk_vitals_bp CHECK (
        systolic_bp IS NULL OR diastolic_bp IS NULL OR systolic_bp > diastolic_bp
    )
);
CREATE INDEX IF NOT EXISTS idx_vitals_patient_time ON vital_signs (patient_id, recorded_at DESC);

-- =====================================================================
-- activity_data: step counts / movement, time-stamped per patient
-- =====================================================================
CREATE TABLE IF NOT EXISTS activity_data (
    id              SERIAL PRIMARY KEY,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    steps           INTEGER,
    active_minutes  INTEGER,
    distance_km     NUMERIC(5,2),
    recorded_at     TIMESTAMP NOT NULL,
    source          VARCHAR(50) DEFAULT 'device',
    CONSTRAINT chk_activity_steps CHECK (steps IS NULL OR steps >= 0)
);
CREATE INDEX IF NOT EXISTS idx_activity_patient_time ON activity_data (patient_id, recorded_at DESC);

-- =====================================================================
-- alert_thresholds: per-patient custom thresholds (Phase 4 depends on this)
-- =====================================================================
CREATE TABLE IF NOT EXISTS alert_thresholds (
    id           SERIAL PRIMARY KEY,
    patient_id   INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    metric_name  VARCHAR(50) NOT NULL,
    min_value    NUMERIC(6,2),
    max_value    NUMERIC(6,2),
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_threshold_patient_metric UNIQUE (patient_id, metric_name),
    CONSTRAINT chk_threshold_range CHECK (
        min_value IS NULL OR max_value IS NULL OR min_value < max_value
    )
);

-- =====================================================================
-- alerts: generated when a reading crosses a threshold / pattern rule
-- =====================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id               SERIAL PRIMARY KEY,
    patient_id       INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    metric_name      VARCHAR(50) NOT NULL,
    value            NUMERIC(6,2) NOT NULL,
    severity         VARCHAR(10) NOT NULL,
    status           VARCHAR(15) NOT NULL DEFAULT 'open',
    triggered_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    acknowledged_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at  TIMESTAMP,
    resolved_at      TIMESTAMP,
    CONSTRAINT chk_alert_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_alert_status CHECK (status IN ('open', 'acknowledged', 'resolved'))
);
CREATE INDEX IF NOT EXISTS idx_alerts_patient_status ON alerts (patient_id, status);

-- =====================================================================
-- risk_scores: Phase 5 risk assessment output, kept over time for trends
-- =====================================================================
CREATE TABLE IF NOT EXISTS risk_scores (
    id                     SERIAL PRIMARY KEY,
    patient_id             INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    score                  NUMERIC(5,2) NOT NULL,
    risk_level             VARCHAR(10) NOT NULL,
    contributing_factors   TEXT,
    calculated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_risk_level CHECK (risk_level IN ('low', 'medium', 'high'))
);
CREATE INDEX IF NOT EXISTS idx_risk_patient_time ON risk_scores (patient_id, calculated_at DESC);

-- =====================================================================
-- audit_log: HIPAA-style access/change log (see proposal, HIPAA section)
-- =====================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action       VARCHAR(20) NOT NULL,
    table_name   VARCHAR(50) NOT NULL,
    record_id    INTEGER NOT NULL,
    occurred_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_audit_action CHECK (action IN ('create', 'read', 'update', 'delete'))
);
CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_log (table_name, record_id);


-- =====================================================================
-- SAMPLE DATA
-- Guarded so this whole block only runs once: if the seed provider
-- 'dr.patel' already exists, we assume the rest of the sample data was
-- already inserted on a previous run and skip it, rather than creating
-- duplicate rows every time this script is re-run.
-- =====================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'dr.patel') THEN

        -- password for every seeded user below is "welcome@123" (bcrypt hash, matches app.auth.hash_password)
        INSERT INTO users (username, email, password_hash, role) VALUES
            ('dr.patel',   'r.patel@healthtrack.example',    '$2b$12$j4aDMK209ZhOwcagyzHxQ.mVZhahIkgvgHRW7OTib38bBmKojHLzC', 'provider'),
            ('dr.nguyen',  'l.nguyen@healthtrack.example',   '$2b$12$j4aDMK209ZhOwcagyzHxQ.mVZhahIkgvgHRW7OTib38bBmKojHLzC', 'provider'),
            ('jsmith',     'j.smith@example.com',            '$2b$12$j4aDMK209ZhOwcagyzHxQ.mVZhahIkgvgHRW7OTib38bBmKojHLzC', 'patient'),
            ('mgarcia',    'm.garcia@example.com',           '$2b$12$j4aDMK209ZhOwcagyzHxQ.mVZhahIkgvgHRW7OTib38bBmKojHLzC', 'patient'),
            ('admin1',     'admin@healthtrack.example',      '$2b$12$j4aDMK209ZhOwcagyzHxQ.mVZhahIkgvgHRW7OTib38bBmKojHLzC', 'admin'),
            ('it.support', 'it@healthtrack.example',         '$2b$12$j4aDMK209ZhOwcagyzHxQ.mVZhahIkgvgHRW7OTib38bBmKojHLzC', 'it_staff');

        INSERT INTO providers (user_id, first_name, last_name, specialty, npi_number)
        SELECT id, 'Reena', 'Patel', 'Cardiology', '1000000001' FROM users WHERE username = 'dr.patel'
        UNION ALL
        SELECT id, 'Long', 'Nguyen', 'Endocrinology', '1000000002' FROM users WHERE username = 'dr.nguyen';

        INSERT INTO patients (user_id, first_name, last_name, date_of_birth, gender, mrn, primary_provider_id)
        SELECT u.id, 'John', 'Smith', DATE '1958-04-12', 'male', 'MRN-00123', p.id
        FROM users u, providers p WHERE u.username = 'jsmith' AND p.npi_number = '1000000001'
        UNION ALL
        SELECT u.id, 'Maria', 'Garcia', DATE '1972-11-03', 'female', 'MRN-00124', p.id
        FROM users u, providers p WHERE u.username = 'mgarcia' AND p.npi_number = '1000000002';

        INSERT INTO vital_signs (patient_id, heart_rate, systolic_bp, diastolic_bp, spo2, temperature, recorded_at, source)
        SELECT id, 78, 138, 88, 96, 98.4, NOW() - INTERVAL '2 hours', 'device' FROM patients WHERE mrn = 'MRN-00123'
        UNION ALL
        SELECT id, 82, 142, 90, 95, 98.6, NOW() - INTERVAL '1 day',   'device' FROM patients WHERE mrn = 'MRN-00123'
        UNION ALL
        SELECT id, 74, 118, 76, 98, 98.1, NOW() - INTERVAL '3 hours', 'device' FROM patients WHERE mrn = 'MRN-00124';

        INSERT INTO activity_data (patient_id, steps, active_minutes, distance_km, recorded_at, source)
        SELECT id, 3200, 22, 2.1, NOW() - INTERVAL '1 day', 'device' FROM patients WHERE mrn = 'MRN-00123'
        UNION ALL
        SELECT id, 6100, 41, 4.3, NOW() - INTERVAL '1 day', 'device' FROM patients WHERE mrn = 'MRN-00124';

        INSERT INTO alert_thresholds (patient_id, metric_name, min_value, max_value)
        SELECT id, 'systolic_bp', 90, 140 FROM patients WHERE mrn = 'MRN-00123'
        UNION ALL
        SELECT id, 'heart_rate',  50, 100 FROM patients WHERE mrn = 'MRN-00123'
        UNION ALL
        SELECT id, 'heart_rate',  50, 110 FROM patients WHERE mrn = 'MRN-00124';

        INSERT INTO alerts (patient_id, metric_name, value, severity, status, triggered_at)
        SELECT id, 'systolic_bp', 142, 'medium', 'open', NOW() - INTERVAL '1 day' FROM patients WHERE mrn = 'MRN-00123';

        INSERT INTO risk_scores (patient_id, score, risk_level, contributing_factors, calculated_at)
        SELECT id, 62.5, 'medium', '["elevated systolic BP trend", "low activity level"]', NOW() - INTERVAL '1 day'
        FROM patients WHERE mrn = 'MRN-00123';

        INSERT INTO audit_log (user_id, action, table_name, record_id)
        SELECT u.id, 'read', 'patients', p.id FROM users u, patients p WHERE u.username = 'dr.patel' AND p.mrn = 'MRN-00123'
        UNION ALL
        SELECT u.id, 'update', 'alert_thresholds', 1 FROM users u WHERE u.username = 'dr.patel';

    END IF;
END $$;