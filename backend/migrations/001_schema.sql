-- ============================================================
-- AI法律助手 v1.0 — 数据库初始化 DDL
-- ============================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id               BIGSERIAL PRIMARY KEY,
    username         VARCHAR(50)  NOT NULL,
    password_hash    VARCHAR(255) NOT NULL,
    phone            VARCHAR(20),
    phone_hash       VARCHAR(64),
    phone_encrypted  TEXT,
    nickname         VARCHAR(50)  DEFAULT '法律助手用户',
    avatar_url       VARCHAR(500),
    privacy_save_history BOOLEAN DEFAULT TRUE,
    status           SMALLINT     DEFAULT 1,
    created_at       TIMESTAMP    DEFAULT NOW(),
    updated_at       TIMESTAMP    DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 会话表
CREATE TABLE IF NOT EXISTS sessions (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT       NOT NULL REFERENCES users(id),
    title         VARCHAR(200) DEFAULT '法律咨询',
    category      VARCHAR(50),
    msg_count     INT          DEFAULT 0,
    status        SMALLINT     DEFAULT 1,
    created_at    TIMESTAMP    DEFAULT NOW(),
    updated_at    TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_category ON sessions(category);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id            BIGSERIAL PRIMARY KEY,
    session_id    BIGINT       NOT NULL REFERENCES sessions(id),
    role          VARCHAR(10)  NOT NULL,
    content       TEXT         NOT NULL,
    content_type  VARCHAR(20)  DEFAULT 'text',
    tokens        INT,
    is_streaming  BOOLEAN      DEFAULT FALSE,
    status        SMALLINT     DEFAULT 1,
    created_at    TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, created_at);

-- 法条引用关联表
CREATE TABLE IF NOT EXISTS message_law_refs (
    id            BIGSERIAL PRIMARY KEY,
    message_id    BIGINT       NOT NULL REFERENCES messages(id),
    law_name      VARCHAR(200) NOT NULL,
    article_num   VARCHAR(50),
    law_text      TEXT,
    source        VARCHAR(200),
    chunk_id      VARCHAR(100),
    relevance     FLOAT,
    created_at    TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_law_refs_message_id ON message_law_refs(message_id);

-- 审核日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT       REFERENCES users(id),
    action        VARCHAR(50)  NOT NULL,
    target_type   VARCHAR(30)  NOT NULL,
    target_id     BIGINT,
    detail        TEXT,
    operator_id   BIGINT,
    ip            VARCHAR(50),
    created_at    TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Token消耗统计表
CREATE TABLE IF NOT EXISTS token_usage (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT       REFERENCES users(id),
    session_id    BIGINT       REFERENCES sessions(id),
    message_id    BIGINT       REFERENCES messages(id),
    model         VARCHAR(50)  NOT NULL,
    input_tokens  INT          DEFAULT 0,
    output_tokens INT          DEFAULT 0,
    created_at    TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_usage_user_id ON token_usage(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_session ON token_usage(session_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_date ON token_usage(DATE(created_at));

-- 短信验证码表
CREATE TABLE IF NOT EXISTS sms_codes (
    id            BIGSERIAL PRIMARY KEY,
    phone         VARCHAR(20)  NOT NULL,
    code          VARCHAR(10)  NOT NULL,
    used          BOOLEAN      DEFAULT FALSE,
    expires_at    TIMESTAMP    NOT NULL,
    created_at    TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sms_codes_phone ON sms_codes(phone, created_at DESC);
