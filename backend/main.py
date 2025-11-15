"""
FastAPI backend server for SKU and image validation pipeline
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import os

from backend.services.sku_generator import SKUGenerator
from backend.services.image_validator import ImageValidator, ValidationStatus
from backend.services.review_queue import ReviewQueue, ReviewDecision
import backend.config as config

logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="SKU & Image Validation Pipeline",
    version="1.0.0",
    description="Unified API for product code generation and image validation"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services (in production, use dependency injection)
sku_generator = None
image_validator = None
review_queue = None


# ============================================================================
# Request/Response Models
# ============================================================================

class GenerateSKURequest(BaseModel):
    """Request to generate SKU"""
    raw_code: str
    vendor_id: int
    vendor_short: str
    product_name: Optional[str] = None


class GenerateSKUResponse(BaseModel):
    """Response from SKU generation"""
    canonical_sku: str
    status: str  # "inserted", "conflict_resolved", "error"
    message: str


class ValidateImageRequest(BaseModel):
    """Request to validate image"""
    image_url: str
    reference_image_url: Optional[str] = None
    product_id: Optional[int] = None


class ValidateImageResponse(BaseModel):
    """Response from image validation"""
    validation_score: float
    status: str  # "auto_accepted", "auto_rejected", "needs_review", "error"
    reason: str
    checks: Dict[str, Any]
    execution_time_ms: int


class CreateReviewTaskRequest(BaseModel):
    """Request to create review task"""
    product_id: int
    product_image_id: int
    product_name: str
    vendor_code: str
    canonical_sku: str
    image_url: str
    validation_score: float
    validation_checks: Dict[str, Any]
    failure_reason: str


class SubmitReviewDecisionRequest(BaseModel):
    """Request to submit review decision"""
    review_task_id: int
    decision: str  # "accepted", "rejected", "requires_edit"
    reviewer_id: int
    reviewer_notes: Optional[str] = None
    reviewer_confidence: int = 5
    corrected_image_url: Optional[str] = None


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SKU & Image Validation Pipeline",
        "version": "1.0.0"
    }


@app.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "image_accept_threshold": config.IMAGE_ACCEPT_THRESHOLD,
        "image_review_threshold": config.IMAGE_HUMAN_REVIEW_THRESHOLD,
        "max_auto_regenerate_attempts": config.MAX_AUTO_REGENERATE_ATTEMPTS,
        "human_review_timeout_hours": config.HUMAN_REVIEW_TIMEOUT_HOURS,
    }


# ============================================================================
# SKU Generation Endpoints (Problem 1)
# ============================================================================

@app.post("/api/v1/sku/generate", response_model=GenerateSKUResponse)
async def generate_sku(request: GenerateSKURequest):
    """
    Generate unique SKU for product.
    
    Problem 1 solution: Deterministic canonicalization with collision detection.
    """
    try:
        if not sku_generator:
            raise HTTPException(status_code=503, detail="SKU service not initialized")

        canonical_sku, status = sku_generator.generate_sku(
            raw_code=request.raw_code,
            vendor_id=request.vendor_id,
            vendor_short=request.vendor_short,
        )

        if not canonical_sku:
            return GenerateSKUResponse(
                canonical_sku="",
                status="error",
                message=f"Failed to generate SKU: {status.value}"
            )

        return GenerateSKUResponse(
            canonical_sku=canonical_sku,
            status=status.value,
            message=f"SKU generated successfully: {canonical_sku}"
        )

    except Exception as e:
        logger.error(f"SKU generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sku/validate/{canonical_sku}")
async def validate_sku_uniqueness(canonical_sku: str):
    """Check if SKU is unique in database"""
    try:
        if not sku_generator:
            raise HTTPException(status_code=503, detail="SKU service not initialized")

        is_unique = sku_generator.validate_sku_uniqueness(canonical_sku)
        return {
            "canonical_sku": canonical_sku,
            "is_unique": is_unique
        }
    except Exception as e:
        logger.error(f"SKU validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Image Validation Endpoints (Problem 2)
# ============================================================================

@app.post("/api/v1/image/validate", response_model=ValidateImageResponse)
async def validate_image(request: ValidateImageRequest):
    """
    Validate product image.
    
    Problem 2 solution: Automated validation with human-in-the-loop fallback.
    """
    try:
        if not image_validator:
            raise HTTPException(status_code=503, detail="Image validator not initialized")

        # Download image to temporary file (placeholder)
        # In production: use proper storage service
        temp_image_path = f"/tmp/image_{request.product_id}.jpg"

        # Validate
        metrics = image_validator.validate_image(
            image_path=temp_image_path,
            reference_image_path=request.reference_image_url,
        )

        return ValidateImageResponse(
            validation_score=metrics.overall_score,
            status=metrics.status.value,
            reason=metrics.reason,
            checks={
                "background_white": metrics.background_white_score,
                "blur": metrics.blur_score,
                "object_coverage": metrics.object_coverage,
                "perceptual_similarity": metrics.perceptual_similarity,
            },
            execution_time_ms=metrics.execution_time_ms,
        )

    except Exception as e:
        logger.error(f"Image validation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/image/upload")
async def upload_product_image(
    file: UploadFile = File(...),
    product_id: int = None,
    auto_validate: bool = True,
):
    """
    Upload product image and optionally validate.
    """
    try:
        # Save uploaded file
        temp_path = f"/tmp/upload_{product_id}_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        response = {
            "filename": file.filename,
            "size_bytes": len(content),
            "product_id": product_id,
            "stored_at": temp_path,
        }

        # Auto-validate if requested
        if auto_validate and image_validator:
            metrics = image_validator.validate_image(temp_path)
            response["validation"] = {
                "score": metrics.overall_score,
                "status": metrics.status.value,
                "reason": metrics.reason,
            }

        return response

    except Exception as e:
        logger.error(f"Image upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Review Queue Endpoints (Problem 2 - HITL)
# ============================================================================

@app.post("/api/v1/review/create-task")
async def create_review_task(request: CreateReviewTaskRequest):
    """Create human review task for low-confidence image"""
    try:
        if not review_queue:
            raise HTTPException(status_code=503, detail="Review queue not initialized")

        task_id = review_queue.create_review_task(
            product_id=request.product_id,
            product_image_id=request.product_image_id,
            product_name=request.product_name,
            vendor_code=request.vendor_code,
            canonical_sku=request.canonical_sku,
            image_url=request.image_url,
            validation_score=request.validation_score,
            validation_checks=request.validation_checks,
            failure_reason=request.failure_reason,
        )

        return {
            "task_id": task_id,
            "status": "created",
            "message": f"Review task created: {task_id}"
        }

    except Exception as e:
        logger.error(f"Review task creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/review/pending")
async def get_pending_review_tasks(limit: int = 50, priority: Optional[int] = None):
    """Get pending review tasks"""
    try:
        if not review_queue:
            raise HTTPException(status_code=503, detail="Review queue not initialized")

        tasks = review_queue.get_pending_tasks(limit=limit, priority_filter=priority)
        return {
            "task_count": len(tasks),
            "tasks": [
                {
                    "id": t.id,
                    "product_name": t.product_name,
                    "canonical_sku": t.canonical_sku,
                    "validation_score": t.validation_score,
                    "priority": t.priority,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "due_by": t.due_by.isoformat() if t.due_by else None,
                }
                for t in tasks
            ]
        }

    except Exception as e:
        logger.error(f"Get pending tasks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/review/task/{task_id}")
async def get_review_task(task_id: int):
    """Get specific review task"""
    try:
        if not review_queue:
            raise HTTPException(status_code=503, detail="Review queue not initialized")

        task = review_queue.get_review_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "id": task.id,
            "product_id": task.product_id,
            "product_name": task.product_name,
            "canonical_sku": task.canonical_sku,
            "image_url": task.image_url,
            "validation_score": task.validation_score,
            "validation_checks": task.validation_checks,
            "failure_reason": task.failure_reason,
            "priority": task.priority,
            "status": task.status.value,
        }

    except Exception as e:
        logger.error(f"Get task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/review/submit-decision")
async def submit_review_decision(request: SubmitReviewDecisionRequest):
    """Submit reviewer's decision"""
    try:
        if not review_queue:
            raise HTTPException(status_code=503, detail="Review queue not initialized")

        # Map string decision to enum
        decision_map = {
            "accepted": ReviewDecision.ACCEPTED,
            "rejected": ReviewDecision.REJECTED,
            "requires_edit": ReviewDecision.REQUIRES_EDIT,
        }

        decision = decision_map.get(request.decision.lower())
        if not decision:
            raise HTTPException(status_code=400, detail="Invalid decision")

        result = review_queue.submit_review_decision(
            review_task_id=request.review_task_id,
            decision=decision,
            reviewer_id=request.reviewer_id,
            reviewer_notes=request.reviewer_notes,
            reviewer_confidence=request.reviewer_confidence,
            corrected_image_url=request.corrected_image_url,
        )

        if result:
            return {
                "task_id": request.review_task_id,
                "decision": request.decision,
                "status": "recorded",
                "message": "Decision recorded successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to record decision")

    except Exception as e:
        logger.error(f"Submit decision error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/review/stats")
async def get_queue_statistics():
    """Get review queue statistics"""
    try:
        if not review_queue:
            raise HTTPException(status_code=503, detail="Review queue not initialized")

        stats = review_queue.get_queue_stats()
        return stats

    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Startup & Shutdown
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    global sku_generator, image_validator, review_queue

    logger.info("Initializing services...")
    
    # Initialize SKU generator (no DB for demo)
    sku_generator = SKUGenerator(db_connection=None)
    logger.info("SKU generator initialized")

    # Initialize image validator
    image_validator = ImageValidator(
        background_white_threshold=config.BACKGROUND_WHITE_THRESHOLD,
        blur_threshold=config.BLUR_THRESHOLD,
        object_coverage_min=config.OBJECT_COVERAGE_MIN,
        object_coverage_max=config.OBJECT_COVERAGE_MAX,
        accept_score_threshold=config.IMAGE_ACCEPT_THRESHOLD,
        review_score_threshold=config.IMAGE_HUMAN_REVIEW_THRESHOLD,
    )
    logger.info("Image validator initialized")

    # Initialize review queue (no DB for demo)
    review_queue = ReviewQueue(db_connection=None)
    logger.info("Review queue initialized")

    logger.info("All services initialized successfully")


@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown"""
    logger.info("Shutting down services")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        workers=config.API_WORKERS,
        log_level=config.LOG_LEVEL.lower(),
    )
