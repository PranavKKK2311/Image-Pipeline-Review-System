"""
SKU Generator: Solves Problem 1 - Unique, collision-resistant product codes

Key features:
- Deterministic canonicalization (slugify raw vendor code)
- Vendor namespace prefix (e.g., "VEND-BRIT10G")
- Collision detection and recovery using stable hash suffix
- Database-level uniqueness enforcement
"""

import hashlib
import re
import string
from typing import Tuple, Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SKUStatus(Enum):
    """Enum for SKU generation status"""
    INSERTED = "inserted"
    CONFLICT_RESOLVED = "conflict_resolved"
    CONFLICT_UNRESOLVED = "conflict_unresolved"
    ERROR = "error"


class SKUGenerator:
    """
    Generates unique, deterministic SKUs for products.
    
    Strategy:
    1. Normalize vendor code (uppercase, remove non-alphanumeric)
    2. Prefix with vendor short code
    3. On collision, append deterministic hash suffix
    4. Enforce uniqueness at database level
    
    Example:
        gen = SKUGenerator(db_connection)
        canonical_sku, status = gen.generate_sku(
            raw_code="BRIT10G",
            vendor_id=42,
            vendor_short="VEND"
        )
        # Returns: ("VEND-BRIT10G", SKUStatus.INSERTED)
        # Or:      ("VEND-BRIT10G-3F4E1A", SKUStatus.CONFLICT_RESOLVED)
    """

    def __init__(
        self,
        db_connection: Any,
        max_sku_length: int = 64,
        hash_suffix_length: int = 6,
    ):
        """
        Initialize SKU generator.
        
        Args:
            db_connection: Database connection pool or connection
            max_sku_length: Maximum length for canonical_sku column
            hash_suffix_length: Length of deterministic suffix (e.g., "3F4E1A")
        """
        self.db = db_connection
        self.max_sku_length = max_sku_length
        self.hash_suffix_length = hash_suffix_length

    @staticmethod
    def _slugify(code: str, max_len: int = 40) -> str:
        """
        Canonicalize vendor code: uppercase, remove non-alphanumeric.
        
        Args:
            code: Raw vendor code (e.g., "BRIT10G", "brit-10-g", "BRIT_10.G")
            max_len: Maximum length of slug
            
        Returns:
            Canonicalized slug (e.g., "BRIT10G")
        """
        if not code:
            return ""
        
        # Uppercase and remove non-alphanumeric
        code = code.upper()
        code = re.sub(r'[^A-Z0-9]+', '', code)
        return code[:max_len]

    @staticmethod
    def _short_hash(value: str, length: int = 6) -> str:
        """
        Generate deterministic short hash (base36) for suffix.
        
        Args:
            value: String to hash (e.g., raw_code + vendor_id)
            length: Length of output hash
            
        Returns:
            Uppercase hash string (e.g., "3F4E1A")
        """
        h = hashlib.sha1(value.encode('utf8')).hexdigest()
        val = int(h[:12], 16)
        alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        out = []
        while len(out) < length:
            out.append(alphabet[val % len(alphabet)])
            val //= len(alphabet)
        return ''.join(out)

    def generate_sku(
        self,
        raw_code: str,
        vendor_id: int,
        vendor_short: str,
        product_id: Optional[int] = None,
        max_retries: int = 5,
    ) -> Tuple[str, SKUStatus]:
        """
        Generate unique SKU from vendor code.
        
        Algorithm:
        1. Slugify raw_code
        2. Combine with vendor_short: "VENDSHORT-SLUG"
        3. Try insert; if unique constraint violation, append hash suffix
        4. Keep trying with longer suffix until success or max retries
        
        Args:
            raw_code: Vendor-supplied product code (e.g., "BRIT10G")
            vendor_id: Vendor ID from database
            vendor_short: Vendor short code (e.g., "VEND")
            product_id: If updating existing product, provide ID
            max_retries: Maximum collision resolution attempts
            
        Returns:
            Tuple of (canonical_sku, status)
            - canonical_sku: Final unique SKU (e.g., "VEND-BRIT10G" or "VEND-BRIT10G-3F4E1A")
            - status: SKUStatus enum (INSERTED, CONFLICT_RESOLVED, etc.)
        """
        if not raw_code or not vendor_short:
            return "", SKUStatus.ERROR

        # Step 1: Slugify
        slug = self._slugify(raw_code)
        if not slug:
            logger.error(f"Failed to slugify raw_code: {raw_code}")
            return "", SKUStatus.ERROR

        # Step 2: Build candidate SKU
        base_candidate = f"{vendor_short}-{slug}"
        
        # Ensure total length doesn't exceed max
        available_for_suffix = self.max_sku_length - len(base_candidate) - 1  # -1 for "-" separator
        if available_for_suffix < 0:
            # Base is too long, truncate slug
            max_slug_len = self.max_sku_length - len(vendor_short) - 2
            slug = slug[:max_slug_len]
            base_candidate = f"{vendor_short}-{slug}"

        # Step 3: Try to insert base candidate
        try:
            if product_id:
                result = self._update_product_sku(product_id, base_candidate)
            else:
                result = self._insert_product_sku(base_candidate, vendor_id, raw_code)
            
            if result:
                logger.info(f"SKU inserted successfully: {base_candidate}")
                return base_candidate, SKUStatus.INSERTED
        except Exception as e:
            logger.debug(f"Insert conflict for {base_candidate}: {e}")

        # Step 4: Collision detected; try with deterministic suffix
        for attempt in range(max_retries):
            # Compute deterministic suffix based on raw_code and vendor_id
            hash_input = f"{raw_code}:{vendor_id}:{attempt}"
            suffix = self._short_hash(hash_input, length=min(self.hash_suffix_length + attempt, 10))
            candidate_with_suffix = f"{base_candidate}-{suffix}"
            
            # Ensure length is within limit
            if len(candidate_with_suffix) > self.max_sku_length:
                logger.warning(f"SKU with suffix exceeds max length: {candidate_with_suffix}")
                continue

            try:
                if product_id:
                    result = self._update_product_sku(product_id, candidate_with_suffix)
                else:
                    result = self._insert_product_sku(candidate_with_suffix, vendor_id, raw_code)
                
                if result:
                    logger.info(f"SKU inserted with suffix after {attempt + 1} attempt(s): {candidate_with_suffix}")
                    return candidate_with_suffix, SKUStatus.CONFLICT_RESOLVED
            except Exception as e:
                logger.debug(f"Collision for {candidate_with_suffix}, attempt {attempt + 1}: {e}")
                continue

        logger.error(f"Failed to generate unique SKU after {max_retries} retries for {raw_code}")
        return "", SKUStatus.CONFLICT_UNRESOLVED

    def _insert_product_sku(self, canonical_sku: str, vendor_id: int, raw_code: str) -> bool:
        """
        Attempt to insert product with canonical_sku.
        Raises exception on unique constraint violation.
        
        Args:
            canonical_sku: The canonical SKU to insert
            vendor_id: Vendor ID
            raw_code: Original vendor code
            
        Returns:
            True if inserted successfully
            
        Raises:
            Exception: If unique constraint violated or DB error
        """
        # This is a placeholder; implement with your actual DB library
        # Example with psycopg2:
        # cursor = self.db.cursor()
        # cursor.execute(
        #     """
        #     INSERT INTO products (vendor_id, vendor_code, canonical_sku)
        #     VALUES (%s, %s, %s)
        #     """,
        #     (vendor_id, raw_code, canonical_sku)
        # )
        # self.db.commit()
        # return True
        
        logger.debug(f"[MOCK] Inserting SKU: {canonical_sku} for vendor_id={vendor_id}")
        return True

    def _update_product_sku(self, product_id: int, canonical_sku: str) -> bool:
        """
        Update existing product's canonical_sku.
        
        Args:
            product_id: Product ID to update
            canonical_sku: New canonical SKU
            
        Returns:
            True if updated successfully
            
        Raises:
            Exception: If unique constraint violated or DB error
        """
        logger.debug(f"[MOCK] Updating product {product_id} SKU to: {canonical_sku}")
        return True

    def validate_sku_uniqueness(self, canonical_sku: str, exclude_product_id: Optional[int] = None) -> bool:
        """
        Check if a SKU is unique in the database.
        
        Args:
            canonical_sku: SKU to check
            exclude_product_id: If provided, exclude this product from uniqueness check
            
        Returns:
            True if unique (can be used), False if already exists
        """
        # Placeholder for actual DB query
        logger.debug(f"[MOCK] Checking uniqueness of {canonical_sku}")
        return True

    def list_sku_collisions(self, vendor_id: Optional[int] = None) -> list:
        """
        Find all potential SKU collisions (canonical codes with same normalized value).
        Useful for audit and cleanup.
        
        Args:
            vendor_id: Optional filter by vendor
            
        Returns:
            List of collision groups
        """
        # Placeholder
        logger.debug(f"[MOCK] Listing SKU collisions for vendor_id={vendor_id}")
        return []

    def migrate_legacy_codes(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Migrate existing products without canonical_sku.
        Generates SKU for each product deterministically.
        Useful during rollout.
        
        Args:
            batch_size: Number of products to process in each batch
            
        Returns:
            Migration statistics (processed, errors, collisions)
        """
        logger.info(f"Starting migration of legacy product codes")
        stats = {
            "processed": 0,
            "migrated": 0,
            "errors": 0,
            "collisions_resolved": 0,
        }
        
        # Placeholder: fetch legacy products, generate SKUs, batch insert
        logger.info(f"Migration complete: {stats}")
        return stats


# ============================================================================
# Standalone usage examples
# ============================================================================

def example_deterministic_sku():
    """Example showing deterministic SKU generation."""
    print("=" * 60)
    print("SKU Generator Example")
    print("=" * 60)
    
    # Mock generator (no DB connection needed for demo)
    gen = SKUGenerator(db_connection=None)
    
    # Test cases
    test_cases = [
        ("BRIT10G", 1, "BRIT"),
        ("britc10g", 1, "BRIT"),  # Different case, same vendor -> collision
        ("BRIT-10-G", 1, "BRIT"),  # Different format, normalizes to same
        ("BRIT10G", 2, "BRIT"),    # Same code, different vendor -> no collision
        ("TEST_CODE.123", 3, "TEST"),
    ]
    
    skus_generated = {}
    
    for raw_code, vendor_id, vendor_short in test_cases:
        candidate, status = gen.generate_sku(
            raw_code=raw_code,
            vendor_id=vendor_id,
            vendor_short=vendor_short,
            max_retries=3,
        )
        
        # Simulate collision detection
        if candidate in skus_generated:
            print(f"  ⚠️  COLLISION: {candidate} (already used)")
            # In real scenario, generator would compute suffix
            candidate, status = gen.generate_sku(raw_code, vendor_id, vendor_short)
        else:
            skus_generated[candidate] = (raw_code, vendor_id, vendor_short)
        
        print(f"  {raw_code:20} (vendor_id={vendor_id}, {vendor_short:5}) -> {candidate:30} [{status.value}]")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total SKUs generated: {len(skus_generated)}")
    print(f"  All unique: {len(skus_generated) == len(test_cases)}")
    print("=" * 60)


if __name__ == "__main__":
    example_deterministic_sku()
