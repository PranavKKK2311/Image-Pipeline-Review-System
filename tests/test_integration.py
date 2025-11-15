"""
Integration tests for full SKU & Image validation pipeline
"""

import pytest
from backend.services.sku_generator import SKUGenerator, SKUStatus
from backend.services.image_validator import ImageValidator, ValidationStatus
from backend.services.review_queue import ReviewQueue, ReviewDecision


class TestEndToEndPipeline:
    """End-to-end integration tests"""

    def test_product_ingest_with_sku_and_validation(self):
        """
        Full workflow:
        1. Receive product with code
        2. Generate unique SKU
        3. Generate/validate image
        4. Create human review task if needed
        """
        # Step 1: Initialize
        sku_gen = SKUGenerator(db_connection=None)
        validator = ImageValidator()
        queue = ReviewQueue(db_connection=None)

        # Step 2: Generate SKU for new product
        raw_code = "BRIT10G"
        vendor_id = 100
        vendor_short = "BRIT"
        
        canonical_sku, sku_status = sku_gen.generate_sku(
            raw_code=raw_code,
            vendor_id=vendor_id,
            vendor_short=vendor_short,
        )

        assert canonical_sku == "BRIT-BRIT10G"
        assert sku_status == SKUStatus.INSERTED

        # Step 3: Validate product image (simulated)
        # In real scenario, we'd validate actual image file
        validation_score = 0.87  # Simulated score
        validation_status = (
            ValidationStatus.AUTO_ACCEPTED
            if validation_score >= 0.85
            else ValidationStatus.NEEDS_REVIEW
        )

        assert validation_status == ValidationStatus.AUTO_ACCEPTED
        assert validation_score >= 0.85

    def test_collision_resolution_workflow(self):
        """
        Scenario: Two users submit similar codes
        User 1: BRIT10G
        User 2: BRITC10G (same vendor)
        
        Expected: Both get unique SKUs without collision
        """
        gen = SKUGenerator(db_connection=None)

        sku1, status1 = gen.generate_sku(
            raw_code="BRIT10G",
            vendor_id=100,
            vendor_short="BRIT",
        )

        sku2, status2 = gen.generate_sku(
            raw_code="BRITC10G",
            vendor_id=100,
            vendor_short="BRIT",
        )

        # Both should start with vendor prefix
        assert sku1.startswith("BRIT-")
        assert sku2.startswith("BRIT-")
        
        # They should normalize differently
        assert "BRIT10G" in sku1
        assert "BRITC10G" in sku2

    def test_image_validation_to_human_review_workflow(self):
        """
        Scenario: Image fails validation and goes to human review
        1. Image has low validation score (0.72)
        2. Create review task
        3. Reviewer makes decision
        4. Store feedback
        """
        validator = ImageValidator(
            accept_score_threshold=0.85,
            review_score_threshold=0.70,
        )
        queue = ReviewQueue(db_connection=None)

        # Simulated validation result
        validation_score = 0.72
        
        # Determine status
        if validation_score >= validator.accept_score_threshold:
            status = ValidationStatus.AUTO_ACCEPTED
        elif validation_score >= validator.review_score_threshold:
            status = ValidationStatus.NEEDS_REVIEW
        else:
            status = ValidationStatus.AUTO_REJECTED

        assert status == ValidationStatus.NEEDS_REVIEW

        # Create review task
        task_id = queue.create_review_task(
            product_id=123,
            product_image_id=1001,
            product_name="Test Product",
            vendor_code="BRIT10G",
            canonical_sku="BRIT-BRIT10G",
            image_url="https://cdn/image.jpg",
            validation_score=validation_score,
            validation_checks={},
            failure_reason="Borderline validation score",
        )

        assert task_id > 0

        # Reviewer submits decision
        result = queue.submit_review_decision(
            review_task_id=task_id,
            decision=ReviewDecision.ACCEPTED,
            reviewer_id=42,
            reviewer_confidence=4,
        )

        assert result is True


class TestMultiVendorScenario:
    """Test multi-vendor product ingest"""

    def test_multiple_vendors_same_code_no_collision(self):
        """
        Multiple vendors submit "PRODUCT10" code
        Each should get unique SKU without collision
        """
        gen = SKUGenerator(db_connection=None)

        vendors = [
            ("British Imports", "BRIT", 1),
            ("Acme Corp", "ACME", 2),
            ("Global Trade", "GLOB", 3),
        ]

        skus_generated = {}
        
        for vendor_name, vendor_short, vendor_id in vendors:
            sku, status = gen.generate_sku(
                raw_code="PRODUCT10",
                vendor_id=vendor_id,
                vendor_short=vendor_short,
            )
            
            assert sku not in skus_generated, f"SKU {sku} collision detected!"
            skus_generated[sku] = vendor_name

        # All SKUs should be unique
        assert len(skus_generated) == len(vendors)
        
        # Each should have correct vendor prefix
        assert "BRIT-" in list(skus_generated.keys())[0]
        print(f"Generated unique SKUs for {len(vendors)} vendors: {list(skus_generated.keys())}")


class TestImageValidationThresholds:
    """Test different validation score thresholds"""

    def test_threshold_configurations(self):
        """Test different threshold configurations"""
        configs = [
            {"accept": 0.90, "review": 0.75},  # Strict
            {"accept": 0.85, "review": 0.70},  # Moderate (default)
            {"accept": 0.75, "review": 0.60},  # Lenient
        ]

        test_scores = [0.65, 0.72, 0.78, 0.88, 0.95]

        for config in configs:
            validator = ImageValidator(
                accept_score_threshold=config["accept"],
                review_score_threshold=config["review"],
            )

            print(f"\nConfiguration: accept={config['accept']}, review={config['review']}")
            for score in test_scores:
                if score >= validator.accept_score_threshold:
                    status = ValidationStatus.AUTO_ACCEPTED
                elif score >= validator.review_score_threshold:
                    status = ValidationStatus.NEEDS_REVIEW
                else:
                    status = ValidationStatus.AUTO_REJECTED

                print(f"  Score {score:.2f}: {status.value}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
