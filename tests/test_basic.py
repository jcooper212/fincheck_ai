# ABOUTME: Basic functionality tests for FinCheck AI components
# ABOUTME: Verifies database, parser, categorizer, and grift detector work correctly

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database
from src.categorizer import Categorizer, Analytics
from src.grift_detector import GriftDetector


def test_database():
    """Test database creation and basic operations"""
    print("Testing database...")

    db = Database(Path("data/test_fincheck.db"))

    # Add test statement
    statement_id = db.add_statement(
        bank_name="Test Bank",
        statement_date="2025-01",
        pdf_path="test.pdf",
        account_last4="1234"
    )

    assert statement_id > 0, "Failed to create statement"

    # Add test transactions
    txn_id = db.add_transaction(
        statement_id=statement_id,
        date="2025-01-15",
        merchant="Netflix",
        amount=15.99,
        category="Entertainment"
    )

    assert txn_id > 0, "Failed to create transaction"

    # Query transactions
    transactions = db.get_transactions()
    assert len(transactions) > 0, "Failed to query transactions"

    print("✓ Database tests passed")


def test_categorizer():
    """Test transaction categorization"""
    print("Testing categorizer...")

    categorizer = Categorizer()

    # Test various categories
    tests = [
        ("Netflix", "Entertainment"),
        ("Whole Foods", "Food & Dining"),
        ("Uber", "Transportation"),
        ("Planet Fitness", "Subscriptions & Memberships"),
    ]

    for merchant, expected_category in tests:
        category = categorizer.categorize_transaction(merchant)
        assert category == expected_category, f"Failed to categorize {merchant}: got {category}, expected {expected_category}"

    print("✓ Categorizer tests passed")


def test_grift_detector():
    """Test grift detection"""
    print("Testing grift detector...")

    # Create test database
    db = Database(Path("data/test_fincheck.db"))

    grift_detector = GriftDetector(db)

    # This will run on test data
    flags = grift_detector.detect_all()

    # Just verify it runs without error
    print(f"✓ Grift detector tests passed (found {len(flags)} flags)")


def test_analytics():
    """Test analytics"""
    print("Testing analytics...")

    db = Database(Path("data/test_fincheck.db"))
    analytics = Analytics(db)

    # Test stats
    stats = db.get_stats()
    assert 'transactions' in stats, "Stats missing transaction count"

    # Test category breakdown
    categories = analytics.get_category_breakdown()
    assert isinstance(categories, list), "Category breakdown should return list"

    print("✓ Analytics tests passed")


if __name__ == "__main__":
    print("\n🧪 Running FinCheck AI tests...\n")

    try:
        test_database()
        test_categorizer()
        test_grift_detector()
        test_analytics()

        print("\n✅ All tests passed!\n")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error running tests: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
