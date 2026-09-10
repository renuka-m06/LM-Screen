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

    def update_cluster_for_product(self, product_id: str, issue_type: str, is_ai_flag: bool = False):
        cluster = self.db.query(ProductCluster).filter(
            ProductCluster.product_id == product_id,
            ProductCluster.issue_type == issue_type
        ).first()

        if not cluster:
            cluster = ProductCluster(
                product_id=product_id,
                issue_type=issue_type,
                report_count=0 if is_ai_flag else 1,
                ai_flag_count=1 if is_ai_flag else 0,
                priority_score=0.5
            )
            self.db.add(cluster)
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
