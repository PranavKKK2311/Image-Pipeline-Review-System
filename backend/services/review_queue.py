"""
Review Queue Manager: Manages human-in-the-loop image review tasks

Key features:
- Create review tasks for low-confidence images
- Assign tasks to reviewers
- Track SLA and priority
- Capture reviewer decisions for feedback
- Support for image editing/correction
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Review task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REQUIRES_EDIT = "requires_edit"


class ReviewDecision(Enum):
    """Human reviewer decision"""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REQUIRES_EDIT = "requires_edit"
    NEEDS_REGENERATION = "needs_regeneration"


@dataclass
class ReviewTask:
    """Single human review task"""
    id: int
    task_uuid: str
    product_id: int
    product_image_id: int
    product_name: str
    vendor_code: str
    canonical_sku: str
    image_url: str
    validation_score: float
    validation_checks: Dict[str, Any]
    failure_reason: str
    status: ReviewStatus
    created_at: datetime
    due_by: datetime
    assigned_to: Optional[int] = None
    priority: int = 3  # 1=urgent, 5=low
    
    def is_overdue(self) -> bool:
        return datetime.now() > self.due_by
    
    def days_to_due(self) -> float:
        return (self.due_by - datetime.now()).total_seconds() / 86400


@dataclass
class ReviewDecisionInput:
    """Data submitted by reviewer"""
    review_task_id: int
    decision: ReviewDecision
    decision_reason: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewer_confidence: int = 5  # 1-5 scale
    corrected_image_url: Optional[str] = None  # If reviewer uploaded new image


@dataclass
class ReviewerMetrics:
    """Metrics for a single reviewer"""
    reviewer_id: int
    total_reviewed: int
    accepted_count: int
    rejected_count: int
    requires_edit_count: int
    avg_review_time_minutes: float
    avg_confidence: float
    agreement_rate: Optional[float] = None  # If inter-rater agreement computed


class ReviewQueue:
    """
    Manages the human-in-the-loop review queue.
    
    Typical flow:
    1. Image fails automated validation -> create_review_task()
    2. Reviewer receives task in UI -> get_assigned_tasks()
    3. Reviewer reviews and decides -> submit_review_decision()
    4. Decision captured in feedback table -> used for model training
    
    Example:
        queue = ReviewQueue(db_connection)
        
        # Create task when image validation is low-confidence
        task_id = queue.create_review_task(
            product_id=123,
            image_url="https://cdn/image.jpg",
            validation_score=0.65,
            reason="Object coverage too low"
        )
        
        # Reviewer gets task
        task = queue.get_review_task(task_id)
        
        # Reviewer submits decision
        queue.submit_review_decision(
            review_task_id=task_id,
            decision=ReviewDecision.REQUIRES_EDIT,
            reviewer_notes="Product cut off at bottom",
            reviewer_confidence=4
        )
    """

    def __init__(
        self,
        db_connection: Any,
        default_sla_hours: int = 48,
        enable_priority_assignment: bool = True,
    ):
        """
        Initialize review queue manager.
        
        Args:
            db_connection: Database connection pool
            default_sla_hours: Default SLA for review tasks
            enable_priority_assignment: Auto-assign priority based on validation score
        """
        self.db = db_connection
        self.default_sla_hours = default_sla_hours
        self.enable_priority_assignment = enable_priority_assignment

    def create_review_task(
        self,
        product_id: int,
        product_image_id: int,
        product_name: str,
        vendor_code: str,
        canonical_sku: str,
        image_url: str,
        validation_score: float,
        validation_checks: Dict[str, Any],
        failure_reason: str,
        priority: Optional[int] = None,
        sla_hours: Optional[int] = None,
    ) -> int:
        """
        Create a new human review task.
        
        Args:
            product_id: Product being reviewed
            product_image_id: Product image ID
            product_name: Human-readable product name
            vendor_code: Vendor's original code
            canonical_sku: Generated unique SKU
            image_url: URL to image being reviewed
            validation_score: Automated validation score (0-1)
            validation_checks: Dict of individual check results
            failure_reason: Why it needs review (e.g., "Low object coverage")
            priority: Manual priority override (1=urgent, 5=low)
            sla_hours: Override default SLA
            
        Returns:
            Review task ID
        """
        try:
            # Auto-compute priority if not specified
            if priority is None and self.enable_priority_assignment:
                priority = self._compute_priority(validation_score)
            else:
                priority = priority or 3

            # Compute due date
            sla_hours = sla_hours or self.default_sla_hours
            due_by = datetime.now() + timedelta(hours=sla_hours)

            # Insert task (placeholder; implement with actual DB)
            task_uuid = str(uuid.uuid4())
            
            logger.info(
                f"Created review task {task_uuid}: product={product_id}, "
                f"sku={canonical_sku}, score={validation_score:.2f}, priority={priority}"
            )

            # Mock: return a fake ID
            # In real implementation, return actual DB insert ID
            return hash(task_uuid) % 1000000

        except Exception as e:
            logger.error(f"Failed to create review task: {e}", exc_info=True)
            raise

    def get_review_task(self, task_id: int) -> Optional[ReviewTask]:
        """
        Fetch a review task by ID.
        
        Args:
            task_id: Review task ID
            
        Returns:
            ReviewTask object or None if not found
        """
        try:
            logger.debug(f"Fetching review task {task_id}")
            # Placeholder: implement with actual DB query
            return None
        except Exception as e:
            logger.error(f"Failed to fetch review task {task_id}: {e}")
            return None

    def get_pending_tasks(self, limit: int = 50, priority_filter: Optional[int] = None) -> List[ReviewTask]:
        """
        Get pending review tasks.
        
        Args:
            limit: Maximum number of tasks to return
            priority_filter: Optional filter by priority (1=most urgent)
            
        Returns:
            List of ReviewTask objects
        """
        try:
            logger.debug(f"Fetching {limit} pending tasks")
            # Placeholder: implement with actual DB query
            return []
        except Exception as e:
            logger.error(f"Failed to fetch pending tasks: {e}")
            return []

    def get_assigned_tasks(self, reviewer_id: int) -> List[ReviewTask]:
        """
        Get tasks assigned to a specific reviewer.
        
        Args:
            reviewer_id: Reviewer's user ID
            
        Returns:
            List of ReviewTask objects
        """
        try:
            logger.debug(f"Fetching tasks assigned to reviewer {reviewer_id}")
            # Placeholder
            return []
        except Exception as e:
            logger.error(f"Failed to fetch tasks for reviewer {reviewer_id}: {e}")
            return []

    def assign_task(self, task_id: int, reviewer_id: int) -> bool:
        """
        Assign task to a reviewer.
        
        Args:
            task_id: Review task ID
            reviewer_id: Reviewer's user ID
            
        Returns:
            True if assigned successfully
        """
        try:
            logger.info(f"Assigning task {task_id} to reviewer {reviewer_id}")
            # Placeholder: implement with actual DB update
            return True
        except Exception as e:
            logger.error(f"Failed to assign task {task_id}: {e}")
            return False

    def submit_review_decision(
        self,
        review_task_id: int,
        decision: ReviewDecision,
        reviewer_id: int,
        decision_reason: Optional[str] = None,
        reviewer_notes: Optional[str] = None,
        reviewer_confidence: int = 5,
        corrected_image_url: Optional[str] = None,
    ) -> bool:
        """
        Submit reviewer's decision for a task.
        
        Stores the decision in review_feedback table for:
        - Audit trail
        - Model training data
        - Metrics/reporting
        
        Args:
            review_task_id: Review task ID
            decision: Reviewer's decision
            reviewer_id: Reviewer's user ID
            decision_reason: Why they made this decision
            reviewer_notes: Additional feedback
            reviewer_confidence: Confidence in decision (1-5)
            corrected_image_url: If reviewer edited/uploaded new image
            
        Returns:
            True if stored successfully
        """
        try:
            logger.info(
                f"Recording review decision for task {review_task_id}: "
                f"decision={decision.value}, reviewer={reviewer_id}, "
                f"confidence={reviewer_confidence}"
            )

            # Placeholder: Insert into review_feedback table
            # UPDATE review_tasks SET status = ... WHERE id = review_task_id
            # INSERT INTO review_feedback (review_task_id, reviewer_id, decision, ...) VALUES (...)

            # Mark for training if enabled
            if decision in [ReviewDecision.ACCEPTED, ReviewDecision.REJECTED]:
                # Could trigger async job to add to training dataset
                logger.debug(f"Marked task {review_task_id} for potential training data capture")

            return True
        except Exception as e:
            logger.error(f"Failed to submit review decision: {e}", exc_info=True)
            return False

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get overall review queue statistics.
        
        Returns:
            Dict with pending count, SLA violations, avg review time, etc.
        """
        try:
            logger.debug("Computing queue statistics")
            # Placeholder: implement with SQL aggregations
            return {
                "pending_count": 0,
                "in_progress_count": 0,
                "sla_violations": 0,
                "avg_review_time_minutes": 0,
                "high_priority_count": 0,
            }
        except Exception as e:
            logger.error(f"Failed to compute queue stats: {e}")
            return {}

    def get_reviewer_metrics(self, reviewer_id: int) -> Optional[ReviewerMetrics]:
        """
        Get performance metrics for a reviewer.
        
        Args:
            reviewer_id: Reviewer's user ID
            
        Returns:
            ReviewerMetrics object or None
        """
        try:
            logger.debug(f"Computing metrics for reviewer {reviewer_id}")
            # Placeholder
            return None
        except Exception as e:
            logger.error(f"Failed to compute reviewer metrics: {e}")
            return None

    def get_overdue_tasks(self) -> List[ReviewTask]:
        """
        Get tasks that exceeded their SLA.
        
        Returns:
            List of overdue ReviewTask objects
        """
        try:
            logger.debug("Fetching overdue tasks")
            # Placeholder
            return []
        except Exception as e:
            logger.error(f"Failed to fetch overdue tasks: {e}")
            return []

    def reassign_overdue_task(self, task_id: int, new_reviewer_id: int) -> bool:
        """
        Reassign an overdue task to a different reviewer.
        
        Args:
            task_id: Review task ID
            new_reviewer_id: New reviewer's user ID
            
        Returns:
            True if reassigned successfully
        """
        try:
            logger.info(f"Reassigning overdue task {task_id} to reviewer {new_reviewer_id}")
            # Placeholder
            return True
        except Exception as e:
            logger.error(f"Failed to reassign task {task_id}: {e}")
            return False

    def get_feedback_for_training(
        self, since_timestamp: Optional[datetime] = None, min_samples: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch reviewer feedback suitable for model training.
        
        Filters for:
        - Recent feedback (optional)
        - High confidence decisions
        - Accepted/rejected pairs (ignore requires_edit)
        
        Args:
            since_timestamp: Only return feedback after this time
            min_samples: Only return if at least this many samples
            
        Returns:
            List of training samples (original_image_url, decision, reviewer_confidence, ...)
        """
        try:
            logger.debug(f"Fetching training data (min_samples={min_samples})")
            # Placeholder: query review_feedback table
            return []
        except Exception as e:
            logger.error(f"Failed to fetch training data: {e}")
            return []

    @staticmethod
    def _compute_priority(validation_score: float) -> int:
        """
        Auto-assign priority based on validation score.
        Lower scores = higher priority.
        
        Args:
            validation_score: 0-1 validation score
            
        Returns:
            Priority 1-5 (1=most urgent)
        """
        if validation_score < 0.40:
            return 1  # Urgent
        elif validation_score < 0.55:
            return 2  # High
        elif validation_score < 0.70:
            return 3  # Normal
        elif validation_score < 0.80:
            return 4  # Low
        else:
            return 5  # Very low


# ============================================================================
# Standalone example
# ============================================================================

def example_review_workflow():
    """Example showing review queue workflow."""
    print("=" * 70)
    print("Human-in-the-Loop Review Queue Example")
    print("=" * 70)

    # Mock queue
    queue = ReviewQueue(db_connection=None)

    print("\n1. Create review tasks for low-confidence images:")
    print("-" * 70)
    
    test_images = [
        {
            "product_id": 101,
            "product_image_id": 1001,
            "product_name": "Widget A",
            "vendor_code": "BRIT10G",
            "canonical_sku": "BRIT-BRIT10G",
            "image_url": "https://cdn/image1.jpg",
            "validation_score": 0.65,
            "reason": "Object coverage low (28% < 30%)",
        },
        {
            "product_id": 102,
            "product_image_id": 1002,
            "product_name": "Widget B",
            "vendor_code": "BRITC10G",
            "canonical_sku": "BRIT-BRITC10G-3F4E1A",
            "image_url": "https://cdn/image2.jpg",
            "validation_score": 0.72,
            "reason": "Background not entirely white",
        },
    ]

    for img in test_images:
        task_id = queue.create_review_task(
            product_id=img["product_id"],
            product_image_id=img["product_image_id"],
            product_name=img["product_name"],
            vendor_code=img["vendor_code"],
            canonical_sku=img["canonical_sku"],
            image_url=img["image_url"],
            validation_score=img["validation_score"],
            validation_checks={},
            failure_reason=img["reason"],
        )
        print(f"  Task {task_id}: {img['product_name']} ({img['canonical_sku']})")
        print(f"    Score: {img['validation_score']:.2f} | Reason: {img['reason']}")

    print("\n2. Reviewer reviews and makes decision:")
    print("-" * 70)
    print(f"  ✓ Reviewer 42 accepts task 1 (Widget A)")
    print(f"    Decision: ACCEPTED | Confidence: 5/5")
    print(f"  ✓ Reviewer 42 requires edit for task 2 (Widget B)")
    print(f"    Decision: REQUIRES_EDIT | Confidence: 4/5")
    print(f"    Notes: 'Please regenerate with higher resolution'")

    print("\n3. Queue Statistics:")
    print("-" * 70)
    stats = queue.get_queue_stats()
    print(f"  Pending tasks: 5")
    print(f"  In progress: 2")
    print(f"  SLA violations: 0")
    print(f"  Avg review time: 4.2 minutes")

    print("\n4. Reviewer Performance:")
    print("-" * 70)
    print(f"  Reviewer 42:")
    print(f"    Reviewed: 127")
    print(f"    Accepted: 89 (70%)")
    print(f"    Rejected: 23 (18%)")
    print(f"    Requires Edit: 15 (12%)")
    print(f"    Avg confidence: 4.6/5")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_review_workflow()
