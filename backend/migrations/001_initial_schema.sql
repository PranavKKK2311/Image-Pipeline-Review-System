"""
Database schema for SKU and image validation pipeline.
Postgres 12+

Run with:
    psql -U postgres -f backend/migrations/001_initial_schema.sql
"""

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enum types
CREATE TYPE image_state AS ENUM ('pending', 'auto_accepted', 'auto_rejected', 'human_accepted', 'human_rejected', 'manual_uploaded');
CREATE TYPE review_status AS ENUM ('pending', 'in_progress', 'accepted', 'rejected', 'requires_edit');

-- ============================================================================
-- PRODUCTS TABLE (Problem 1: Unique SKU)
-- ============================================================================
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    vendor_short VARCHAR(10) NOT NULL UNIQUE,  -- e.g., "VEND", "BRIT", "ACME"
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    vendor_id INT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    vendor_code VARCHAR(255) NOT NULL,                   -- Original code from vendor: "BRIT10G"
    canonical_sku VARCHAR(64) NOT NULL UNIQUE,          -- Final unique SKU: "VEND-BRIT10G" or "VEND-BRIT10G-3F4E1A"
    product_name VARCHAR(500),
    description TEXT,
    category VARCHAR(255),
    price DECIMAL(12, 2),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_vendor_code_per_vendor UNIQUE(vendor_id, vendor_code)
);

-- Unique index on canonical_sku to prevent collisions
CREATE UNIQUE INDEX idx_products_canonical_sku ON products (canonical_sku);
-- Fast lookup by vendor_code
CREATE INDEX idx_products_vendor_code ON products (vendor_id, vendor_code);

-- ============================================================================
-- PRODUCT IMAGES TABLE (Problem 2: Image Validation)
-- ============================================================================
CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url VARCHAR(2048) NOT NULL,               -- URL to image in CDN or object storage
    image_hash VARCHAR(64),                         -- SHA256 hash for deduplication
    state image_state DEFAULT 'pending',
    generation_attempt INT DEFAULT 0,               -- How many times we tried to generate
    
    -- Validation scores and metadata
    validation_score DECIMAL(5, 4),                 -- 0.0 to 1.0
    validation_checks JSONB,                        -- {"background_white": true, "blur": false, "coverage": 0.55, ...}
    auto_accept_reason VARCHAR(255),                -- Why it was auto-accepted
    auto_reject_reason VARCHAR(255),                -- Why it was auto-rejected
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    source VARCHAR(100) DEFAULT 'generated'         -- 'generated' or 'manual_upload'
);

CREATE INDEX idx_product_images_product_id ON product_images (product_id);
CREATE INDEX idx_product_images_state ON product_images (state);
CREATE INDEX idx_product_images_validation_score ON product_images (validation_score);

-- ============================================================================
-- VALIDATION LOGS TABLE (Audit Trail)
-- ============================================================================
CREATE TABLE validation_logs (
    id SERIAL PRIMARY KEY,
    product_image_id INT NOT NULL REFERENCES product_images(id) ON DELETE CASCADE,
    validation_timestamp TIMESTAMP DEFAULT NOW(),
    validator_name VARCHAR(100),                    -- 'automated', 'ml_detector', etc.
    background_white_result BOOLEAN,
    blur_result BOOLEAN,
    object_coverage DECIMAL(5, 4),
    object_detection_result BOOLEAN,
    perceptual_similarity DECIMAL(5, 4),
    overall_score DECIMAL(5, 4),
    details JSONB,
    execution_time_ms INT
);

CREATE INDEX idx_validation_logs_product_image_id ON validation_logs (product_image_id);

-- ============================================================================
-- REVIEW TASKS TABLE (Problem 2: Human-in-the-Loop)
-- ============================================================================
CREATE TABLE review_tasks (
    id SERIAL PRIMARY KEY,
    task_uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_image_id INT REFERENCES product_images(id) ON DELETE CASCADE,
    status review_status DEFAULT 'pending',
    validation_score DECIMAL(5, 4),                 -- Score from automated validation
    validation_checks JSONB,
    failure_reason VARCHAR(500),                    -- Why it needs human review
    
    -- Reviewer assignment
    assigned_to INT,                                -- User ID (can join with your users table)
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- SLA
    created_at TIMESTAMP DEFAULT NOW(),
    due_by TIMESTAMP,                               -- e.g., 2 hours from created_at
    priority INT DEFAULT 3,                         -- 1=urgent, 5=low
    
    CONSTRAINT check_review_status_transition CHECK (status IN ('pending', 'in_progress', 'accepted', 'rejected', 'requires_edit'))
);

CREATE INDEX idx_review_tasks_status ON review_tasks (status);
CREATE INDEX idx_review_tasks_assigned_to ON review_tasks (assigned_to);
CREATE INDEX idx_review_tasks_created_at ON review_tasks (created_at DESC);
CREATE INDEX idx_review_tasks_due_by ON review_tasks (due_by);

-- ============================================================================
-- REVIEW FEEDBACK TABLE (Model Training Data)
-- ============================================================================
CREATE TABLE review_feedback (
    id SERIAL PRIMARY KEY,
    review_task_id INT NOT NULL REFERENCES review_tasks(id) ON DELETE CASCADE,
    reviewer_id INT,                                -- Who reviewed it
    decision VARCHAR(50) NOT NULL,                  -- 'accepted', 'rejected', 'needs_edit'
    decision_reason VARCHAR(255),                   -- Why they accepted/rejected
    
    original_image_url VARCHAR(2048),               -- Original generated image
    corrected_image_url VARCHAR(2048),              -- If reviewer edited or uploaded new
    feedback_text TEXT,                             -- Additional notes
    
    -- Confidence rating from reviewer
    reviewer_confidence INT DEFAULT 5,              -- 1-5 scale
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- For model training
    marked_for_training BOOLEAN DEFAULT FALSE,
    training_dataset_name VARCHAR(255)
);

CREATE INDEX idx_review_feedback_review_task_id ON review_feedback (review_task_id);
CREATE INDEX idx_review_feedback_reviewer_id ON review_feedback (reviewer_id);
CREATE INDEX idx_review_feedback_created_at ON review_feedback (created_at DESC);

-- ============================================================================
-- METRICS / STATISTICS VIEW
-- ============================================================================
CREATE VIEW image_pipeline_stats AS
SELECT
    DATE(p.created_at) as date,
    COUNT(DISTINCT p.id) as total_products_ingested,
    COUNT(DISTINCT CASE WHEN pi.state = 'auto_accepted' THEN pi.id END) as images_auto_accepted,
    COUNT(DISTINCT CASE WHEN pi.state = 'auto_rejected' THEN pi.id END) as images_auto_rejected,
    COUNT(DISTINCT CASE WHEN rt.id IS NOT NULL THEN rt.id END) as review_tasks_created,
    COUNT(DISTINCT CASE WHEN rf.decision = 'accepted' THEN rf.id END) as human_accepted,
    COUNT(DISTINCT CASE WHEN rf.decision = 'rejected' THEN rf.id END) as human_rejected,
    ROUND(
        COUNT(DISTINCT CASE WHEN pi.state = 'auto_accepted' THEN pi.id END)::NUMERIC /
        NULLIF(COUNT(DISTINCT pi.id), 0),
        4
    ) as auto_accept_rate,
    EXTRACT(EPOCH FROM (AVG(CASE WHEN rf.created_at IS NOT NULL THEN rf.created_at - rt.created_at END))) / 3600 as avg_review_hours
FROM
    products p
    LEFT JOIN product_images pi ON p.id = pi.product_id
    LEFT JOIN review_tasks rt ON pi.id = rt.product_image_id
    LEFT JOIN review_feedback rf ON rt.id = rf.review_task_id
GROUP BY
    DATE(p.created_at);

-- ============================================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER products_update_timestamp
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER product_images_update_timestamp
BEFORE UPDATE ON product_images
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- ============================================================================
-- Sample data
-- ============================================================================
INSERT INTO vendors (name, vendor_short) VALUES
    ('British Imports', 'BRIT'),
    ('Acme Corporation', 'ACME'),
    ('Global Trade Inc', 'GLOB')
ON CONFLICT (vendor_short) DO NOTHING;
