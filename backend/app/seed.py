import datetime
from sqlalchemy.orm import Session
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.models import (
    User, Product, Scan, OCRResult, ExtractedField, RuleResult,
    CitizenReport, ProductCluster, OfficerReview, DecisionTrace
)

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Create Demo Users
        officer = db.query(User).filter(User.email == "officer@legalmetrology.gov.in").first()
        if not officer:
            officer = User(
                email="officer@legalmetrology.gov.in",
                hashed_password="scrypt:32768:8:1$hashed_password",
                full_name="Inspector R. K. Sharma",
                role="OFFICER",
                badge_number="LM-OFFICER-1082"
            )
            db.add(officer)

        citizen = db.query(User).filter(User.email == "citizen@example.com").first()
        if not citizen:
            citizen = User(
                email="citizen@example.com",
                hashed_password="scrypt:32768:8:1$hashed_password",
                full_name="Ananya Verma",
                role="CITIZEN"
            )
            db.add(citizen)

        db.commit()

        # 2. Demo Product 1: Clean Compliant Scan
        p1 = db.query(Product).filter(Product.gtin == "8901234567890").first()
        if not p1:
            p1 = Product(
                gtin="8901234567890",
                brand_name="PureHarvest",
                product_name="Organic Whole Wheat Atta 5kg",
                manufacturer="PureHarvest Agro Foods Pvt Ltd",
                category="food"
            )
            db.add(p1)
            db.commit()
            db.refresh(p1)

            scan1 = Scan(
                product_id=p1.id,
                image_hash="clean_atta_hash_1001",
                image_path="uploads/demo_clean_atta.png",
                quality_status="ACCEPTABLE",
                blur_score=142.5,
                brightness_score=0.55,
                glare_ratio=0.02,
                status="PASS_SCREENING",
                public_label="No issue detected in the checks performed",
                screening_confidence=0.94,
                rule_version="2026.1"
            )
            db.add(scan1)
            db.commit()

            # Extracted Fields for Clean Scan
            fields1 = [
                ExtractedField(scan_id=scan1.id, field_name="mrp", raw_value="MRP Rs. 260.00", normalized_value="₹ 260.00", confidence=0.96, extraction_method="REGEX_PATTERN"),
                ExtractedField(scan_id=scan1.id, field_name="net_quantity", raw_value="Net Qty: 5.0 kg", normalized_value="5 kg", confidence=0.95, extraction_method="REGEX_PATTERN"),
                ExtractedField(scan_id=scan1.id, field_name="manufacture_date", raw_value="MFD: 01/2026", normalized_value="01/2026", confidence=0.92, extraction_method="KEYWORD_ANCHOR"),
                ExtractedField(scan_id=scan1.id, field_name="manufacturer_or_packer", raw_value="PureHarvest Agro Foods", normalized_value="PureHarvest Agro Foods", confidence=0.90, extraction_method="KEYWORD_ANCHOR"),
                ExtractedField(scan_id=scan1.id, field_name="address", raw_value="Plot 12, Industrial Area, Noida UP", normalized_value="Plot 12, Industrial Area, Noida UP", confidence=0.88, extraction_method="KEYWORD_ANCHOR"),
                ExtractedField(scan_id=scan1.id, field_name="consumer_care", raw_value="Consumer Care: 1800-11-2233", normalized_value="1800-11-2233", confidence=0.94, extraction_method="KEYWORD_ANCHOR")
            ]
            for f in fields1:
                db.add(f)

            rules1 = [
                RuleResult(scan_id=scan1.id, rule_id="LM001", rule_name="MRP Declaration Screening", status="PASS", confidence=0.96, reason="MRP declaration detected and formatted correctly."),
                RuleResult(scan_id=scan1.id, rule_id="LM002", rule_name="Net Quantity Screening", status="PASS", confidence=0.95, reason="Net quantity statement declared in metric units."),
                RuleResult(scan_id=scan1.id, rule_id="LM003", rule_name="Date of Manufacture Screening", status="PASS", confidence=0.92, reason="Month/Year of manufacture clearly visible.")
            ]
            for r in rules1:
                db.add(r)
            db.commit()

        # 3. Demo Product 2: Missing MRP Declaration
        p2 = db.query(Product).filter(Product.gtin == "8909876543210").first()
        if not p2:
            p2 = Product(
                gtin="8909876543210",
                brand_name="ChocoDelight",
                product_name="Premium Dark Chocolate Bar 100g",
                manufacturer="ChocoDelight Confectionery",
                category="food"
            )
            db.add(p2)
            db.commit()
            db.refresh(p2)

            scan2 = Scan(
                product_id=p2.id,
                image_hash="missing_mrp_choco_hash_2002",
                image_path="uploads/demo_missing_mrp.png",
                quality_status="ACCEPTABLE",
                blur_score=118.0,
                brightness_score=0.48,
                glare_ratio=0.04,
                status="POTENTIAL_NON_COMPLIANCE",
                public_label="Potential non-compliance detected",
                screening_confidence=0.88,
                rule_version="2026.1"
            )
            db.add(scan2)
            db.commit()

            fields2 = [
                ExtractedField(scan_id=scan2.id, field_name="net_quantity", raw_value="Net Wt: 100g", normalized_value="100 g", confidence=0.94, extraction_method="REGEX_PATTERN"),
                ExtractedField(scan_id=scan2.id, field_name="manufacture_date", raw_value="MFD: 02/2026", normalized_value="02/2026", confidence=0.91, extraction_method="KEYWORD_ANCHOR")
            ]
            for f in fields2:
                db.add(f)

            rules2 = [
                RuleResult(scan_id=scan2.id, rule_id="LM001", rule_name="MRP Declaration Screening", status="POTENTIAL_NON_COMPLIANCE", confidence=0.88, reason="Required statutory declaration 'mrp' missing from visible label panel."),
                RuleResult(scan_id=scan2.id, rule_id="LM002", rule_name="Net Quantity Screening", status="PASS", confidence=0.94, reason="Net quantity statement visible.")
            ]
            for r in rules2:
                db.add(r)

            # Citizen Report for Missing MRP
            rep = CitizenReport(
                product_id=p2.id,
                scan_id=scan2.id,
                reporter_hash="hash_citizen_report_01",
                issue_category="Missing Information",
                description="MRP sticker removed from back panel",
                location_city="Mumbai",
                status="UNVERIFIED"
            )
            db.add(rep)

            # Product Cluster for Missing MRP
            cluster2 = ProductCluster(
                product_id=p2.id,
                issue_type="Missing Information",
                report_count=3,
                ai_flag_count=2,
                priority_score=0.78,
                status="UNVERIFIED"
            )
            db.add(cluster2)
            db.commit()

        # 4. Demo Product 3: Blurry Retake Required Scan
        p3 = db.query(Product).filter(Product.gtin == "8905555444333").first()
        if not p3:
            p3 = Product(
                gtin="8905555444333",
                brand_name="DailyFresh",
                product_name="Skimmed Milk Powder 200g",
                manufacturer="DailyFresh Dairy Products",
                category="food"
            )
            db.add(p3)
            db.commit()
            db.refresh(p3)

            scan3 = Scan(
                product_id=p3.id,
                image_hash="blurry_milk_hash_3003",
                image_path="uploads/demo_blurry_milk.png",
                quality_status="RETAKE_REQUIRED",
                blur_score=22.4,
                brightness_score=0.20,
                glare_ratio=0.28,
                status="NEEDS_REVIEW",
                public_label="More evidence or human review required",
                screening_confidence=0.50,
                rule_version="2026.1"
            )
            db.add(scan3)
            db.commit()

        db.commit()

        # 4. Demo Product 4: Identity Mismatch
        p4 = db.query(Product).filter(Product.gtin == "8902222333444").first()
        if not p4:
            p4 = Product(
                gtin="8902222333444",
                brand_name="ChocoBrand",
                product_name="Premium Choco-Chip Biscuits 250g",
                manufacturer="ABC Foods Pvt Ltd",
                category="food"
            )
            db.add(p4)
            db.commit()
            db.refresh(p4)

            scan4 = Scan(
                product_id=p4.id,
                image_hash="mismatch_choco_hash_4004",
                image_path="uploads/demo_mismatch.png",
                quality_status="ACCEPTABLE",
                blur_score=130.0,
                brightness_score=0.52,
                glare_ratio=0.03,
                status="NEEDS_REVIEW",
                public_label="More evidence or human review required",
                screening_confidence=0.60,
                rule_version="2026.1"
            )
            db.add(scan4)
            db.commit()

            fields4 = [
                ExtractedField(scan_id=scan4.id, field_name="product_name", raw_value="Premium Choco-Chip Biscuits", normalized_value="Premium Choco-Chip Biscuits", confidence=0.90, extraction_method="HEURISTIC_PRODUCT_NAME"),
                ExtractedField(scan_id=scan4.id, field_name="net_quantity", raw_value="Net Quantity: 250 g", normalized_value="250.0 g", confidence=0.93, extraction_method="KEYWORD_ANCHOR"),
                ExtractedField(scan_id=scan4.id, field_name="mrp", raw_value="MRP: Rs. 150.00", normalized_value="Rs. 150.00", confidence=0.95, extraction_method="REGEX_PATTERN"),
                ExtractedField(scan_id=scan4.id, field_name="manufacture_date", raw_value="Mfg. Date: 09/2026", normalized_value="09/2026", confidence=0.91, extraction_method="KEYWORD_ANCHOR"),
                ExtractedField(scan_id=scan4.id, field_name="manufacturer_or_packer", raw_value="Manufactured & Packed by: ABC Foods Pvt Ltd.", normalized_value="ABC Foods Pvt Ltd.", confidence=0.88, extraction_method="KEYWORD_ANCHOR"),
                ExtractedField(scan_id=scan4.id, field_name="consumer_care", raw_value="Consumer Care: 1800-123-4567", normalized_value="1800-123-4567", confidence=0.89, extraction_method="KEYWORD_ANCHOR"),
            ]
            for f in fields4:
                db.add(f)
            db.commit()

        # 5. Demo Product 5: Citizen Cluster (Multiple signals, high priority)
        p5 = db.query(Product).filter(Product.gtin == "8907777888999").first()
        if not p5:
            p5 = Product(
                gtin="8907777888999",
                brand_name="FastBites",
                product_name="Instant Noodles Masala 75g",
                manufacturer="FastBites Foods India Ltd",
                category="food"
            )
            db.add(p5)
            db.commit()
            db.refresh(p5)

            # High-priority cluster driven by citizen signals
            cluster5 = ProductCluster(
                product_id=p5.id,
                issue_type="Suspicious MRP",
                report_count=8,
                ai_flag_count=3,
                priority_score=0.87,
                status="UNVERIFIED"
            )
            db.add(cluster5)
            db.commit()

            # Add multiple citizen reports
            cities = ["Delhi", "Mumbai", "Pune", "Bengaluru", "Chennai", "Hyderabad", "Kolkata", "Jaipur"]
            descs = [
                "MRP label printed over original price sticker",
                "Two different MRP prices printed on same pack",
                "MRP higher than printed on earlier batch",
                "Retailer selling above printed MRP",
                "MRP sticker applied on top of another",
                "Pack says Rs. 20 but retailer charged Rs. 25",
                "MRP partially scratched off",
                "Different MRP on front vs back of package"
            ]
            import datetime as dt
            for i in range(8):
                rep5 = CitizenReport(
                    product_id=p5.id,
                    reporter_hash=f"hash_citizen_noodles_{i+1:02d}",
                    issue_category="Suspicious MRP",
                    description=descs[i],
                    location_city=cities[i],
                    status="UNVERIFIED",
                    created_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=i)
                )
                db.add(rep5)

            db.commit()

        db.commit()
        print("Database successfully seeded with SIH demo data (6 cases).")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
