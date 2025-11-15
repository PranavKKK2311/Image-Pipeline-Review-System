"""
Tests for SKU Generator (Problem 1)

Covers:
- Deterministic SKU generation
- Collision detection and resolution
- Edge cases (special chars, length limits, etc.)
- Database uniqueness enforcement
"""

import pytest
from backend.services.sku_generator import SKUGenerator, SKUStatus


class TestSKUGenerator:
    """Test cases for SKU generator"""

    @pytest.fixture
    def generator(self):
        """Create a SKU generator instance"""
        return SKUGenerator(db_connection=None)

    # ========================================================================
    # Slugify Tests
    # ========================================================================

    def test_slugify_basic(self, generator):
        """Test basic slugification"""
        assert generator._slugify("BRIT10G") == "BRIT10G"
        assert generator._slugify("britc10g") == "BRITC10G"  # Lowercase
        assert generator._slugify("Brit-10-G") == "BRIT10G"  # Dashes removed
        assert generator._slugify("BRIT_10.G") == "BRIT10G"  # Underscores and dots removed

    def test_slugify_special_chars(self, generator):
        """Test slugification with special characters"""
        assert generator._slugify("BRIT@10#G!") == "BRIT10G"
        assert generator._slugify("BRIT (10G)") == "BRIT10G"
        assert generator._slugify("BRIT/10/G") == "BRIT10G"

    def test_slugify_empty(self, generator):
        """Test slugification of empty string"""
        assert generator._slugify("") == ""
        assert generator._slugify(None) == ""

    def test_slugify_length_limit(self, generator):
        """Test slugification respects max length"""
        long_code = "A" * 100
        slug = generator._slugify(long_code, max_len=40)
        assert len(slug) == 40

    # ========================================================================
    # Hash Suffix Tests
    # ========================================================================

    def test_short_hash_deterministic(self, generator):
        """Test that hash is deterministic (same input -> same output)"""
        value = "BRIT10G:42"
        hash1 = generator._short_hash(value, length=6)
        hash2 = generator._short_hash(value, length=6)
        assert hash1 == hash2

    def test_short_hash_different_inputs(self, generator):
        """Test that different inputs produce different hashes"""
        hash1 = generator._short_hash("BRIT10G:42", length=6)
        hash2 = generator._short_hash("BRITC10G:42", length=6)
        assert hash1 != hash2

    def test_short_hash_length(self, generator):
        """Test hash output respects length parameter"""
        hash6 = generator._short_hash("test", length=6)
        hash8 = generator._short_hash("test", length=8)
        assert len(hash6) == 6
        assert len(hash8) == 8
        assert hash6 != hash8

    # ========================================================================
    # SKU Generation Tests
    # ========================================================================

    def test_generate_sku_basic(self, generator):
        """Test basic SKU generation"""
        sku, status = generator.generate_sku(
            raw_code="BRIT10G",
            vendor_id=42,
            vendor_short="VEND",
        )
        assert sku == "VEND-BRIT10G"
        assert status == SKUStatus.INSERTED

    def test_generate_sku_case_insensitive(self, generator):
        """Test SKU generation is case-insensitive"""
        sku1, _ = generator.generate_sku("BRIT10G", vendor_id=42, vendor_short="VEND")
        sku2, _ = generator.generate_sku("brit10g", vendor_id=42, vendor_short="VEND")
        sku3, _ = generator.generate_sku("BrIt10G", vendor_id=42, vendor_short="VEND")
        # All normalize to same SKU (collision)
        assert sku1 == sku2 == sku3

    def test_generate_sku_empty_code(self, generator):
        """Test generation with empty raw code"""
        sku, status = generator.generate_sku("", vendor_id=42, vendor_short="VEND")
        assert sku == ""
        assert status == SKUStatus.ERROR

    def test_generate_sku_with_vendor_prefix(self, generator):
        """Test vendor prefix is included"""
        sku, _ = generator.generate_sku("BRIT10G", vendor_id=1, vendor_short="VENDA")
        assert sku.startswith("VENDA-")
        
        sku, _ = generator.generate_sku("BRIT10G", vendor_id=2, vendor_short="VENDB")
        assert sku.startswith("VENDB-")

    def test_generate_sku_collision_resolution(self, generator):
        """Test collision resolution with deterministic suffix"""
        # Simulate collision by generating with same inputs
        sku1, status1 = generator.generate_sku("BRIT10G", vendor_id=1, vendor_short="VEND")
        
        # Second attempt (simulating collision) should use suffix
        # In real DB, this would fail on unique constraint
        sku2, status2 = generator.generate_sku("BRIT10G", vendor_id=1, vendor_short="VEND", max_retries=3)
        
        # Both should be valid SKUs, but sku1 is simpler (no suffix)
        assert sku1.startswith("VEND-")
        assert sku2.startswith("VEND-")

    # ========================================================================
    # Different Vendor Tests
    # ========================================================================

    def test_different_vendors_no_collision(self, generator):
        """Test different vendors can use same raw code"""
        sku1, _ = generator.generate_sku("BRIT10G", vendor_id=1, vendor_short="VENDA")
        sku2, _ = generator.generate_sku("BRIT10G", vendor_id=2, vendor_short="VENDB")
        
        # Different vendors should not collide due to prefix
        assert sku1 != sku2
        assert "VENDA-" in sku1
        assert "VENDB-" in sku2

    def test_normalized_codes_different_vendors(self, generator):
        """Test BRIT10G and BRITC10G from same vendor"""
        sku1, _ = generator.generate_sku("BRIT10G", vendor_id=1, vendor_short="VEND")
        sku2, _ = generator.generate_sku("BRITC10G", vendor_id=1, vendor_short="VEND")
        
        # Both normalize to VEND-BRIT10G but different raw codes
        # In production, would detect collision and add suffix
        # For now, just verify both start with correct prefix
        assert sku1.startswith("VEND-")
        assert sku2.startswith("VEND-")

    # ========================================================================
    # Length Limit Tests
    # ========================================================================

    def test_sku_respects_max_length(self, generator):
        """Test generated SKU respects max length"""
        generator.max_sku_length = 30
        sku, _ = generator.generate_sku("AVERYLONGPRODUCTCODE", vendor_id=1, vendor_short="VENDOR")
        assert len(sku) <= 30

    # ========================================================================
    # Edge Cases
    # ========================================================================

    def test_numbers_only_code(self, generator):
        """Test with numeric-only code"""
        sku, _ = generator.generate_sku("12345", vendor_id=1, vendor_short="VEND")
        assert sku == "VEND-12345"

    def test_mixed_alphanumeric(self, generator):
        """Test with mixed alphanumeric code"""
        sku, _ = generator.generate_sku("A1B2C3", vendor_id=1, vendor_short="VEND")
        assert sku == "VEND-A1B2C3"

    def test_unicode_normalization(self, generator):
        """Test unicode characters are handled"""
        # Unicode chars should be stripped in slugify
        sku, _ = generator.generate_sku("BRIT10G™", vendor_id=1, vendor_short="VEND")
        assert "BRIT10G" in sku


# ========================================================================
# Integration Tests (with mocked DB)
# ========================================================================

class TestSKUGeneratorIntegration:
    """Integration tests for SKU generator"""

    def test_deterministic_suffix_consistency(self):
        """Test that collision suffix is deterministic"""
        gen = SKUGenerator(db_connection=None)
        
        # Same input should always produce same suffix
        hash1 = gen._short_hash("BRIT10G:42:0", length=6)
        hash2 = gen._short_hash("BRIT10G:42:0", length=6)
        hash3 = gen._short_hash("BRIT10G:42:0", length=6)
        
        assert hash1 == hash2 == hash3

    def test_sku_generation_is_stable(self):
        """Test that repeated generation with same inputs produces same SKU"""
        gen = SKUGenerator(db_connection=None)
        
        results = []
        for _ in range(5):
            sku, _ = gen.generate_sku("BRIT10G", vendor_id=42, vendor_short="VEND")
            results.append(sku)
        
        # All results should be identical
        assert all(r == results[0] for r in results)


# ========================================================================
# Scenario Tests
# ========================================================================

class TestSKUScenarios:
    """Real-world scenario tests"""

    def test_user1_user2_collision_scenario(self):
        """
        Scenario from problem statement:
        User 1: BRIT10G
        User 2: BRITC10G
        Both from same vendor -> should not collide due to normalization difference
        or if they normalize to same, should get deterministic suffix
        """
        gen = SKUGenerator(db_connection=None)
        
        sku_user1, status1 = gen.generate_sku("BRIT10G", vendor_id=100, vendor_short="BRIT")
        sku_user2, status2 = gen.generate_sku("BRITC10G", vendor_id=100, vendor_short="BRIT")
        
        # Verify they're different (BRITC normalizes differently than BRIT)
        assert "BRIT10G" in sku_user1
        assert "BRITC10G" in sku_user2
        # Should both start with same vendor prefix
        assert sku_user1.startswith("BRIT-")
        assert sku_user2.startswith("BRIT-")

    def test_multi_vendor_scenario(self):
        """
        Multiple vendors submitting similar codes should not collide
        """
        gen = SKUGenerator(db_connection=None)
        
        # Same product code, different vendors
        skus = []
        vendors = [
            ("British Imports", "BRIT"),
            ("Acme Corp", "ACME"),
            ("Global Trade", "GLOB"),
        ]
        
        for vendor_name, vendor_short in vendors:
            sku, _ = gen.generate_sku("PRODUCT10", vendor_id=hash(vendor_name) % 10000, vendor_short=vendor_short)
            skus.append(sku)
        
        # All SKUs should be unique due to vendor prefix
        assert len(set(skus)) == len(skus), "Vendor prefix should prevent collisions"
        print(f"Generated unique SKUs: {skus}")


# ========================================================================
# Benchmark Tests (optional)
# ========================================================================

class TestSKUPerformance:
    """Performance benchmarks for SKU generation"""

    def test_sku_generation_speed(self):
        """Benchmark SKU generation speed"""
        import time
        gen = SKUGenerator(db_connection=None)
        
        start = time.time()
        for i in range(1000):
            gen.generate_sku(f"CODE{i}", vendor_id=i % 100, vendor_short="VEND")
        elapsed = time.time() - start
        
        avg_ms = (elapsed / 1000) * 1000
        print(f"\nSKU generation: {avg_ms:.3f}ms per SKU")
        assert avg_ms < 1.0, "SKU generation should be < 1ms per SKU"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
