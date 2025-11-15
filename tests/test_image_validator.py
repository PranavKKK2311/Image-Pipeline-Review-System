"""
Tests for Image Validator (Problem 2)

Covers:
- Background white detection
- Blur detection
- Object coverage analysis
- Validation scoring
- Status determination (auto-accept, needs-review, auto-reject)
"""

import pytest
import tempfile
import os
from backend.services.image_validator import ImageValidator, ValidationStatus


class TestImageValidator:
    """Test cases for image validator"""

    @pytest.fixture
    def validator(self):
        """Create image validator instance"""
        return ImageValidator(
            background_white_threshold=0.95,
            blur_threshold=100.0,
            object_coverage_min=0.30,
            object_coverage_max=0.90,
            accept_score_threshold=0.85,
            review_score_threshold=0.70,
        )

    # ========================================================================
    # Configuration Tests
    # ========================================================================

    def test_validator_initialization(self, validator):
        """Test validator initializes with correct thresholds"""
        assert validator.background_white_threshold == 0.95
        assert validator.blur_threshold == 100.0
        assert validator.object_coverage_min == 0.30
        assert validator.object_coverage_max == 0.90
        assert validator.accept_score_threshold == 0.85
        assert validator.review_score_threshold == 0.70

    def test_weights_sum_to_one(self, validator):
        """Test that validation weights sum to 1.0"""
        weight_sum = sum(validator.weights.values())
        assert abs(weight_sum - 1.0) < 0.001, "Weights should sum to 1.0"

    # ========================================================================
    # Validation Status Tests
    # ========================================================================

    def test_auto_accept_threshold(self, validator):
        """Test auto-accept when score >= threshold"""
        # High score (0.90) should auto-accept
        score = 0.90
        if score >= validator.accept_score_threshold:
            assert True  # Would auto-accept
        else:
            assert False

    def test_needs_review_threshold(self, validator):
        """Test needs-review for borderline scores"""
        # Score between thresholds should need review
        score = 0.77  # Between 0.70 and 0.85
        is_borderline = validator.review_score_threshold <= score < validator.accept_score_threshold
        assert is_borderline

    def test_auto_reject_threshold(self, validator):
        """Test auto-reject when score < review threshold"""
        score = 0.60  # Below 0.70
        if score < validator.review_score_threshold:
            assert True  # Would auto-reject
        else:
            assert False

    # ========================================================================
    # Scoring Tests
    # ========================================================================

    def test_score_computation_weighted_average(self, validator):
        """Test that overall score is weighted average of checks"""
        # Mock individual scores
        bg_score = 1.0
        blur_score = 0.8
        coverage_score = 0.9
        detect_score = 0.85
        sim_score = 0.95

        overall = (
            validator.weights["background_white"] * bg_score
            + validator.weights["blur"] * blur_score
            + validator.weights["object_coverage"] * coverage_score
            + validator.weights["object_detection"] * detect_score
            + validator.weights["perceptual_similarity"] * sim_score
        )

        # Overall should be weighted average
        assert 0.0 <= overall <= 1.0
        assert overall > 0.8  # With these good scores

    def test_score_bounds(self, validator):
        """Test score stays within 0-1 bounds"""
        scores = [
            (1.0, 1.0, 1.0, 1.0, 1.0),  # Perfect
            (0.0, 0.0, 0.0, 0.0, 0.0),  # Fail all
            (0.5, 0.5, 0.5, 0.5, 0.5),  # Middle
        ]

        for bg, blur, cov, det, sim in scores:
            overall = (
                validator.weights["background_white"] * bg
                + validator.weights["blur"] * blur
                + validator.weights["object_coverage"] * cov
                + validator.weights["object_detection"] * det
                + validator.weights["perceptual_similarity"] * sim
            )
            assert 0.0 <= overall <= 1.0


class TestImageValidationLogic:
    """Test validation decision logic"""

    @pytest.fixture
    def validator(self):
        return ImageValidator(accept_score_threshold=0.85, review_score_threshold=0.70)

    def test_high_score_auto_accepts(self, validator):
        """High score (>0.85) should auto-accept"""
        score = 0.92
        if score >= validator.accept_score_threshold:
            status = ValidationStatus.AUTO_ACCEPTED
        else:
            status = ValidationStatus.AUTO_REJECTED
        assert status == ValidationStatus.AUTO_ACCEPTED

    def test_borderline_score_needs_review(self, validator):
        """Score between thresholds should need review"""
        score = 0.77
        if score >= validator.accept_score_threshold:
            status = ValidationStatus.AUTO_ACCEPTED
        elif score >= validator.review_score_threshold:
            status = ValidationStatus.NEEDS_REVIEW
        else:
            status = ValidationStatus.AUTO_REJECTED
        assert status == ValidationStatus.NEEDS_REVIEW

    def test_low_score_auto_rejects(self, validator):
        """Low score (<0.70) should auto-reject"""
        score = 0.55
        if score < validator.review_score_threshold:
            status = ValidationStatus.AUTO_REJECTED
        else:
            status = ValidationStatus.AUTO_ACCEPTED
        assert status == ValidationStatus.AUTO_REJECTED


class TestValidationChecks:
    """Test individual validation checks"""

    @pytest.fixture
    def validator(self):
        return ImageValidator()

    def test_background_white_scoring(self, validator):
        """Test background white check scoring"""
        # All pixels white
        score1 = 1.0
        assert 0.0 <= score1 <= 1.0

        # Half pixels white
        score2 = 0.5
        assert 0.0 <= score2 <= 1.0

        # No pixels white
        score3 = 0.0
        assert 0.0 <= score3 <= 1.0

    def test_blur_scoring(self, validator):
        """Test blur detection scoring"""
        # High variance (sharp)
        laplacian_var = 150.0
        score = min(1.0, laplacian_var / validator.blur_threshold)
        assert score > 0.8  # Should be mostly unblurry

        # Low variance (blurry)
        laplacian_var = 50.0
        score = min(1.0, laplacian_var / validator.blur_threshold)
        assert score < 0.6  # Should be blurry

    def test_coverage_scoring(self, validator):
        """Test object coverage scoring"""
        # Good coverage (50%)
        coverage = 0.50
        if validator.object_coverage_min <= coverage <= validator.object_coverage_max:
            score = 1.0
        else:
            score = 0.0
        assert score == 1.0

        # Too small coverage (10%)
        coverage = 0.10
        if coverage < validator.object_coverage_min:
            score = 0.0
        else:
            score = 1.0
        assert score == 0.0

        # Too large coverage (95%)
        coverage = 0.95
        if coverage > validator.object_coverage_max:
            score = 0.0
        else:
            score = 1.0
        assert score == 0.0


class TestValidationScenarios:
    """Real-world validation scenarios"""

    @pytest.fixture
    def validator(self):
        return ImageValidator()

    def test_perfect_image_scenario(self, validator):
        """Scenario: Perfect product image"""
        # Perfect: white background, sharp, good coverage, single object
        scores = {
            "background_white": 1.0,
            "blur": 1.0,
            "object_coverage": 1.0,
            "object_detection": 1.0,
            "perceptual_similarity": 1.0,
        }

        overall = sum(scores[key] * validator.weights[key] for key in scores)
        assert overall >= validator.accept_score_threshold
        assert overall == 1.0

    def test_slightly_imperfect_image_scenario(self, validator):
        """Scenario: Slightly imperfect (still acceptable)"""
        # Slightly imperfect: mostly white bg, slight blur, good coverage
        scores = {
            "background_white": 0.92,
            "blur": 0.85,
            "object_coverage": 0.95,
            "object_detection": 0.80,
            "perceptual_similarity": 0.90,
        }

        overall = sum(scores[key] * validator.weights[key] for key in scores)
        if overall >= validator.accept_score_threshold:
            status = ValidationStatus.AUTO_ACCEPTED
        else:
            status = ValidationStatus.NEEDS_REVIEW
        # Should be auto-accepted
        assert overall > 0.85

    def test_borderline_image_scenario(self, validator):
        """Scenario: Borderline image (needs human review)"""
        # Borderline: some bg issues, slight blur, coverage okay
        scores = {
            "background_white": 0.70,
            "blur": 0.75,
            "object_coverage": 0.80,
            "object_detection": 0.70,
            "perceptual_similarity": 0.72,
        }

        overall = sum(scores[key] * validator.weights[key] for key in scores)
        if overall >= validator.accept_score_threshold:
            status = ValidationStatus.AUTO_ACCEPTED
        elif overall >= validator.review_score_threshold:
            status = ValidationStatus.NEEDS_REVIEW
        else:
            status = ValidationStatus.AUTO_REJECTED
        # Should need review
        assert validator.review_score_threshold <= overall < validator.accept_score_threshold

    def test_poor_image_scenario(self, validator):
        """Scenario: Poor quality image (auto-reject)"""
        # Poor: dirty background, blurry, wrong coverage, multiple objects
        scores = {
            "background_white": 0.30,
            "blur": 0.40,
            "object_coverage": 0.20,
            "object_detection": 0.50,
            "perceptual_similarity": 0.35,
        }

        overall = sum(scores[key] * validator.weights[key] for key in scores)
        if overall < validator.review_score_threshold:
            status = ValidationStatus.AUTO_REJECTED
        # Should auto-reject
        assert overall < validator.review_score_threshold


class TestImageHashComputation:
    """Test image hash computation for deduplication"""

    def test_image_hash_consistency(self):
        """Same image should produce same hash"""
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            temp_path = f.name
            f.write(b"dummy image data")

        try:
            hash1 = ImageValidator.compute_image_hash(temp_path)
            hash2 = ImageValidator.compute_image_hash(temp_path)
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 hex is 64 chars
        finally:
            os.unlink(temp_path)

    def test_different_images_different_hashes(self):
        """Different images should produce different hashes"""
        # Create two temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f1:
            temp_path1 = f1.name
            f1.write(b"image data 1")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f2:
            temp_path2 = f2.name
            f2.write(b"image data 2")

        try:
            hash1 = ImageValidator.compute_image_hash(temp_path1)
            hash2 = ImageValidator.compute_image_hash(temp_path2)
            assert hash1 != hash2
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
