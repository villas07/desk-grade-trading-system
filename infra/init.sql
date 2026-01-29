-- init.sql - PostgreSQL + TimescaleDB schema for desk-grade-ready

-- Extensions
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Base types / enums
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'risk_mode') THEN
        CREATE TYPE risk_mode AS ENUM ('NORMAL', 'DEGRADED', 'HALT');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
        CREATE TYPE job_status AS ENUM ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELLED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trade_state_enum') THEN
        CREATE TYPE trade_state_enum AS ENUM ('FLAT', 'ENTERED', 'MANAGED', 'EXITED');
    END IF;
END$$;

-- OHLCV hypertable
CREATE TABLE IF NOT EXISTS ohlcv (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol       TEXT        NOT NULL,
    ts           TIMESTAMPTZ NOT NULL,
    open         DOUBLE PRECISION NOT NULL,
    high         DOUBLE PRECISION NOT NULL,
    low          DOUBLE PRECISION NOT NULL,
    close        DOUBLE PRECISION NOT NULL,
    volume       DOUBLE PRECISION NOT NULL,
    timeframe    TEXT        NOT NULL DEFAULT '1m',
    source       TEXT        DEFAULT 'unknown'
);

SELECT create_hypertable('ohlcv', 'ts', if_not_exists => TRUE);

-- Constraint único para evitar duplicados (símbolo + timestamp + timeframe)
CREATE UNIQUE INDEX IF NOT EXISTS idx_ohlcv_unique ON ohlcv(symbol, ts, timeframe);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_ts ON ohlcv(symbol, ts DESC);

-- Live signals
CREATE TABLE IF NOT EXISTS signals_live (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol       TEXT        NOT NULL,
    ts           TIMESTAMPTZ NOT NULL,
    side         TEXT        NOT NULL, -- 'BUY' / 'SELL'
    strength     DOUBLE PRECISION,
    strategy_id  TEXT        NOT NULL,
    meta         JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_signals_live_symbol_ts ON signals_live(symbol, ts DESC);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol          TEXT        NOT NULL,
    side            TEXT        NOT NULL, -- BUY / SELL
    qty             DOUBLE PRECISION NOT NULL,
    price           DOUBLE PRECISION,
    order_type      TEXT        NOT NULL DEFAULT 'MARKET',
    status          TEXT        NOT NULL DEFAULT 'NEW', -- NEW/FILLED/CANCELLED
    strategy_id     TEXT        NOT NULL,
    paper_trade     BOOLEAN     NOT NULL DEFAULT TRUE,
    parent_order_id UUID,
    meta            JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_orders_symbol_ts ON orders(symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Fills
CREATE TABLE IF NOT EXISTS fills (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id    UUID        NOT NULL REFERENCES orders(id),
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol      TEXT        NOT NULL,
    side        TEXT        NOT NULL,
    qty         DOUBLE PRECISION NOT NULL,
    price       DOUBLE PRECISION NOT NULL,
    fee         DOUBLE PRECISION DEFAULT 0,
    meta        JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_fills_symbol_ts ON fills(symbol, ts DESC);

-- Positions
CREATE TABLE IF NOT EXISTS positions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol          TEXT        NOT NULL,
    qty             DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_price       DOUBLE PRECISION NOT NULL DEFAULT 0,
    realized_pnl    DOUBLE PRECISION NOT NULL DEFAULT 0,
    unrealized_pnl  DOUBLE PRECISION NOT NULL DEFAULT 0,
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    strategy_id     TEXT        NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_positions_symbol_strategy ON positions(symbol, strategy_id);

-- Cash balances
CREATE TABLE IF NOT EXISTS cash_balances (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    currency     TEXT        NOT NULL,
    balance      DOUBLE PRECISION NOT NULL,
    available    DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cash_balances_ts ON cash_balances(ts DESC);

-- Risk budgets
CREATE TABLE IF NOT EXISTS risk_budgets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id     TEXT        NOT NULL,
    max_drawdown    DOUBLE PRECISION NOT NULL,
    daily_loss_limit DOUBLE PRECISION NOT NULL,
    weekly_loss_limit DOUBLE PRECISION NOT NULL,
    vol_target      DOUBLE PRECISION,
    sector_cap      DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_risk_budgets_strategy ON risk_budgets(strategy_id);

-- Risk state
CREATE TABLE IF NOT EXISTS risk_state (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mode            risk_mode  NOT NULL DEFAULT 'NORMAL',
    reason          TEXT,
    dd_pct          DOUBLE PRECISION,
    daily_pnl       DOUBLE PRECISION,
    weekly_pnl      DOUBLE PRECISION,
    correlation_flag BOOLEAN DEFAULT FALSE,
    reconciliation_flag BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_risk_state_ts ON risk_state(ts DESC);

-- Risk events
CREATE TABLE IF NOT EXISTS risk_events (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type  TEXT        NOT NULL,
    severity    TEXT        NOT NULL,
    description TEXT,
    meta        JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_risk_events_ts ON risk_events(ts DESC);

-- Exposure snapshots
CREATE TABLE IF NOT EXISTS exposure_snapshots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol          TEXT        NOT NULL,
    sector          TEXT,
    gross_exposure  DOUBLE PRECISION NOT NULL,
    net_exposure    DOUBLE PRECISION NOT NULL,
    leverage        DOUBLE PRECISION,
    strategy_id     TEXT        NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_exposure_symbol_ts ON exposure_snapshots(symbol, ts DESC);

-- Correlation state
CREATE TABLE IF NOT EXISTS correlation_state (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol_pair     TEXT        NOT NULL,
    window_minutes  INTEGER     NOT NULL,
    correlation     DOUBLE PRECISION NOT NULL,
    meta            JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_correlation_state_ts ON correlation_state(ts DESC);

-- ATR cache
CREATE TABLE IF NOT EXISTS atr_cache (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol          TEXT        NOT NULL,
    timeframe       TEXT        NOT NULL,
    ts              TIMESTAMPTZ NOT NULL,
    atr             DOUBLE PRECISION NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_atr_cache_symbol_tf_ts ON atr_cache(symbol, timeframe, ts);

-- Trade state
CREATE TABLE IF NOT EXISTS trade_state (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol          TEXT        NOT NULL,
    strategy_id     TEXT        NOT NULL,
    state           trade_state_enum NOT NULL DEFAULT 'FLAT',
    entry_ts        TIMESTAMPTZ,
    entry_price     DOUBLE PRECISION,
    qty             DOUBLE PRECISION DEFAULT 0,
    stop_price      DOUBLE PRECISION,
    tp1_price       DOUBLE PRECISION,
    tp2_price       DOUBLE PRECISION,
    trailing_price  DOUBLE PRECISION,
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_trade_state_symbol_strategy ON trade_state(symbol, strategy_id);

-- Trade events
CREATE TABLE IF NOT EXISTS trade_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol          TEXT        NOT NULL,
    strategy_id     TEXT        NOT NULL,
    event_type      TEXT        NOT NULL,
    description     TEXT,
    meta            JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_trade_events_symbol_ts ON trade_events(symbol, ts DESC);

-- Trade journal (R, MAE, MFE)
CREATE TABLE IF NOT EXISTS trade_journal (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol          TEXT        NOT NULL,
    strategy_id     TEXT        NOT NULL,
    entry_ts        TIMESTAMPTZ NOT NULL,
    exit_ts         TIMESTAMPTZ NOT NULL,
    entry_price     DOUBLE PRECISION NOT NULL,
    exit_price      DOUBLE PRECISION NOT NULL,
    qty             DOUBLE PRECISION NOT NULL,
    r               DOUBLE PRECISION NOT NULL,
    pnl_r           DOUBLE PRECISION NOT NULL,
    mae             DOUBLE PRECISION,
    mfe             DOUBLE PRECISION,
    meta            JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_trade_journal_symbol_ts ON trade_journal(symbol, exit_ts DESC);

-- Position lifecycle
CREATE TABLE IF NOT EXISTS position_lifecycle (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol          TEXT        NOT NULL,
    strategy_id     TEXT        NOT NULL,
    lifecycle_state TEXT        NOT NULL,
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    meta            JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_position_lifecycle_symbol_ts ON position_lifecycle(symbol, ts DESC);

-- Job queue
CREATE TABLE IF NOT EXISTS job_queue (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scheduled_for   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    job_type        TEXT        NOT NULL, -- 'RISK_CYCLE', 'KILL_SWITCH', etc.
    status          job_status  NOT NULL DEFAULT 'PENDING',
    last_update     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attempts        INTEGER     NOT NULL DEFAULT 0,
    payload         JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_job_queue_status_scheduled ON job_queue(status, scheduled_for);

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level           TEXT        NOT NULL, -- INFO/WARN/ERROR
    source          TEXT        NOT NULL,
    message         TEXT        NOT NULL,
    meta            JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts DESC);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor           TEXT        NOT NULL,
    action          TEXT        NOT NULL,
    entity_type     TEXT        NOT NULL,
    entity_id       TEXT,
    details         JSONB       DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log(ts DESC);

-- Seed mínimo de cash balance
INSERT INTO cash_balances (currency, balance, available)
SELECT 'USD', 10000, 10000
WHERE NOT EXISTS (SELECT 1 FROM cash_balances);

