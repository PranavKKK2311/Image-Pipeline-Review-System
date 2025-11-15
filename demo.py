#!/usr/bin/env python3
"""
Demo script: Run end-to-end examples of SKU generation and image validation
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.services.sku_generator import SKUGenerator, SKUStatus
from backend.services.image_validator import ImageValidator, ValidationStatus
from backend.services.review_queue import ReviewQueue, ReviewDecision


def demo_sku_generation():
    """Demo: Unique SKU generation for multi-vendor scenario"""
    print("\n" + "=" * 80)
    print("DEMO 1: Unique SKU Generation (Problem 1)")
    print("=" * 80)
    print("\nScenario: Two users submit similar codes for same product")
    print("  User 1 (British Imports): BRIT10G")
    print("  User 2 (Global Trade): BRITC10G")
    print("  Problem: Without unique SKU, codes clash\n")

    gen = SKUGenerator(db_connection=None)

    # User 1: British Imports vendor
    print("✓ User 1 submits: BRIT10G (vendor: BRIT)")
    sku1, status1 = gen.generate_sku(
        raw_code="BRIT10G",
        vendor_id=1,
        vendor_short="BRIT",
    )
    print(f"  Generated SKU: {sku1} (status: {status1.value})\n")

    # User 2: Global Trade vendor (same raw code normalized differently)
    print("✓ User 2 submits: BRITC10G (vendor: BRIT)")
    sku2, status2 = gen.generate_sku(
        raw_code="BRITC10G",
        vendor_id=1,
        vendor_short="BRIT",
    )
    print(f"  Generated SKU: {sku2} (status: {status2.value})\n")

    # Different vendors, same code
    print("✓ User 3 submits: BRIT10G (vendor: ACME)")
    sku3, status3 = gen.generate_sku(
        raw_code="BRIT10G",
        vendor_id=2,
        vendor_short="ACME",
    )
    print(f"  Generated SKU: {sku3} (status: {status3.value})\n")

    print("Summary:")
    print(f"  All SKUs unique: {len(set([sku1, sku2, sku3])) == 3}")
    print(f"  Vendor prefix prevents collisions: {sku1.split('-')[0] != sku3.split('-')[0]}")


def demo_image_validation():
    """Demo: Image validation with human-in-the-loop"""
    print("\n" + "=" * 80)
    print("DEMO 2: Image Validation & Human-in-the-Loop (Problem 2)")
    print("=" * 80)
    print("\nScenario: After code is accepted, image is generated for product")
    print("Problem: Generated image sometimes has issues (bad background, blur, coverage)")
    print("Solution: Automated validation with confidence scoring + human review\n")

    validator = ImageValidator(
        accept_score_threshold=0.85,
        review_score_threshold=0.70,
    )

    # Test scenarios
    scenarios = [
        {
            "name": "Perfect Product Image",
            "scores": {
                "background_white": 0.98,
                "blur": 0.95,
                "object_coverage": 0.85,
                "object_detection": 0.92,
                "perceptual_similarity": 0.98,
            },
            "expected": "auto_accepted",
        },
        {
            "name": "Slightly Imperfect Image",
            "scores": {
                "background_white": 0.88,
                "blur": 0.80,
                "object_coverage": 0.75,
                "object_detection": 0.80,
                "perceptual_similarity": 0.82,
            },
            "expected": "needs_review",
        },
        {
            "name": "Poor Quality Image",
            "scores": {
                "background_white": 0.40,
                "blur": 0.50,
                "object_coverage": 0.20,
                "object_detection": 0.55,
                "perceptual_similarity": 0.45,
            },
            "expected": "auto_rejected",
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        
        # Compute weighted score
        overall_score = (
            validator.weights["background_white"] * scenario["scores"]["background_white"]
            + validator.weights["blur"] * scenario["scores"]["blur"]
            + validator.weights["object_coverage"] * scenario["scores"]["object_coverage"]
            + validator.weights["object_detection"] * scenario["scores"]["object_detection"]
            + validator.weights["perceptual_similarity"] * scenario["scores"]["perceptual_similarity"]
        )

        # Determine status
        if overall_score >= validator.accept_score_threshold:
            status = ValidationStatus.AUTO_ACCEPTED
        elif overall_score >= validator.review_score_threshold:
            status = ValidationStatus.NEEDS_REVIEW
        else:
            status = ValidationStatus.AUTO_REJECTED

        print(f"   Background white: {scenario['scores']['background_white']:.2f}")
        print(f"   Blur: {scenario['scores']['blur']:.2f}")
        print(f"   Object coverage: {scenario['scores']['object_coverage']:.2f}")
        print(f"   Object detection: {scenario['scores']['object_detection']:.2f}")
        print(f"   Perceptual similarity: {scenario['scores']['perceptual_similarity']:.2f}")
        print(f"   ─────────────────────────")
        print(f"   Overall score: {overall_score:.2f}")
        print(f"   Status: {status.value.upper()}")
        
        if status.value != scenario["expected"]:
            print(f"   ⚠️ Expected: {scenario['expected']}")
        else:
            print(f"   ✓ Correct decision")
        print()


def demo_human_review_workflow():
    """Demo: Human review workflow and feedback capture"""
    print("\n" + "=" * 80)
    print("DEMO 3: Human-in-the-Loop Review Workflow")
    print("=" * 80)
    print("\nScenario: Image validation score is borderline (0.72)")
    print("Action: Send to human reviewer for decision\n")

    queue = ReviewQueue(db_connection=None)

    # Create review task
    print("✓ Image validation score: 0.72 (borderline)")
    print("✓ Creating review task...\n")

    task_id = queue.create_review_task(
        product_id=123,
        product_image_id=1001,
        product_name="Widget A",
        vendor_code="BRIT10G",
        canonical_sku="BRIT-BRIT10G",
        image_url="https://cdn/product_widget_a.jpg",
        validation_score=0.72,
        validation_checks={
            "background_white": 0.70,
            "blur": 0.85,
            "object_coverage": 0.75,
        },
        failure_reason="Borderline validation score (background white check slightly low)",
    )

    print(f"✓ Review task created: ID {task_id}")
    print(f"  Product: Widget A")
    print(f"  SKU: BRIT-BRIT10G")
    print(f"  Validation score: 0.72")
    print(f"  Reason: Borderline validation score (background white check slightly low)\n")

    # Simulate reviewer decisions
    print("─── Reviewer Dashboard ───")
    print("Task in review queue. Waiting for reviewer...\n")

    decisions = [
        {
            "decision": ReviewDecision.ACCEPTED,
            "confidence": 5,
            "notes": "Image looks good after closer inspection",
        },
        {
            "decision": ReviewDecision.REJECTED,
            "confidence": 4,
            "notes": "Background has slight discoloration at bottom right",
        },
        {
            "decision": ReviewDecision.REQUIRES_EDIT,
            "confidence": 3,
            "notes": "Product slightly cut off at top, please regenerate",
        },
    ]

    for i, dec in enumerate(decisions, 1):
        print(f"{i}. Reviewer Decision #{i}:")
        print(f"   Decision: {dec['decision'].value.upper()}")
        print(f"   Confidence: {dec['confidence']}/5")
        print(f"   Notes: {dec['notes']}")
        print()

    print("✓ Decision recorded")
    print("✓ Feedback saved for model training")
    print("✓ Image status updated\n")


def demo_integration_example():
    """Demo: Full integration example"""
    print("\n" + "=" * 80)
    print("DEMO 4: Full End-to-End Integration")
    print("=" * 80)
    print("\nScenario: New product received, SKU generated, image validated\n")

    gen = SKUGenerator(db_connection=None)
    validator = ImageValidator()
    queue = ReviewQueue(db_connection=None)

    # Step 1: Ingest new product
    print("Step 1: Product Ingestion")
    print("  Raw product code: BRIT10G")
    print("  Vendor: British Imports (BRIT)")
    print("  Product name: Industrial Widget\n")

    sku, sku_status = gen.generate_sku(
        raw_code="BRIT10G",
        vendor_id=100,
        vendor_short="BRIT",
    )
    print(f"  ✓ Canonical SKU generated: {sku}\n")

    # Step 2: Generate and validate image
    print("Step 2: Image Generation & Validation")
    print("  Image generated by AI/ML model...")
    print("  Running validation checks...\n")

    # Simulated validation result
    validation_score = 0.89
    validation_status = (
        ValidationStatus.AUTO_ACCEPTED
        if validation_score >= 0.85
        else ValidationStatus.NEEDS_REVIEW
    )

    print(f"  Validation score: {validation_score:.2f}")
    print(f"  Status: {validation_status.value}\n")

    if validation_status == ValidationStatus.AUTO_ACCEPTED:
        print("  ✓ Auto-accepted (high confidence)")
        print("  ✓ Image stored in product catalog\n")
    else:
        print(f"  ⚠️ Status: {validation_status.value}")
        print("  ✓ Creating review task for human decision...\n")

    # Step 3: Success
    print("Step 3: Product Ready")
    print(f"  ✓ Product SKU: {sku}")
    print(f"  ✓ Product image: {validation_status.value}")
    print(f"  ✓ Ready for catalog/ecommerce\n")


def main():
    """Run all demos"""
    print("\n" + "█" * 80)
    print("█  SKU & Image Validation Pipeline - Interactive Demo")
    print("█  Version 1.0")
    print("█" * 80)

    try:
        demo_sku_generation()
        demo_image_validation()
        demo_human_review_workflow()
        demo_integration_example()

        print("\n" + "=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print("\nNext Steps:")
        print("1. Review the code in backend/services/")
        print("2. Review database schema in backend/migrations/001_initial_schema.sql")
        print("3. Start API server: python backend/main.py")
        print("4. Explore API endpoints at http://localhost:8000/docs")
        print("5. Run tests: pytest tests/ -v")
        print("6. Deploy reviewer UI from frontend/")
        print("\nDocumentation:")
        print("  - README.md: Project overview")
        print("  - INTEGRATION_GUIDE.md: Integration steps")
        print("  - backend/config.py: Configuration options")
        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
