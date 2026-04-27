-- PostgreSQL Schema for Blockchain Voting System
--
-- This schema provides immutable storage for:
-- 1. Voting tokens (one-time use enforcement)
-- 2. Blockchain votes (immutable voting records)
-- 3. Email-token mappings (temporary, deleted after voting)
-- 4. RSA keys for blind signatures
-- 5. System state and audit logs

-- ============================================================================
-- 1. RSA Keys Table (for blind signature scheme)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rsa_keys (
    id SERIAL PRIMARY KEY,
    key_type VARCHAR(20) NOT NULL,  -- 'private' or 'public'
    key_size INT NOT NULL,           -- 2048, 4096, etc.
    pem_data BYTEA NOT NULL,         -- PEM-encoded key
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(50) DEFAULT 'system',
    UNIQUE(key_type, key_size)
);

-- ============================================================================
-- 2. Voting Tokens Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS voting_tokens (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tokens_is_used ON voting_tokens(is_used);
CREATE INDEX IF NOT EXISTS idx_tokens_hash ON voting_tokens(token_hash);

-- ============================================================================
-- 3. Blockchain Votes Table (Immutable)
-- ============================================================================
CREATE TABLE IF NOT EXISTS blockchain_votes (
    id SERIAL PRIMARY KEY,
    vote_choice VARCHAR(255) NOT NULL,
    nonce BYTEA NOT NULL,
    signature BYTEA NOT NULL,
    vote_hash VARCHAR(64) NOT NULL,
    block_index INT UNIQUE NOT NULL,
    previous_hash VARCHAR(64),
    block_hash VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_votes_block_hash ON blockchain_votes(block_hash);
CREATE INDEX IF NOT EXISTS idx_votes_vote_hash ON blockchain_votes(vote_hash);
CREATE INDEX IF NOT EXISTS idx_votes_block_index ON blockchain_votes(block_index);
CREATE INDEX IF NOT EXISTS idx_votes_candidate ON blockchain_votes(vote_choice);

-- ============================================================================
-- 4. Email-Token Mapping (Temporary)
-- ============================================================================
CREATE TABLE IF NOT EXISTS email_token_mappings (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    token_hash VARCHAR(64) NOT NULL,
    sent_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_mappings_email ON email_token_mappings(email);
CREATE INDEX IF NOT EXISTS idx_email_mappings_token ON email_token_mappings(token_hash);

-- ============================================================================
-- 5. Voting State
-- ============================================================================
CREATE TABLE IF NOT EXISTS voting_state (
    id SERIAL PRIMARY KEY,
    state_key VARCHAR(50) UNIQUE NOT NULL,
    state_value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO voting_state (state_key, state_value) VALUES
    ('voting_started', 'false'),
    ('voting_stopped', 'false'),
    ('mode', 'secured'),
    ('total_tokens', '0'),
    ('total_votes', '0')
ON CONFLICT (state_key) DO NOTHING;

-- ============================================================================
-- 6. Audit Log
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    event_data TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at);

-- ============================================================================
-- 7. Genesis Block
-- ============================================================================
INSERT INTO blockchain_votes
    (vote_choice, nonce, signature, vote_hash, block_index, previous_hash, block_hash)
VALUES
    ('GENESIS', E'\\x00', E'\\x00', 'GENESIS_HASH', 0, 'NONE', 'GENESIS_HASH')
ON CONFLICT (block_hash) DO NOTHING;

-- ============================================================================
-- 8. Views
-- ============================================================================

CREATE OR REPLACE VIEW voting_results AS
SELECT
    vote_choice AS candidate,
    COUNT(*) AS vote_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM blockchain_votes WHERE block_index > 0), 2) AS percentage
FROM blockchain_votes
WHERE block_index > 0
GROUP BY vote_choice
ORDER BY vote_count DESC;

CREATE OR REPLACE VIEW voting_statistics AS
SELECT
    (SELECT COUNT(*) FROM blockchain_votes WHERE block_index > 0) AS total_votes,
    (SELECT COUNT(DISTINCT vote_choice) FROM blockchain_votes WHERE block_index > 0) AS candidates_count,
    (SELECT COUNT(*) FROM voting_tokens WHERE is_used = true) AS tokens_used,
    (SELECT COUNT(*) FROM voting_tokens WHERE is_used = false) AS tokens_remaining,
    (SELECT COUNT(*) FROM voting_tokens) AS tokens_total;

-- ============================================================================
-- 9. Immutability Functions
-- ============================================================================

CREATE OR REPLACE FUNCTION prevent_vote_deletion() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Cannot delete votes - blockchain is immutable';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION prevent_vote_update() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.vote_choice != OLD.vote_choice
        OR NEW.nonce != OLD.nonce
        OR NEW.signature != OLD.signature
        OR NEW.block_index != OLD.block_index
        OR NEW.previous_hash != OLD.previous_hash
    THEN
        RAISE EXCEPTION 'Cannot modify votes - blockchain is immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS prevent_vote_deletion_trigger ON blockchain_votes;
CREATE TRIGGER prevent_vote_deletion_trigger
BEFORE DELETE ON blockchain_votes
FOR EACH ROW
EXECUTE FUNCTION prevent_vote_deletion();

DROP TRIGGER IF EXISTS prevent_vote_update_trigger ON blockchain_votes;
CREATE TRIGGER prevent_vote_update_trigger
BEFORE UPDATE ON blockchain_votes
FOR EACH ROW
EXECUTE FUNCTION prevent_vote_update();
