from sqlalchemy.orm import Session
from backend.app.models.models import ProductCluster, Product, CitizenReport, Scan
from backend.app.services.prioritization import PrioritizationEngine

class ClusteringEngine:
    """
    Issue Clustering Engine.
    Clusters signals and scans by canonical product ID + issue_type.
    Recalculates Operational Prioritization Scores on updates.
    """
    def __init__(self, db: Session):
        self.db = db
        self.prioritizer = PrioritizationEngine()

    def update_cluster_from_report(self, scan_id: str = None, product_id: str = None, is_ai_flag: bool = False):
        cluster = None
        if scan_id:
            scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
            if scan and scan.cluster_id:
                cluster = self.db.query(ProductCluster).filter(ProductCluster.id == scan.cluster_id).first()
                
        if not cluster and product_id:
            # Fallback to finding a cluster with this product_id
            cluster = self.db.query(ProductCluster).filter(ProductCluster.product_id == product_id).first()

        if not cluster:
            # If still no cluster, we create an ad-hoc one for the report/product
            cluster = ProductCluster(
                product_id=product_id,
                match_method="INITIAL",
                match_strength="NO_MATCH",
                report_count=0 if is_ai_flag else 1,
                ai_flag_count=1 if is_ai_flag else 0,
                priority_score=0.5
            )
            self.db.add(cluster)
            self.db.flush()
            if scan_id:
                scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
                if scan:
                    scan.cluster_id = cluster.id
        else:
            if is_ai_flag:
                cluster.ai_flag_count += 1
            else:
                cluster.report_count += 1

        self.db.commit()
        self.db.refresh(cluster)

        # Recalculate priority score
        score_data = self.prioritizer.calculate_score(
            report_count=cluster.report_count,
            ai_flag_count=cluster.ai_flag_count
        )
        cluster.priority_score = score_data["operational_prioritization_score"]
        self.db.commit()
        return cluster
