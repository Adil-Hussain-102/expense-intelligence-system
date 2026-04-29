-- schema.sql

DROP TABLE IF EXISTS forecasts CASCADE;
DROP TABLE IF EXISTS anomalies CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- Categories table
CREATE TABLE categories (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) UNIQUE NOT NULL,
    color_hex  VARCHAR(7) DEFAULT '#888888',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Transactions table
CREATE TABLE transactions (
    id            SERIAL PRIMARY KEY,
    date          DATE NOT NULL,
    description   TEXT NOT NULL,
    amount        NUMERIC(12, 2) NOT NULL,
    category_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    is_anomaly    BOOLEAN DEFAULT FALSE,
    confidence    FLOAT,
    raw_text      TEXT,
    uploaded_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_category ON transactions(category_id);

-- Anomalies table
CREATE TABLE anomalies (
    id             SERIAL PRIMARY KEY,
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    reason         TEXT,
    severity       VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high')),
    detected_at    TIMESTAMP DEFAULT NOW()
);

-- Forecasts table
CREATE TABLE forecasts (
    id               SERIAL PRIMARY KEY,
    category_id      INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    forecast_month   DATE NOT NULL,
    predicted_amount NUMERIC(12, 2),
    actual_amount    NUMERIC(12, 2),
    created_at       TIMESTAMP DEFAULT NOW(),
    UNIQUE(category_id, forecast_month)
);

-- Seed categories
INSERT INTO categories (name, color_hex) VALUES
    ('Food & Dining',    '#FF6B6B'),
    ('Transport',        '#4ECDC4'),
    ('Utilities',        '#45B7D1'),
    ('Rent & Housing',   '#96CEB4'),
    ('Shopping',         '#FFEAA7'),
    ('Healthcare',       '#DDA0DD'),
    ('Entertainment',    '#98D8C8'),
    ('Education',        '#F7DC6F'),
    ('Salary & Income',  '#82E0AA'),
    ('Transfer',         '#AEB6BF'),
    ('Other',            '#D7DBDD');