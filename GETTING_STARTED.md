# Getting Started Guide

Complete, production-ready solution for Problems 1 & 2 is now ready.

## Quick Start (5 minutes)

### 1. Understand the Solution via Demo

Run the interactive demo:

```bash
cd sku-image-pipeline
python demo.py
```

This demonstrates:
- **Problem 1 solved**: Unique SKU generation for multi-vendor products
- **Problem 2 solved**: Image validation with human-in-the-loop

### 2. Project Structure

```
sku-image-pipeline/
├── README.md                          # Project overview
├── GETTING_STARTED.md                 # This file
├── INTEGRATION_GUIDE.md               # How to integrate into your system
├── demo.py                            # Interactive demo (run this first!)
├── requirements.txt                   # Python dependencies
│
├── backend/
│   ├── main.py                        # FastAPI server
│   ├── config.py                      # Configuration (EDIT THIS for your settings)
│   ├── migrations/
│   │   └── 001_initial_schema.sql     # PostgreSQL schema
│   ├── services/
│   │   ├── sku_generator.py           # Problem 1: SKU generation
│   │   ├── image_validator.py         # Problem 2: Image validation
│   │   └── review_queue.py            # Problem 2: Human review workflow
│   └── api/                           # (FastAPI endpoints in main.py)
│
├── frontend/
│   ├── package.json                   # Node dependencies
│   └── pages/
│       └── ReviewQueue.tsx            # Human reviewer UI
│
├── tests/
│   ├── test_sku_generator.py          # Tests for Problem 1
│   ├── test_image_validator.py        # Tests for Problem 2
│   └── test_integration.py            # E2E tests
```

## Installation (10 minutes)

### Prerequisites
- Python 3.8+
- PostgreSQL 12+ (optional, can use SQLite for dev)
- Node.js 16+ (for frontend)

### Backend Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Set up PostgreSQL database
psql -U postgres -f backend/migrations/001_initial_schema.sql

# 4. Run demo to verify installation
python demo.py
```

### Frontend Setup (Optional)

```bash
cd frontend
npm install
npm run dev  # Starts dev server at http://localhost:3000
```

## Understanding the Solution

### Problem 1: Product Code Collisions

**Issue**: Users submit similar codes (`BRIT10G` vs `BRITC10G`), causing ambiguity.

**Solution**: Deterministic SKU generation with vendor namespace + collision detection

```python
from backend.services.sku_generator import SKUGenerator

gen = SKUGenerator(db_connection)

# User 1: BRIT vendor
sku1, status = gen.generate_sku(
    raw_code="BRIT10G",
    vendor_id=1,
    vendor_short="BRIT"
)
# Result: "BRIT-BRIT10G"

# User 2: Same vendor, different code
sku2, status = gen.generate_sku(
    raw_code="BRITC10G", 
    vendor_id=1,
    vendor_short="BRIT"
)
# Result: "BRIT-BRITC10G" (Different!)

# User 3: Different vendor, same code
sku3, status = gen.generate_sku(
    raw_code="BRIT10G",
    vendor_id=2,
    vendor_short="ACME"
)
# Result: "ACME-BRIT10G" (Also different!)
```

**Key Features**:
- ✓ Deterministic: Same input always produces same output
- ✓ Collision-safe: Vendor prefix + deterministic suffix on collision
- ✓ Database-enforced: Unique index prevents duplicates
- ✓ Human-readable: Prefixed codes remain meaningful

### Problem 2: Image Quality & Human Review

**Issue**: Generated images sometimes have issues (bad background, blur, wrong content). Manual review needed but no workflow exists.

**Solution**: Automated validation + human-in-the-loop review queue

```python
from backend.services.image_validator import ImageValidator
from backend.services.review_queue import ReviewQueue

# 1. Validate image automatically
validator = ImageValidator(
    accept_score_threshold=0.85,      # Auto-accept if >= 0.85
    review_score_threshold=0.70,      # Human review if 0.70-0.85
)

metrics = validator.validate_image("product_image.jpg")

if metrics.status == "auto_accepted":
    print("✓ Image approved automatically")
    # Store in catalog immediately
    
elif metrics.status == "needs_review":
    print("⚠️ Image needs human review")
    # Create review task
    queue = ReviewQueue(db_connection)
    task_id = queue.create_review_task(
        product_id=123,
        image_url="product_image.jpg",
        validation_score=metrics.overall_score,
        failure_reason=metrics.reason,
    )
    # Human reviewer sees task in UI
    
else:  # auto_rejected
    print("✗ Image rejected, retry generation")
    # Trigger regeneration with modified prompt
```

**Validation Checks**:
1. **Background white**: Samples border pixels, checks if white
2. **Blur detection**: Laplacian variance (higher = sharper)
3. **Object coverage**: Foreground object size (should be 30-90% of image)
4. **Object detection**: ML-based presence confirmation
5. **Perceptual similarity**: Hash comparison to reference (if available)

**Human Review Workflow**:
1. Reviewer receives task in UI (http://localhost:3000/review)
2. Sees image + validation results
3. Makes decision: Accept / Reject / Requires Edit
4. Provides confidence rating + notes
5. Decision recorded for model training

## Configuration

Edit `backend/config.py` to customize thresholds:

```python
# Image acceptance thresholds
IMAGE_ACCEPT_THRESHOLD = 0.85           # Auto-accept if score >= 0.85
IMAGE_HUMAN_REVIEW_THRESHOLD = 0.70     # Human review if score < 0.85 but >= 0.70
MAX_AUTO_REGENERATE_ATTEMPTS = 2        # Retry N times before human review

# Validation check weights (must sum to 1.0)
VALIDATION_WEIGHTS = {
    "background_white": 0.25,
    "blur": 0.15,
    "object_coverage": 0.25,
    "object_detection": 0.20,
    "perceptual_similarity": 0.15,
}

# White background check
BACKGROUND_WHITE_TOLERANCE = 10         # RGB distance
BACKGROUND_WHITE_THRESHOLD = 0.95       # % of border pixels

# Object size constraints
OBJECT_COVERAGE_MIN = 0.30              # Minimum 30%
OBJECT_COVERAGE_MAX = 0.90              # Maximum 90%

# Blur detection
BLUR_THRESHOLD = 100.0                  # Laplacian variance threshold
```

## Running the Server

```bash
# Start FastAPI server
python backend/main.py

# Server starts at http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Test API Endpoints

```bash
# Generate SKU
curl -X POST http://localhost:8000/api/v1/sku/generate \
  -H "Content-Type: application/json" \
  -d '{
    "raw_code": "BRIT10G",
    "vendor_id": 42,
    "vendor_short": "BRIT"
  }'

# Validate image
curl -X POST http://localhost:8000/api/v1/image/validate \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://cdn.example.com/image.jpg",
    "product_id": 123
  }'

# Create review task
curl -X POST http://localhost:8000/api/v1/review/create-task \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 123,
    "product_image_id": 1001,
    "product_name": "Widget A",
    "vendor_code": "BRIT10G",
    "canonical_sku": "BRIT-BRIT10G",
    "image_url": "https://cdn.example.com/image.jpg",
    "validation_score": 0.72,
    "validation_checks": {"background_white": 0.70},
    "failure_reason": "Borderline validation score"
  }'

# Get pending review tasks
curl http://localhost:8000/api/v1/review/pending
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_sku_generator.py -v

# Run with coverage
pytest tests/ --cov=backend
```

## Integration into Your System

See `INTEGRATION_GUIDE.md` for step-by-step instructions to integrate into your existing:
- Product ingestion pipeline
- Image generation service
- Database schema
- Monitoring/metrics system

Quick summary:

1. **Product Ingestion**: Call `sku_generator.generate_sku()` for each new product
2. **Image Generation**: After image generated, call `image_validator.validate_image()`
3. **Image Review**: High-confidence images auto-approved; others sent to review queue
4. **Human Review**: Reviewer UI for borderline cases
5. **Feedback**: Reviewer decisions stored for model retraining

## File Descriptions

### Backend Services

| File | Purpose | Lines |
|------|---------|-------|
| `sku_generator.py` | Deterministic SKU generation with collision handling | ~300 |
| `image_validator.py` | Automated image validation with multiple checks | ~500 |
| `review_queue.py` | Human review task management | ~400 |

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/sku/generate` | POST | Generate unique SKU |
| `/api/v1/sku/validate/{sku}` | GET | Check SKU uniqueness |
| `/api/v1/image/validate` | POST | Validate product image |
| `/api/v1/image/upload` | POST | Upload image and validate |
| `/api/v1/review/create-task` | POST | Create human review task |
| `/api/v1/review/pending` | GET | Get pending review tasks |
| `/api/v1/review/task/{id}` | GET | Get specific review task |
| `/api/v1/review/submit-decision` | POST | Submit reviewer decision |
| `/api/v1/review/stats` | GET | Get queue statistics |

### Frontend

| File | Purpose |
|------|---------|
| `ReviewQueue.tsx` | React component for human reviewer UI |

### Database

| Table | Purpose |
|-------|---------|
| `products` | Product catalog with canonical SKU |
| `product_images` | Image records with validation scores |
| `review_tasks` | Human review queue |
| `review_feedback` | Reviewer decisions (for model training) |
| `validation_logs` | Audit trail of all validation checks |

## Database Schema

The solution uses PostgreSQL with the following key tables:

**Products Table**:
- `vendor_code` - Original code from vendor
- `canonical_sku` - Unique generated SKU (UNIQUE constraint)
- Supports multi-vendor setup with prefix-based uniqueness

**Product Images Table**:
- `image_url` - URL to image file
- `validation_score` - Overall validation score (0-1)
- `validation_checks` - JSONB with individual check results
- `state` - Image status (pending, auto_accepted, auto_rejected, human_accepted, human_rejected)

**Review Tasks Table**:
- Tasks created for low-confidence images
- Tracks reviewer assignment, SLA, priority
- Supports reassignment for overdue tasks

**Review Feedback Table**:
- Captures reviewer decisions for training data
- Stores confidence ratings and notes
- Used for model retraining and accuracy measurement

## Monitoring & Metrics

Key metrics to track:

```
SKU Generation:
  - sku_generated_total (counter)
  - sku_collision_count (counter)
  - sku_collision_resolution_time_ms (histogram)

Image Validation:
  - images_validated_total (counter)
  - images_auto_accepted (counter)
  - images_auto_rejected (counter)
  - images_needs_review (counter)
  - validation_score_distribution (histogram)
  - validation_execution_time_ms (histogram)

Review Queue:
  - review_tasks_created (counter)
  - review_tasks_completed (counter)
  - review_task_turnaround_time_hours (histogram)
  - reviewer_agreement_rate (gauge)
  - review_sla_violations (counter)
```

## Troubleshooting

### SKU Generation Issues

**Q: Getting collision errors despite deterministic suffix?**
- Increase `SKU_DETERMINISTIC_HASH_LENGTH` in config.py
- Check database index on `canonical_sku`

**Q: SKU too long, exceeding column limit?**
- Truncate vendor prefix or product code
- Reduce hash suffix length
- Or increase DB column size

### Image Validation Issues

**Q: Too many false positives (auto-rejected good images)?**
- Lower `IMAGE_ACCEPT_THRESHOLD` in config.py
- Loosen individual check thresholds
- Example: increase `BLUR_THRESHOLD` or lower `OBJECT_COVERAGE_MIN`

**Q: Too many false negatives (accepting bad images)?**
- Raise `IMAGE_ACCEPT_THRESHOLD`
- Increase weight of failing checks in `VALIDATION_WEIGHTS`

**Q: PIL/OpenCV not available?**
- Install: `pip install pillow opencv-python imagehash`
- Missing libraries don't block basic functionality, but some checks disabled

### Review Queue Issues

**Q: Review tasks piling up?**
- Add more reviewers
- Lower `HUMAN_REVIEW_TIMEOUT_HOURS` to escalate urgently
- Automate more with stricter validation (increase `IMAGE_ACCEPT_THRESHOLD`)

**Q: Reviewer confusion about what to decide?**
- Add more context in task creation (product description, reference images)
- Provide decision guidelines in UI
- Example decision guide:
  - **Accept**: Image is clear, product visible, white background intact
  - **Reject**: Multiple issues, recommend regeneration
  - **Requires Edit**: Minor issues (crop, rotation, etc.)

## Next Steps

1. ✓ Run `python demo.py` to understand solution
2. ✓ Review code in `backend/services/`
3. ✓ Run `pytest tests/ -v` to see test coverage
4. ✓ Read `INTEGRATION_GUIDE.md` for your specific system
5. → Deploy backend: `python backend/main.py`
6. → Deploy frontend: `npm install && npm run build`
7. → Connect to your database (see config.py)
8. → Test API endpoints
9. → Monitor metrics
10. → Iterate based on reviewer feedback

## Support

For questions or issues:
1. Check INTEGRATION_GUIDE.md for integration steps
2. Review code comments in services/
3. Run tests: `pytest tests/ -v -s`
4. Check logs in backend/main.py output

## Summary

This solution provides:

✓ **Problem 1 - Unique SKU Generation**
  - Deterministic canonicalization
  - Multi-vendor support
  - Collision detection & automatic suffix
  - Database-enforced uniqueness
  - Production-ready with tests

✓ **Problem 2 - Image Validation & Human Review**
  - 5 automated validation checks
  - Confidence-based acceptance thresholds
  - Human review queue for borderline cases
  - React UI for reviewers
  - Feedback capture for model improvement
  - Complete audit trail

✓ **Deployment-Ready**
  - FastAPI REST API
  - PostgreSQL schema with migrations
  - Comprehensive tests
  - Configuration management
  - Monitoring hooks
  - Integration guide

---

**Created**: November 14, 2025  
**Version**: 1.0  
**Status**: Production-Ready
