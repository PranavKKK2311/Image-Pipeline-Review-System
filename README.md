# SKU Generation & Image Validation Pipeline

Complete solution for unique product code generation (SKU) and human-in-the-loop image validation.

## Problem Statement

**Problem 1:** Two different users submit similar product codes (e.g., `BRIT10G` vs `BRITC10G`) for the same product, causing collisions and ambiguity.

**Problem 2:** After code acceptance, automated image generation produces product images with white background, but sometimes images are incorrect (wrong product, bad background, artifacts). Requires human review for low-confidence results.

## Solution Overview

### Problem 1: Unique SKU Generation

- **Vendor namespace prefix**: All SKUs prefixed with vendor short code (`VEND-BRIT10G`)
- **Deterministic hashing**: On collision, append stable hash suffix (`VEND-BRIT10G-3F4E1A`)
- **Database enforcement**: Unique index on `canonical_sku` ensures no duplicates
- **Transaction-safe upsert**: Insert attempts use DB-level conflict detection

**Key files:**
- `backend/services/sku_generator.py` - Core canonicalization and SKU generation
- `backend/migrations/001_initial_schema.sql` - Database schema with uniqueness constraints
- `tests/test_sku_generator.py` - Test cases and edge cases

### Problem 2: Image Validation & Human-in-the-Loop

- **Automated validation**: White background, object detection, blur, coverage checks
- **Confidence scoring**: Weighted combination of multiple checks
- **Human review queue**: Tasks created for low-confidence images
- **Reviewer feedback**: Captured for model improvement and retraining
- **Review UI**: React frontend for human reviewers

**Key files:**
- `backend/services/image_validator.py` - Automated validation checks
- `backend/services/review_queue.py` - Task management for human review
- `frontend/pages/ReviewQueue.tsx` - React UI for reviewers
- `tests/test_image_validator.py` - Validation test suite

## Architecture

```
Product Ingestion
    ↓
[1] SKU Generation (deterministic canonicalization)
    ↓
[2] Image Generation (automated)
    ↓
[3] Image Validation (automated checks)
    ├─ HIGH confidence → Auto-accept
    ├─ LOW confidence → Human Review Queue
    └─ FAILED → Retry/Escalate
    ↓
[4] Human Review (optional)
    ├─ Accept
    ├─ Reject & Regenerate
    └─ Edit/Upload New
    ↓
[5] Feedback Capture (for model improvement)
```

## Quick Start

### Prerequisites
```
Python 3.8+
PostgreSQL 12+
Node.js 16+
```

### Setup

1. **Database**
   ```bash
   psql -U postgres -f backend/migrations/001_initial_schema.sql
   ```

2. **Backend**
   ```bash
   pip install -r requirements.txt
   python -m pytest tests/
   python backend/main.py
   ```

3. **Frontend**
   ```bash
   npm install
   npm start
   ```

4. **Test SKU Generation**
   ```bash
   python tests/test_sku_generator.py
   ```

5. **Test Image Validation**
   ```bash
   python tests/test_image_validator.py
   ```

## Usage Examples

### Generate Unique SKU

```python
from backend.services.sku_generator import SKUGenerator

gen = SKUGenerator(db_connection)
canonical_sku, status = gen.generate_sku(
    raw_code="BRIT10G",
    vendor_id=42,
    vendor_short="VEND"
)
# Returns: ("VEND-BRIT10G", "inserted") or ("VEND-BRIT10G-3F4E1A", "conflict_resolved")
```

### Validate Image

```python
from backend.services.image_validator import ImageValidator

validator = ImageValidator(
    background_white_threshold=0.95,
    blur_threshold=100.0,
    object_coverage_min=0.30,
    object_coverage_max=0.90
)

score, checks = validator.validate_image("product_image.jpg")
# Returns: (0.87, {"background_white": True, "blur": False, "coverage": 0.55, ...})

if score >= 0.85:  # Auto-accept threshold
    print("Auto-accepted")
else:
    print("Send to human review")
```

### Submit for Human Review

```python
from backend.services.review_queue import ReviewQueue

queue = ReviewQueue(db_connection)
task_id = queue.create_review_task(
    product_id=123,
    image_url="https://cdn.example.com/temp_image.jpg",
    validation_score=0.65,
    validation_checks=checks,
    reason="Low object coverage"
)
# Task now visible in ReviewQueue UI
```

## Configuration

Edit `backend/config.py`:

```python
# Thresholds
SKU_ACCEPT_THRESHOLD = 0.95
IMAGE_ACCEPT_THRESHOLD = 0.85
IMAGE_ACCEPT_ON_MANUAL_RETRY = 0.70

# Retry policy
MAX_AUTO_REGENERATE_ATTEMPTS = 2
HUMAN_REVIEW_TIMEOUT_HOURS = 48

# Quality metrics
BACKGROUND_WHITE_TOLERANCE = 10  # RGB distance
OBJECT_COVERAGE_MIN = 0.30       # 30% of image
OBJECT_COVERAGE_MAX = 0.90       # 90% of image
BLUR_THRESHOLD = 100.0           # Laplacian variance
```

## Database Schema

See `backend/migrations/001_initial_schema.sql` for:

- `products` - Core product table with canonical SKU
- `product_images` - Image records with validation scores
- `review_tasks` - Human review queue
- `review_feedback` - Reviewer decisions and feedback (for model training)
- `validation_logs` - Full audit trail of validation checks

## Monitoring & Metrics

- Image auto-accept rate (should be > 90%)
- Human review average time-to-decision (SLA: < 2 hours)
- False positive/negative rate (tracked after human review)
- Reviewer agreement rate (if multiple reviewers)

## Integration Steps

1. **Add SKU generation to ingestion pipeline** → compute canonical_sku at insert time
2. **Add image validation to generation service** → run checks after image generated
3. **Implement review queue consumer** → poll for new human tasks
4. **Deploy reviewer UI** → expose review task queue and decision UI
5. **Capture feedback** → store reviewer decisions for analytics and model retraining

## File Structure

```
sku-image-pipeline/
├── README.md
├── requirements.txt
├── backend/
│   ├── main.py                          # FastAPI server
│   ├── config.py                        # Configuration
│   ├── database.py                      # DB connection pooling
│   ├── migrations/
│   │   └── 001_initial_schema.sql       # Database schema
│   ├── services/
│   │   ├── sku_generator.py             # SKU canonicalization (Problem 1)
│   │   ├── image_validator.py           # Image validation (Problem 2)
│   │   └── review_queue.py              # HITL task management
│   └── api/
│       ├── products.py                  # Product endpoints
│       ├── images.py                    # Image endpoints
│       └── review.py                    # Review queue endpoints
├── frontend/
│   ├── package.json
│   ├── pages/
│   │   └── ReviewQueue.tsx              # Reviewer UI
│   └── components/
│       ├── ImageViewer.tsx
│       └── ReviewActions.tsx
└── tests/
    ├── test_sku_generator.py            # SKU tests
    ├── test_image_validator.py          # Validation tests
    └── test_review_workflow.py          # E2E tests
```

## Performance Notes

- **SKU generation**: O(1) average, with retry loop on collision
- **Image validation**: ~500ms per image (Pillow + simple checks), ~2s with ML detector
- **Human review**: Async queue, no blocking on validation
- **Database**: Unique index on canonical_sku ensures O(log n) conflict checks

## Future Improvements

1. Active learning: Present borderline-case images to reviewers for max signal
2. Model retraining: Use accepted/rejected pairs to fine-tune image generator
3. Multi-vendor SKU consolidation: Detect and merge duplicate SKUs across vendors
4. ML-based image quality: Train binary classifier (good/bad) on reviewer feedback
5. A/B testing: Test different canonicalization strategies or validation thresholds

## Support & Troubleshooting

- **SKU collision after deterministic suffix**: Increase hash length or implement incremental counter
- **Images in review queue not moving**: Check reviewer UI deployment, verify API connectivity
- **High false positive rate**: Loosen validation thresholds or disable certain checks
- **Image generation failures**: Implement retry with exponential backoff; escalate if all retries fail

---

**Created:** November 14, 2025
**Version:** 1.0
