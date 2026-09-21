from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models.models import Scan, CitizenReport, ProductCluster, OfficerReview, Product
import datetime

router = APIRouter(prefix="/dashboard", tags=["Dashboard Statistics"])

@router.get("/statistics")
def get_dashboard_statistics(db: Session = Depends(get_db)):
    total_scans = db.query(Scan).count()
    pass_scans = db.query(Scan).filter(Scan.status == "PASS_SCREENING").count()
    potential_scans = db.query(Scan).filter(Scan.status == "POTENTIAL_NON_COMPLIANCE").count()
    review_scans = db.query(Scan).filter(Scan.status == "NEEDS_REVIEW").count()

    total_reports = db.query(CitizenReport).count()
    total_clusters = db.query(ProductCluster).count()
    total_reviews = db.query(OfficerReview).count()

    # Top priority products (PRIORITY_REVIEW clusters)
    top_clusters = db.query(ProductCluster).filter(
        ProductCluster.priority_class == "PRIORITY_REVIEW"
    ).order_by(ProductCluster.updated_at.desc()).limit(5).all()
    
    # If not enough, fetch STANDARD_REVIEW
    if len(top_clusters) < 5:
        more = db.query(ProductCluster).filter(
            ProductCluster.priority_class == "STANDARD_REVIEW"
        ).order_by(ProductCluster.updated_at.desc()).limit(5 - len(top_clusters)).all()
        top_clusters.extend(more)
    priority_products = []
    for c in top_clusters:
        prod = db.query(Product).filter(Product.id == c.product_id).first()
        priority_products.append({
            "cluster_id": c.id,
            "product_name": c.product_name or (prod.product_name if prod else "Unknown"),
            "gtin": c.gtin or (prod.gtin if prod else None),
            "match_strength": c.match_strength,
            "priority_score": round(c.priority_score, 2), # Legacy
            "priority_class": c.priority_class,
            "priority_label": c.priority_class.replace("_", " "),
            "evidence_strength": c.evidence_strength,
            "actionability_state": c.actionability_state,
            "citizen_reports": c.report_count,
            "ai_flags": c.ai_flag_count,
            "status": c.status
        })

    # Issue category distribution from citizen reports
    all_reports = db.query(CitizenReport).all()
    issue_freq: dict = {}
    for r in all_reports:
        cat = r.issue_category
        issue_freq[cat] = issue_freq.get(cat, 0) + 1
    issue_distribution = [{"issue": k, "count": v} for k, v in sorted(issue_freq.items(), key=lambda x: -x[1])]

    # Recent scan trend (last 7 days)
    scan_trend = []
    today = datetime.datetime.now(datetime.timezone.utc).date()
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day, datetime.time.min)
        day_end = datetime.datetime.combine(day, datetime.time.max)
        count = db.query(Scan).filter(Scan.timestamp >= day_start, Scan.timestamp <= day_end).count()
        scan_trend.append({"date": day.strftime("%d %b"), "scans": count})

    return {
        "scans": {
            "total": total_scans,
            "pass_screening": pass_scans,
            "potential_non_compliance": potential_scans,
            "needs_review": review_scans
        },
        "citizen_intelligence": {
            "total_signals": total_reports,
            "unverified_signals": db.query(CitizenReport).filter(CitizenReport.status == "UNVERIFIED").count(),
            "issue_distribution": issue_distribution
        },
        "enforcement_prioritization": {
            "active_clusters": total_clusters,
            "completed_officer_reviews": total_reviews,
            "priority_products": priority_products
        },
        "scan_trend": scan_trend
    }
