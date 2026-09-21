"""
scripts/reset_demo_data.py
─────────────────────────────────────────────────────────────────────────────
LM-Screen SIH Demo Data Reset Script

PURPOSE: Safely removes ONLY records created by seed_demo_data.py.
All demo records are identified by image_hash or fields starting with
the DEMO_TAG prefix "SIH_DEMO_SYNTHETIC".

[!]  SAFETY GUARANTEE:
    - Only deletes records explicitly tagged as DEMO data
    - Never touches scans whose image_hash does not start with "SIH_DEMO_SYNTHETIC"
    - Never deletes users created outside of seeding (officer@legalmetrology.gov.in
      is shared, so it is NOT deleted to preserve audit trail links)
    - Prints a preview of what will be deleted before acting
    - Requires confirmation (--confirm flag) to actually delete

Usage:
    python scripts/reset_demo_data.py              # Preview only (dry run)
    python scripts/reset_demo_data.py --confirm    # Actually delete demo data
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import SessionLocal
from backend.app.models.models import (
    Scan, ExtractedField, RuleResult, CitizenReport,
    ProductCluster, OfficerReview, DecisionTrace, Product, User
)

DEMO_TAG = "SIH_DEMO_SYNTHETIC"
DEMO_GTIN_PREFIX = "DEMO-"


def preview_demo_records(db):
    demo_scans = db.query(Scan).filter(Scan.image_hash.like(f"{DEMO_TAG}%")).all()
    demo_products = db.query(Product).filter(Product.gtin.like(f"{DEMO_GTIN_PREFIX}%")).all()
    demo_citizen_users = db.query(User).filter(User.email == "citizen.demo@example.com").all()

    print(f"\n{'='*60}")
    print(f"DEMO DATA RESET — DRY RUN PREVIEW")
    print(f"{'='*60}")
    print(f"\nScans tagged {DEMO_TAG}: {len(demo_scans)}")
    for s in demo_scans:
        print(f"  - Scan ID: {s.id[:16]}... | Status: {s.status} | Hash: {s.image_hash}")

    print(f"\nProducts with GTIN prefix '{DEMO_GTIN_PREFIX}': {len(demo_products)}")
    for p in demo_products:
        print(f"  - Product: {p.product_name} | GTIN: {p.gtin}")

    print(f"\nDemo citizen users: {len(demo_citizen_users)}")
    print(f"\n[!]  Officer user (officer@legalmetrology.gov.in) will NOT be deleted")
    print(f"    (preserves audit trail integrity)")
    print(f"\n{'='*60}")

    return demo_scans, demo_products, demo_citizen_users


def reset_demo_data(confirm: bool = False):
    db = SessionLocal()
    try:
        demo_scans, demo_products, demo_citizen_users = preview_demo_records(db)

        if not confirm:
            print("\n[SRCH] DRY RUN — No data was deleted.")
            print("   To actually delete, run: python scripts/reset_demo_data.py --confirm")
            return

        # Collect scan IDs for cascade
        scan_ids = [s.id for s in demo_scans]
        product_ids = [p.id for p in demo_products]

        print(f"\n[DEL]  Deleting demo data...")

        # Delete in FK order (children before parents)
        if scan_ids:
            db.query(DecisionTrace).filter(DecisionTrace.scan_id.in_(scan_ids)).delete(synchronize_session=False)
            db.query(RuleResult).filter(RuleResult.scan_id.in_(scan_ids)).delete(synchronize_session=False)
            db.query(ExtractedField).filter(ExtractedField.scan_id.in_(scan_ids)).delete(synchronize_session=False)
            db.query(OfficerReview).filter(OfficerReview.scan_id.in_(scan_ids)).delete(synchronize_session=False)
            db.query(CitizenReport).filter(CitizenReport.scan_id.in_(scan_ids)).delete(synchronize_session=False)

        if product_ids:
            db.query(CitizenReport).filter(CitizenReport.product_id.in_(product_ids)).delete(synchronize_session=False)
            db.query(ProductCluster).filter(ProductCluster.product_id.in_(product_ids)).delete(synchronize_session=False)

        if scan_ids:
            db.query(Scan).filter(Scan.id.in_(scan_ids)).delete(synchronize_session=False)

        if product_ids:
            db.query(Product).filter(Product.id.in_(product_ids)).delete(synchronize_session=False)

        # Remove demo citizen user (safe — they only exist in demo data)
        for u in demo_citizen_users:
            db.delete(u)

        db.commit()

        print(f"\n[OK] Reset complete.")
        print(f"   Deleted {len(scan_ids)} demo scans, {len(product_ids)} demo products.")
        print(f"   Production data was NOT affected.")
        print(f"\n   To recreate demo data: python scripts/seed_demo_data.py")

    finally:
        db.close()


if __name__ == "__main__":
    confirm = "--confirm" in sys.argv
    reset_demo_data(confirm=confirm)
