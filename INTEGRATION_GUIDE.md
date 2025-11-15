"""
Integration and deployment guide
"""

# ============================================================================
# Integration into Existing Ingestion Pipeline
# ============================================================================

## Step 1: Add SKU Generation to Product Ingestion

When a new product is received:

```python
from backend.services.sku_generator import SKUGenerator

def ingest_product(vendor_id: int, raw_code: str, product_data: dict):
    """
    Add this to your product ingestion pipeline
    """
    sku_gen = SKUGenerator(db_connection=db)
    
    # Generate unique SKU (deterministic, with collision handling)
    canonical_sku, status = sku_gen.generate_sku(
        raw_code=raw_code,
        vendor_id=vendor_id,
        vendor_short=get_vendor_short(vendor_id),
    )
    
    if not canonical_sku:
        log_error(f"Failed to generate SKU for {raw_code}")
        return None
    
    # Insert product with canonical_sku
    product = Product.create(
        vendor_id=vendor_id,
        vendor_code=raw_code,
        canonical_sku=canonical_sku,
        **product_data
    )
    
    return product
```

## Step 2: Add Image Validation to Generation Pipeline

After image is generated:

```python
from backend.services.image_validator import ImageValidator
from backend.services.review_queue import ReviewQueue

def process_generated_image(product_id: int, image_path: str):
    """
    Add this to your image generation pipeline
    """
    validator = ImageValidator()
    queue = ReviewQueue(db_connection=db)
    
    # Run validation checks
    metrics = validator.validate_image(image_path)
    
    # Store validation result
    product_image = ProductImage.create(
        product_id=product_id,
        image_url=image_path,
        validation_score=metrics.overall_score,
        validation_checks=metrics.to_dict(),
        state=metrics.status.value,
        auto_accept_reason=metrics.reason if metrics.status == ValidationStatus.AUTO_ACCEPTED else None,
        auto_reject_reason=metrics.reason if metrics.status == ValidationStatus.AUTO_REJECTED else None,
    )
    
    # If high confidence, accept immediately
    if metrics.status == ValidationStatus.AUTO_ACCEPTED:
        product_image.state = 'auto_accepted'
        product_image.save()
        log_info(f"Image auto-accepted: product={product_id}, score={metrics.overall_score:.2f}")
        return product_image
    
    # If low confidence, create human review task
    elif metrics.status in [ValidationStatus.NEEDS_REVIEW, ValidationStatus.AUTO_REJECTED]:
        task_id = queue.create_review_task(
            product_id=product_id,
            product_image_id=product_image.id,
            product_name=product.name,
            vendor_code=product.vendor_code,
            canonical_sku=product.canonical_sku,
            image_url=image_path,
            validation_score=metrics.overall_score,
            validation_checks=metrics.to_dict(),
            failure_reason=metrics.reason,
        )
        
        product_image.state = 'pending'
        product_image.save()
        
        log_warning(f"Image sent to review: product={product_id}, score={metrics.overall_score:.2f}, task={task_id}")
        return product_image
    
    return product_image
```

## Step 3: Deploy Review Queue Consumer

Run a background worker that processes human decisions:

```python
from backend.services.review_queue import ReviewQueue, ReviewDecision

def review_queue_consumer():
    """
    Background worker (use Celery, APScheduler, etc.)
    Poll for completed review tasks and process feedback
    """
    queue = ReviewQueue(db_connection=db)
    
    while True:
        # Check for feedback on completed reviews
        feedback_samples = queue.get_feedback_for_training(
            since_timestamp=datetime.now() - timedelta(hours=1),
            min_samples=100,
        )
        
        if feedback_samples:
            # Trigger model retraining or export to training dataset
            log_info(f"Collected {len(feedback_samples)} feedback samples for training")
            # Could trigger: async_retrain_image_generator.delay(feedback_samples)
        
        time.sleep(30)  # Poll every 30 seconds
```

# ============================================================================
# Schema Changes for Existing Database
# ============================================================================

## If You Have Existing Products Table

Run migration to add SKU columns:

```sql
-- Add columns
ALTER TABLE products ADD COLUMN vendor_code VARCHAR(255);
ALTER TABLE products ADD COLUMN canonical_sku VARCHAR(64);

-- Create unique index
CREATE UNIQUE INDEX uq_products_canonical_sku ON products (canonical_sku);

-- Backfill existing products (deterministic based on current data)
UPDATE products 
SET 
    vendor_code = COALESCE(vendor_code, code),  -- Rename existing 'code' column
    canonical_sku = vendor_short || '-' || UPPER(REGEXP_REPLACE(code, '[^A-Z0-9]', '', 'g'))
WHERE canonical_sku IS NULL;
```

## If You Have Existing Images Table

Add validation columns:

```sql
-- Add columns
ALTER TABLE product_images ADD COLUMN validation_score DECIMAL(5, 4);
ALTER TABLE product_images ADD COLUMN validation_checks JSONB DEFAULT '{}';
ALTER TABLE product_images ADD COLUMN state VARCHAR(50) DEFAULT 'pending';

-- Create index
CREATE INDEX idx_product_images_validation_score ON product_images (validation_score);
CREATE INDEX idx_product_images_state ON product_images (state);
```

# ============================================================================
# Monitoring & Metrics
# ============================================================================

## Metrics to Track

```python
# In your monitoring system (Prometheus, DataDog, etc.)

class PipelineMetrics:
    """Key metrics to monitor"""
    
    # SKU Generation
    sku_generated_total = Counter(...)
    sku_collision_count = Counter(...)
    sku_collision_resolution_time_ms = Histogram(...)
    
    # Image Validation
    images_validated_total = Counter(...)
    images_auto_accepted = Counter(...)
    images_auto_rejected = Counter(...)
    images_needs_review = Counter(...)
    validation_score_distribution = Histogram(...)
    validation_execution_time_ms = Histogram(...)
    
    # Review Queue
    review_tasks_created = Counter(...)
    review_tasks_completed = Counter(...)
    review_task_sla_violations = Counter(...)
    review_task_turnaround_time_hours = Histogram(...)
    reviewer_accuracy = Gauge(...)  # Based on inter-reviewer agreement
    
    # Model Training
    feedback_samples_collected = Counter(...)
    training_jobs_triggered = Counter(...)
    model_performance_improvement = Gauge(...)
```

## Alert Thresholds

```
- High collision rate (> 5%): Investigate SKU generation
- High auto-reject rate (> 20%): Review validation thresholds or image generation quality
- Review queue backlog (> 100 pending): Add more reviewers
- High SLA violations (> 10%): Escalate urgent reviews
- Low reviewer confidence (< 3/5 avg): Provide training or adjust task difficulty
```

# ============================================================================
# Database Connection Setup
# ============================================================================

Example with PostgreSQL and SQLAlchemy:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import backend.config as config

engine = create_engine(
    config.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=config.DATABASE_POOL_SIZE,
    max_overflow=config.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=config.DATABASE_POOL_PRE_PING,
)

# Pass engine connection to services
sku_generator = SKUGenerator(db_connection=engine)
image_validator = ImageValidator()  # No DB needed
review_queue = ReviewQueue(db_connection=engine)
```

# ============================================================================
# API Usage Examples
# ============================================================================

## Generate SKU

```bash
curl -X POST http://localhost:8000/api/v1/sku/generate \
  -H "Content-Type: application/json" \
  -d '{
    "raw_code": "BRIT10G",
    "vendor_id": 42,
    "vendor_short": "BRIT",
    "product_name": "Widget A"
  }'
```

Response:
```json
{
  "canonical_sku": "BRIT-BRIT10G",
  "status": "inserted",
  "message": "SKU generated successfully: BRIT-BRIT10G"
}
```

## Validate Image

```bash
curl -X POST http://localhost:8000/api/v1/image/validate \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://cdn/image.jpg",
    "product_id": 123
  }'
```

Response:
```json
{
  "validation_score": 0.89,
  "status": "auto_accepted",
  "reason": "All checks passed",
  "checks": {
    "background_white": 0.98,
    "blur": 0.92,
    "object_coverage": 0.85,
    "perceptual_similarity": 0.95
  },
  "execution_time_ms": 523
}
```

## Create Review Task

```bash
curl -X POST http://localhost:8000/api/v1/review/create-task \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 123,
    "product_image_id": 1001,
    "product_name": "Widget A",
    "vendor_code": "BRIT10G",
    "canonical_sku": "BRIT-BRIT10G",
    "image_url": "https://cdn/image.jpg",
    "validation_score": 0.72,
    "validation_checks": {"background_white": 0.70},
    "failure_reason": "Borderline validation score"
  }'
```

Response:
```json
{
  "task_id": 5001,
  "status": "created",
  "message": "Review task created: 5001"
}
```

## Submit Review Decision

```bash
curl -X POST http://localhost:8000/api/v1/review/submit-decision \
  -H "Content-Type: application/json" \
  -d '{
    "review_task_id": 5001,
    "decision": "accepted",
    "reviewer_id": 42,
    "reviewer_confidence": 5,
    "reviewer_notes": "Image looks good after closer inspection"
  }'
```

Response:
```json
{
  "task_id": 5001,
  "decision": "accepted",
  "status": "recorded",
  "message": "Decision recorded successfully"
}
```

# ============================================================================
# Performance & Scaling
# ============================================================================

## SKU Generation
- **Latency**: ~1ms per SKU (slugify + hash)
- **Bottleneck**: DB unique constraint check on collision (typically < 5%)
- **Scaling**: Add DB index on canonical_sku; handle collisions in queue

## Image Validation
- **Latency**: 
  - Simple checks (white background, blur): ~100ms
  - ML object detection: ~2000ms
  - Perceptual hash: ~200ms
- **Recommendation**: Run expensive checks async; quick checks sync in request
- **Scaling**: Offload validation to queue workers; use GPU for ML inference

## Review Queue
- **Throughput**: 1 reviewer ~ 5-10 tasks/hour
- **Scaling**: 
  - Increase reviewers as backlog grows
  - Use priority queue for urgent items
  - Distribute tasks based on reviewer expertise

# ============================================================================
# Future Improvements
# ============================================================================

1. **Active Learning**: Present borderline-case images to reviewers for max signal
2. **Model Retraining**: Use accepted/rejected pairs to fine-tune image generator
3. **Multi-Vendor SKU Consolidation**: Detect and merge duplicate SKUs across vendors
4. **ML-Based Image Quality**: Train binary classifier on reviewer feedback
5. **A/B Testing**: Test different canonicalization or validation strategies
6. **Batch Import**: Support bulk SKU generation and image validation
7. **API Authentication**: Add OAuth2 or API keys
8. **Rate Limiting**: Protect API from abuse
9. **Caching**: Cache validation results for duplicate images (use image hash)
10. **Webhooks**: Notify external systems on review completion

---

Version: 1.0
Created: November 14, 2025
