"""
Image Validator: Solves Problem 2 - Automated image quality checks with human-in-the-loop

Key features:
- White background detection
- Blur detection
- Object coverage analysis
- Perceptual hash similarity
- Weighted scoring for accept/reject/review decisions
- Audit logging of all validation checks
"""

import logging
from typing import Tuple, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
import os
import hashlib

try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    np = None

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Image validation status"""
    AUTO_ACCEPTED = "auto_accepted"
    AUTO_REJECTED = "auto_rejected"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"


@dataclass
class ValidationChecks:
    """Result of all validation checks"""
    background_white: bool
    blur: bool
    object_coverage: bool
    object_detection: bool
    perceptual_similarity: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationMetrics:
    """Detailed metrics from validation"""
    background_white_score: float  # 0-1, pct of white border pixels
    blur_score: float              # 0-1, Laplacian variance
    object_coverage: float         # 0-1, pct of image covered by object
    perceptual_similarity: float   # 0-1, pHash similarity
    overall_score: float           # 0-1, weighted average
    status: ValidationStatus
    reason: str
    execution_time_ms: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {**asdict(self), "status": self.status.value}


class ImageValidator:
    """
    Validates product images for quality and correctness.
    
    Validation pipeline:
    1. Load image and extract metadata
    2. Check white background (border sampling)
    3. Detect blur (Laplacian variance)
    4. Analyze object coverage (foreground segmentation)
    5. Optional: ML object detection
    6. Optional: Perceptual hash similarity to reference
    7. Combine scores using weighted average
    8. Return: status (auto-accept/reject/review) + detailed metrics
    
    Example:
        validator = ImageValidator(
            background_white_threshold=0.95,
            blur_threshold=100.0,
            object_coverage_min=0.30,
            object_coverage_max=0.90,
        )
        
        metrics = validator.validate_image("product_image.jpg", reference_image=None)
        
        if metrics.status == ValidationStatus.AUTO_ACCEPTED:
            print(f"Auto-accepted with score {metrics.overall_score}")
        else:
            print(f"Needs human review: {metrics.reason}")
    """

    def __init__(
        self,
        background_white_threshold: float = 0.95,
        background_white_tolerance: int = 10,
        background_white_border_px: int = 10,
        blur_threshold: float = 100.0,
        object_coverage_min: float = 0.30,
        object_coverage_max: float = 0.90,
        perceptual_hash_min_similarity: float = 0.70,
        weights: Optional[Dict[str, float]] = None,
        accept_score_threshold: float = 0.85,
        review_score_threshold: float = 0.70,
    ):
        """
        Initialize image validator.
        
        Args:
            background_white_threshold: % of border pixels that should be white
            background_white_tolerance: RGB distance tolerance to white (255,255,255)
            background_white_border_px: Pixels from edge to sample
            blur_threshold: Laplacian variance threshold (higher = less blurry)
            object_coverage_min: Minimum object coverage (fraction of image)
            object_coverage_max: Maximum object coverage (fraction of image)
            perceptual_hash_min_similarity: pHash similarity threshold (0-1)
            weights: Dict of check weights (must sum to 1.0)
            accept_score_threshold: Score >= this -> auto-accept
            review_score_threshold: Score < this -> escalate (between accept and review thresholds -> needs_review)
        """
        if not PIL_AVAILABLE:
            logger.warning("Pillow not available; some checks will be disabled")
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available; some checks will be disabled")
        if not IMAGEHASH_AVAILABLE:
            logger.warning("imagehash not available; perceptual similarity disabled")

        self.background_white_threshold = background_white_threshold
        self.background_white_tolerance = background_white_tolerance
        self.background_white_border_px = background_white_border_px
        self.blur_threshold = blur_threshold
        self.object_coverage_min = object_coverage_min
        self.object_coverage_max = object_coverage_max
        self.perceptual_hash_min_similarity = perceptual_hash_min_similarity
        self.accept_score_threshold = accept_score_threshold
        self.review_score_threshold = review_score_threshold

        # Default weights for scoring
        self.weights = weights or {
            "background_white": 0.25,
            "blur": 0.15,
            "object_coverage": 0.25,
            "object_detection": 0.20,
            "perceptual_similarity": 0.15,
        }

        # Validate weights sum to 1.0
        if abs(sum(self.weights.values()) - 1.0) > 0.001:
            logger.warning(f"Weights do not sum to 1.0: {sum(self.weights.values())}")

    def validate_image(
        self,
        image_path: str,
        reference_image_path: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> ValidationMetrics:
        """
        Run full validation pipeline on image.
        
        Args:
            image_path: Path to product image file
            reference_image_path: Optional reference image for perceptual similarity
            execution_context: Optional metadata (e.g., product_id, attempt number)
            
        Returns:
            ValidationMetrics with overall score and decision
        """
        import time
        start_time = time.time()
        
        try:
            # Check file exists
            if not os.path.exists(image_path):
                return ValidationMetrics(
                    background_white_score=0.0,
                    blur_score=0.0,
                    object_coverage=0.0,
                    perceptual_similarity=0.0,
                    overall_score=0.0,
                    status=ValidationStatus.ERROR,
                    reason="Image file not found",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Run individual checks
            background_score = self._check_background_white(image_path)
            blur_score = self._check_blur(image_path)
            coverage_score, is_coverage_ok = self._check_object_coverage(image_path)
            detection_score = self._check_object_detection(image_path)
            similarity_score = 1.0  # Default to perfect if no reference
            if reference_image_path:
                similarity_score = self._check_perceptual_similarity(image_path, reference_image_path)

            # Compute weighted overall score
            overall_score = (
                self.weights["background_white"] * background_score
                + self.weights["blur"] * blur_score
                + self.weights["object_coverage"] * coverage_score
                + self.weights["object_detection"] * detection_score
                + self.weights["perceptual_similarity"] * similarity_score
            )

            # Determine status
            if overall_score >= self.accept_score_threshold:
                status = ValidationStatus.AUTO_ACCEPTED
                reason = "All checks passed"
            elif overall_score >= self.review_score_threshold:
                status = ValidationStatus.NEEDS_REVIEW
                reason = f"Score {overall_score:.2f} is borderline; requires human review"
            else:
                status = ValidationStatus.AUTO_REJECTED
                reason = f"Score {overall_score:.2f} below review threshold"

            # Log individual check results for debugging
            logger.info(
                f"Validation complete: {image_path} | "
                f"bg={background_score:.2f} blur={blur_score:.2f} "
                f"coverage={coverage_score:.2f} detect={detection_score:.2f} "
                f"sim={similarity_score:.2f} | overall={overall_score:.2f} | {status.value}"
            )

            return ValidationMetrics(
                background_white_score=background_score,
                blur_score=blur_score,
                object_coverage=coverage_score,
                perceptual_similarity=similarity_score,
                overall_score=overall_score,
                status=status,
                reason=reason,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.error(f"Validation error for {image_path}: {e}", exc_info=True)
            return ValidationMetrics(
                background_white_score=0.0,
                blur_score=0.0,
                object_coverage=0.0,
                perceptual_similarity=0.0,
                overall_score=0.0,
                status=ValidationStatus.ERROR,
                reason=f"Validation error: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _check_background_white(self, image_path: str) -> float:
        """
        Check if background is white (sample border pixels).
        
        Returns:
            Score 0-1 (fraction of border pixels that are white)
        """
        if not PIL_AVAILABLE:
            logger.warning("Pillow not available; skipping background check")
            return 0.5

        try:
            im = Image.open(image_path).convert('RGB')
            w, h = im.size
            arr = np.array(im)

            # Sample four borders
            border_px = self.background_white_border_px
            top = arr[:border_px, :, :].reshape(-1, 3)
            bottom = arr[-border_px:, :, :].reshape(-1, 3)
            left = arr[:, :border_px, :].reshape(-1, 3)
            right = arr[:, -border_px:, :].reshape(-1, 3)
            samples = np.vstack([top, bottom, left, right])

            # Compute distance to white (255, 255, 255)
            white = np.array([255, 255, 255])
            dist = np.linalg.norm(samples - white, axis=1)
            pct_white = (dist < self.background_white_tolerance).mean()

            logger.debug(f"Background white check: {pct_white:.2%} of border pixels white")
            return pct_white
        except Exception as e:
            logger.error(f"Background white check failed: {e}")
            return 0.5

    def _check_blur(self, image_path: str) -> float:
        """
        Detect blur using Laplacian variance.
        
        Returns:
            Score 0-1 (1 = not blurry, 0 = very blurry)
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available; skipping blur check")
            return 0.5

        try:
            im = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if im is None:
                logger.warning(f"Could not read image for blur check: {image_path}")
                return 0.5

            lap = cv2.Laplacian(im, cv2.CV_64F)
            var = lap.var()

            # Normalize: map Laplacian variance to 0-1 score
            # Assume threshold at blur_threshold; scores below are blurry
            score = min(1.0, var / self.blur_threshold)
            logger.debug(f"Blur check: Laplacian variance={var:.2f}, score={score:.2f}")
            return score
        except Exception as e:
            logger.error(f"Blur check failed: {e}")
            return 0.5

    def _check_object_coverage(self, image_path: str) -> Tuple[float, bool]:
        """
        Analyze object coverage using simple contour detection.
        Works best with high-contrast foreground (product) against white background.
        
        Returns:
            Tuple of (score 0-1, is_coverage_ok boolean)
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available; skipping coverage check")
            return 0.5, True

        try:
            im = cv2.imread(image_path)
            if im is None:
                logger.warning(f"Could not read image for coverage check: {image_path}")
                return 0.5, True

            gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            # Inverse binary: white background (250+) becomes 0, product becomes 1
            _, th = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                logger.warning(f"No foreground contours detected: {image_path}")
                return 0.0, False

            # Find largest contour area
            area = max(cv2.contourArea(c) for c in contours)
            total_area = im.shape[0] * im.shape[1]
            coverage = area / total_area

            # Score based on min/max thresholds
            if coverage < self.object_coverage_min:
                score = coverage / self.object_coverage_min * 0.5  # Score up to 0.5
                is_ok = False
            elif coverage > self.object_coverage_max:
                score = max(0.0, 1.0 - (coverage - self.object_coverage_max) / (1.0 - self.object_coverage_max) * 0.5)
                is_ok = False
            else:
                score = 1.0
                is_ok = True

            logger.debug(f"Object coverage: {coverage:.2%}, score={score:.2f}, ok={is_ok}")
            return score, is_ok
        except Exception as e:
            logger.error(f"Object coverage check failed: {e}")
            return 0.5, True

    def _check_object_detection(self, image_path: str) -> float:
        """
        Placeholder for ML object detection (e.g., using YOLO, MobileNet-SSD).
        For now, return a neutral score (0.7) since detection is complex.
        
        In production, integrate with your ML model:
        - Load pretrained detector (YOLO, SSD, etc.)
        - Detect products in image
        - Verify exactly one object detected
        - Return high score if single object with good confidence, low if multiple/none
        
        Returns:
            Score 0-1
        """
        logger.debug(f"Object detection (placeholder): returning neutral score")
        return 0.7

    def _check_perceptual_similarity(
        self, image_path: str, reference_image_path: str
    ) -> float:
        """
        Compare two images using perceptual hash (pHash).
        Useful if you have a reference product image or expected visual attributes.
        
        Returns:
            Score 0-1 (similarity), 1.0 = identical, 0.0 = very different
        """
        if not IMAGEHASH_AVAILABLE:
            logger.warning("imagehash not available; returning neutral score")
            return 0.7

        try:
            if not os.path.exists(reference_image_path):
                logger.warning(f"Reference image not found: {reference_image_path}")
                return 0.7

            h1 = imagehash.phash(Image.open(image_path))
            h2 = imagehash.phash(Image.open(reference_image_path))

            # Normalized similarity (hash size in bits, typically 64 for pHash)
            maxbits = h1.hash.size
            diff = (h1 - h2)
            similarity = 1.0 - (diff / maxbits)

            logger.debug(f"Perceptual similarity: {similarity:.2f}")
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.error(f"Perceptual similarity check failed: {e}")
            return 0.7

    @staticmethod
    def compute_image_hash(image_path: str) -> str:
        """
        Compute SHA256 hash of image file for deduplication.
        
        Args:
            image_path: Path to image
            
        Returns:
            Hex string of SHA256 hash
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(image_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute image hash: {e}")
            return ""


# ============================================================================
# Standalone examples
# ============================================================================

def example_image_validation():
    """Example showing image validation pipeline."""
    print("=" * 70)
    print("Image Validator Example")
    print("=" * 70)

    validator = ImageValidator(
        background_white_threshold=0.95,
        blur_threshold=100.0,
        object_coverage_min=0.30,
        object_coverage_max=0.90,
        accept_score_threshold=0.85,
        review_score_threshold=0.70,
    )

    # Simulated validation results (since we don't have actual images)
    test_images = [
        ("perfect_product.jpg", {"result": "Auto-accepted", "score": 0.92}),
        ("slightly_blurry.jpg", {"result": "Needs review", "score": 0.78}),
        ("bad_background.jpg", {"result": "Auto-rejected", "score": 0.55}),
        ("missing_object.jpg", {"result": "Auto-rejected", "score": 0.40}),
    ]

    print("\nValidation Results:")
    print("-" * 70)
    for image_name, expected in test_images:
        print(f"\n  Image: {image_name}")
        print(f"  Expected: {expected['result']} (score={expected['score']})")
        print(f"  Status: {ValidationStatus.AUTO_ACCEPTED.value if expected['score'] >= 0.85 else ValidationStatus.NEEDS_REVIEW.value if expected['score'] >= 0.70 else ValidationStatus.AUTO_REJECTED.value}")

    print("\n" + "=" * 70)
    print("Configuration:")
    print(f"  Auto-accept threshold: 0.85")
    print(f"  Human-review threshold: 0.70")
    print(f"  Score < 0.70: Auto-rejected")
    print("=" * 70)


if __name__ == "__main__":
    # Check availability of required libraries
    print(f"PIL/Pillow available: {PIL_AVAILABLE}")
    print(f"OpenCV available: {CV2_AVAILABLE}")
    print(f"imagehash available: {IMAGEHASH_AVAILABLE}")
    print()
    example_image_validation()
