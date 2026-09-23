import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import CitizenReport, Product
from backend.app.schemas.schemas import ReportCreate, ReportResponse
from backend.app.services.clustering import ClusteringEngine

router = APIRouter(prefix="/reports", tags=["Citizen Reports"])

@router.post("", response_model=ReportResponse)
def submit_report(payload: ReportCreate, db: Session = Depends(get_db)):
    # 1. Product lookup or creation
    db_product = None
    if payload.gtin or payload.product_name:
        db_product = db.query(Product).filter(
            (Product.gtin == payload.gtin) if payload.gtin else (Product.product_name == payload.product_name)
        ).first()
        if not db_product:
            db_product = Product(
                gtin=payload.gtin,
                product_name=payload.product_name or "Reported Commodity"
            )
            db.add(db_product)
            db.commit()
            db.refresh(db_product)

    # 2. Hash reporter ID for privacy & rate limiting
    reporter_hash = hashlib.sha256("anonymous_citizen_session".encode()).hexdigest()

    # 3. Save report (validate scan_id existence to prevent FK constraint failure)
    valid_scan_id = None
    if payload.scan_id:
        from backend.app.models.models import Scan
        if db.query(Scan).filter(Scan.id == payload.scan_id).first():
            valid_scan_id = payload.scan_id

    report = CitizenReport(
        product_id=db_product.id if db_product else None,
        scan_id=valid_scan_id,
        reporter_hash=reporter_hash,
        issue_category=payload.issue_category,
        description=payload.description,
        location_city=payload.location_city or "Delhi",
        status="UNVERIFIED"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # 4. Trigger issue clustering update if product identified
    if db_product or valid_scan_id:
        clustering = ClusteringEngine(db)
        clustering.update_cluster_from_report(scan_id=valid_scan_id, product_id=db_product.id if db_product else None)

    return ReportResponse(
        report_id=report.id,
        status="UNVERIFIED",
        message="Your report is a signal for officer review. It is not a confirmed legal violation."
    )

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    reports = db.query(CitizenReport).all()
    return [
        {
            "report_id": r.id,
            "product_id": r.product_id,
            "issue_category": r.issue_category,
            "description": r.description,
            "location_city": r.location_city,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        }
        for r in reports
    ]
