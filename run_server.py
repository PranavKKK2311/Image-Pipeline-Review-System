"""
SKU Image Pipeline - Backend Server with Authentication
"""
import sys
import os
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import uvicorn
from pydantic import BaseModel
from enum import Enum

from backend.services.sku_generator import SKUGenerator
from backend.services.image_validator import ImageValidator
from backend.services.review_queue import ReviewQueue
import backend.config as config

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Create app
app = FastAPI(
    title="SKU & Image Validation Pipeline",
    version="2.0.0",
    description="Image validation with user authentication"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

# ============================================================================
# In-Memory Storage (for demo - use database in production)
# ============================================================================

users_db: Dict[str, Dict] = {}
tokens_db: Dict[str, str] = {}  # token -> email
submissions_db: List[Dict] = []
submission_counter = 0
review_tasks: List[Dict] = []
task_counter = 0

# Global services
sku_generator = None
image_validator = None
review_queue = None


# ============================================================================
# Models
# ============================================================================

class UserRole(str, Enum):
    VENDOR = "vendor"
    OFFICIAL = "official"


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateReviewTaskRequest(BaseModel):
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
    review_task_id: int
    decision: str
    reviewer_id: int
    reviewer_notes: Optional[str] = None
    reviewer_confidence: int = 5
    feedback_message: Optional[str] = None


# ============================================================================
# Auth Helpers
# ============================================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict]:
    if not credentials:
        return None
    token = credentials.credentials
    email = tokens_db.get(token)
    if email and email in users_db:
        return users_db[email]
    return None


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    user = await get_current_user(credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_official(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    user = await require_auth(credentials)
    if user["role"] != "official":
        raise HTTPException(status_code=403, detail="Officials only")
    return user


async def require_vendor(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    user = await require_auth(credentials)
    if user["role"] != "vendor":
        raise HTTPException(status_code=403, detail="Vendors only")
    return user


# ============================================================================
# Auth Endpoints
# ============================================================================

@app.post("/api/v1/auth/register")
async def register(request: RegisterRequest):
    """Register a new user"""
    if request.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    users_db[request.email] = {
        "name": request.name,
        "email": request.email,
        "password": hash_password(request.password),
        "role": request.role.value,
        "created_at": datetime.now().isoformat(),
    }
    
    # Auto-login after registration
    token = generate_token()
    tokens_db[token] = request.email
    
    return {
        "message": "Registration successful",
        "token": token,
        "user": {
            "name": request.name,
            "email": request.email,
            "role": request.role.value,
        }
    }


@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """Login user"""
    user = users_db.get(request.email)
    if not user or user["password"] != hash_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = generate_token()
    tokens_db[token] = request.email
    
    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        }
    }


@app.get("/api/v1/auth/me")
async def get_me(user: Dict = Depends(require_auth)):
    """Get current user info"""
    return {
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }


@app.post("/api/v1/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user"""
    if credentials and credentials.credentials in tokens_db:
        del tokens_db[credentials.credentials]
    return {"message": "Logged out"}


# ============================================================================
# Vendor Image Upload
# ============================================================================

# Create uploads directory
UPLOAD_DIR = os.path.join(project_root, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/api/v1/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    product_name: str = Form(...),
    vendor_code: str = Form(...),
    user: Dict = Depends(require_vendor),
):
    """Vendor uploads an image for review"""
    global submission_counter, task_counter
    
    # Validate file type
    if not file.content_type in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPG/PNG images allowed")
    
    # Save file
    submission_counter += 1
    ext = "jpg" if "jpeg" in file.content_type else "png"
    filename = f"submission_{submission_counter}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    # Create submission record
    submission = {
        "id": submission_counter,
        "vendor_email": user["email"],
        "vendor_name": user["name"],
        "product_name": product_name,
        "vendor_code": vendor_code,
        "filename": filename,
        "image_url": f"/uploads/{filename}",
        "status": "pending",
        "feedback": None,
        "reviewed_by": None,
        "created_at": datetime.now().isoformat(),
        "reviewed_at": None,
    }
    submissions_db.append(submission)
    
    # Also create a review task
    task_counter += 1
    task = {
        "id": task_counter,
        "submission_id": submission_counter,
        "product_id": submission_counter,
        "product_image_id": submission_counter,
        "product_name": product_name,
        "vendor_code": vendor_code,
        "vendor_name": user["name"],
        "vendor_email": user["email"],
        "canonical_sku": f"{vendor_code.upper()[:4]}-{vendor_code.upper()}",
        "image_url": f"/uploads/{filename}",
        "validation_score": 0.70,  # Default pending score
        "validation_checks": {
            "background_white": 0.75,
            "blur": 0.80,
            "object_coverage": 0.70,
            "perceptual_similarity": 0.65,
        },
        "failure_reason": "Awaiting human review",
        "priority": 3,
        "status": "pending",
        "feedback": None,
        "created_at": datetime.now().isoformat(),
        "due_by": (datetime.now() + timedelta(hours=48)).isoformat(),
    }
    review_tasks.append(task)
    
    return {
        "message": "Image uploaded successfully",
        "submission_id": submission_counter,
        "status": "pending",
    }


@app.get("/api/v1/images/my-submissions")
async def get_my_submissions(user: Dict = Depends(require_vendor)):
    """Get vendor's own submissions"""
    my_subs = [s for s in submissions_db if s["vendor_email"] == user["email"]]
    return {
        "count": len(my_subs),
        "submissions": sorted(my_subs, key=lambda x: x["id"], reverse=True),
    }


# Serve uploaded files
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ============================================================================
# Review Queue Endpoints (for Officials)
# ============================================================================

@app.get("/api/v1/review/pending")
async def get_pending_review_tasks(
    limit: int = 50, 
    priority: Optional[int] = None,
    user: Dict = Depends(require_official),
):
    """Get pending review tasks (officials only)"""
    pending = [t for t in review_tasks if t["status"] == "pending"]
    
    if priority:
        pending = [t for t in pending if t["priority"] == priority]
    
    return {
        "task_count": len(pending[:limit]),
        "tasks": pending[:limit]
    }


@app.get("/api/v1/review/task/{task_id}")
async def get_review_task(task_id: int, user: Dict = Depends(require_official)):
    """Get specific review task"""
    for task in review_tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")


@app.post("/api/v1/review/submit-decision")
async def submit_review_decision(
    request: SubmitReviewDecisionRequest,
    user: Dict = Depends(require_official),
):
    """Submit reviewer's decision with feedback"""
    for task in review_tasks:
        if task["id"] == request.review_task_id:
            task["status"] = request.decision
            task["reviewed_by"] = user["name"]
            task["reviewer_notes"] = request.reviewer_notes
            task["feedback"] = request.feedback_message or request.reviewer_notes
            task["reviewer_confidence"] = request.reviewer_confidence
            task["reviewed_at"] = datetime.now().isoformat()
            
            # Update corresponding submission
            for sub in submissions_db:
                if sub["id"] == task.get("submission_id"):
                    sub["status"] = request.decision
                    sub["feedback"] = request.feedback_message or request.reviewer_notes
                    sub["reviewed_by"] = user["name"]
                    sub["reviewed_at"] = datetime.now().isoformat()
                    break
            
            return {
                "task_id": request.review_task_id,
                "decision": request.decision,
                "status": "recorded",
                "message": "Decision recorded and vendor notified"
            }
    
    raise HTTPException(status_code=404, detail="Task not found")


@app.get("/api/v1/review/stats")
async def get_queue_statistics(user: Dict = Depends(require_official)):
    """Get review queue statistics"""
    pending_count = len([t for t in review_tasks if t["status"] == "pending"])
    completed = [t for t in review_tasks if t["status"] != "pending"]
    
    accepted = len([t for t in completed if t["status"] == "accepted"])
    rejected = len([t for t in completed if t["status"] == "rejected"])
    
    now = datetime.now()
    sla_violations = 0
    for task in review_tasks:
        if task["status"] == "pending":
            due_by = datetime.fromisoformat(task["due_by"])
            if now > due_by:
                sla_violations += 1
    
    avg_review_time = None
    if completed:
        times = []
        for task in completed:
            if task.get("reviewed_at"):
                created = datetime.fromisoformat(task["created_at"])
                reviewed = datetime.fromisoformat(task["reviewed_at"])
                times.append((reviewed - created).total_seconds() / 60)
        if times:
            avg_review_time = sum(times) / len(times)
    
    return {
        "pending_count": pending_count,
        "completed_count": len(completed),
        "accepted_count": accepted,
        "rejected_count": rejected,
        "sla_violations": sla_violations,
        "avg_review_time_minutes": avg_review_time,
    }


# ============================================================================
# Public endpoints (no auth required)
# ============================================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "SKU & Image Validation Pipeline",
        "version": "2.0.0"
    }


@app.post("/api/v1/review/create-task")
async def create_review_task_public(request: CreateReviewTaskRequest):
    """Create review task (public for testing)"""
    global task_counter
    task_counter += 1
    
    task = {
        "id": task_counter,
        "product_id": request.product_id,
        "product_image_id": request.product_image_id,
        "product_name": request.product_name,
        "vendor_code": request.vendor_code,
        "vendor_name": "Demo Vendor",
        "vendor_email": "demo@vendor.com",
        "canonical_sku": request.canonical_sku,
        "image_url": request.image_url,
        "validation_score": request.validation_score,
        "validation_checks": request.validation_checks,
        "failure_reason": request.failure_reason,
        "priority": 3,
        "status": "pending",
        "feedback": None,
        "created_at": datetime.now().isoformat(),
        "due_by": (datetime.now() + timedelta(hours=48)).isoformat(),
    }
    
    review_tasks.append(task)
    
    return {
        "task_id": task_counter,
        "status": "created",
        "message": f"Review task created: {task_counter}"
    }


# ============================================================================
# Startup
# ============================================================================

@app.on_event("startup")
async def startup():
    global sku_generator, image_validator, review_queue
    
    print("\n" + "=" * 60)
    print("  SKU & Image Validation Pipeline v2.0")
    print("  With User Authentication")
    print("=" * 60)
    
    sku_generator = SKUGenerator(db_connection=None)
    print("✓ SKU generator initialized")
    
    image_validator = ImageValidator(
        background_white_threshold=config.BACKGROUND_WHITE_THRESHOLD,
        blur_threshold=config.BLUR_THRESHOLD,
        object_coverage_min=config.OBJECT_COVERAGE_MIN,
        object_coverage_max=config.OBJECT_COVERAGE_MAX,
        accept_score_threshold=config.IMAGE_ACCEPT_THRESHOLD,
        review_score_threshold=config.IMAGE_HUMAN_REVIEW_THRESHOLD,
    )
    print("✓ Image validator initialized")
    
    review_queue = ReviewQueue(db_connection=None)
    print("✓ Review queue initialized")
    
    print(f"\n🚀 Server ready at http://localhost:{config.API_PORT}")
    print(f"📡 API docs: http://localhost:{config.API_PORT}/docs")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
