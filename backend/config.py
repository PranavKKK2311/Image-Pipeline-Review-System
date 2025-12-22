"""
Configuration for SKU and image validation pipeline.
"""

import os
from typing import Optional

# ============================================================================
# SKU Generation Configuration (Problem 1)
# ============================================================================
SKU_VENDOR_PREFIX_ENABLED = True          # Prepend vendor short code
SKU_MAX_LENGTH = 64                       # Max length of canonical_sku column
SKU_DETERMINISTIC_HASH_LENGTH = 6         # Length of collision suffix (e.g., "3F4E1A")
SKU_ACCEPT_THRESHOLD = 0.95               # Confidence threshold for SKU acceptance

# ============================================================================
# Image Generation & Validation Configuration (Problem 2)
# ============================================================================
IMAGE_ACCEPT_THRESHOLD = 0.85             # Auto-accept if validation score >= this
IMAGE_HUMAN_REVIEW_THRESHOLD = 0.70       # If score < 0.70, escalate or reject
IMAGE_ACCEPT_ON_MANUAL_RETRY = 0.65       # Lower threshold after human override

# Image validation check weights (must sum to 1.0)
VALIDATION_WEIGHTS = {
    "background_white": 0.20,
    "blur": 0.30,             # Increased importance
    "object_coverage": 0.20,
    "object_detection": 0.15,
    "perceptual_similarity": 0.15,
}

# White background check
BACKGROUND_WHITE_TOLERANCE = 10           # RGB distance tolerance
BACKGROUND_WHITE_BORDER_PX = 10           # Pixels to sample from border
BACKGROUND_WHITE_THRESHOLD = 0.95         # % of border pixels that must be white

# Blur detection
BLUR_THRESHOLD = 1000.0                   # Laplacian variance threshold (much higher = stricter)

# Object coverage
OBJECT_COVERAGE_MIN = 0.30                # Minimum 30% of image
OBJECT_COVERAGE_MAX = 0.90                # Maximum 90% of image
OBJECT_DETECTION_CONFIDENCE = 0.50        # ML detector confidence (0-1)

# Perceptual hash similarity
PERCEPTUAL_HASH_MIN_SIMILARITY = 0.70     # pHash similarity (0-1)

# ============================================================================
# Retry & Escalation Policy
# ============================================================================
MAX_AUTO_REGENERATE_ATTEMPTS = 2          # Auto-retry generation N times before human review
HUMAN_REVIEW_TIMEOUT_HOURS = 48           # SLA for human to decide
HUMAN_REVIEW_PRIORITY_LEVELS = {
    "urgent": 1,      # Critical issues, decide within 2 hours
    "high": 2,        # Important, 8 hours
    "normal": 3,      # Standard, 24 hours
    "low": 4,         # Can wait, 48 hours
}

# ============================================================================
# Database Configuration
# ============================================================================
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/product_pipeline"
)
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10
DATABASE_POOL_PRE_PING = True

# ============================================================================
# Storage Configuration
# ============================================================================
IMAGE_STORAGE_TYPE = os.environ.get("IMAGE_STORAGE_TYPE", "s3")  # s3, gcs, local
IMAGE_STORAGE_BUCKET = os.environ.get("IMAGE_STORAGE_BUCKET", "product-images")
IMAGE_TEMP_DIRECTORY = os.environ.get("IMAGE_TEMP_DIRECTORY", "/tmp/product_images")
IMAGE_MAX_SIZE_MB = 50                    # Maximum image file size

# ============================================================================
# API Configuration
# ============================================================================
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))
API_WORKERS = int(os.environ.get("API_WORKERS", "4"))
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# ============================================================================
# Review Queue Configuration
# ============================================================================
REVIEW_QUEUE_BATCH_SIZE = 50              # Items to fetch at once
REVIEW_QUEUE_POLL_INTERVAL_SECONDS = 30   # How often to check for new tasks
REVIEWER_MAX_CONCURRENT_TASKS = 10        # Tasks assigned per reviewer

# ============================================================================
# Logging & Monitoring
# ============================================================================
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
METRICS_ENABLED = True
METRICS_PORT = 9090
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

# ============================================================================
# Model Training & Feedback
# ============================================================================
ENABLE_FEEDBACK_CAPTURE = True            # Capture reviewer decisions for training
TRAINING_DATASET_MIN_SIZE = 100           # Min reviewed items before retraining
TRAINING_AUTO_TRIGGER_ENABLED = False     # Auto-trigger retraining when dataset ready
