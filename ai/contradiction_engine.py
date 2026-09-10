import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ContradictionSource(BaseModel):
    source_type: str  # USER_INPUT, IMAGE_EVIDENCE, HISTORICAL_SCAN, DATABASE, BARCODE
    value: str
    details: Dict[str, Any] = Field(default_factory=dict)

class ContradictionObject(BaseModel):
    id: str = Field(default_factory=lambda: f"contra_{uuid.uuid4().hex[:8]}")
    type: str  # PRODUCT_IDENTITY_CONFLICT, PACKAGING_QUANTITY_CHANGE_SIGNAL, DATA_CONSISTENCY_CONFLICT
    severity: str  # HIGH, MEDIUM, LOW
    sources: List[ContradictionSource]
    confidence: float = 0.90
    explanation: str
    recommended_action: str  # REQUEST_MORE_EVIDENCE, MARK_UNDER_INVESTIGATION, REJECT
    status: str = "OPEN"

class ContradictionReport(BaseModel):
    has_contradictions: bool
    scan_id: Optional[str] = None
    contradictions: List[ContradictionObject] = Field(default_factory=list)
    suggested_verdict_override: Optional[str] = None  # NEEDS_REVIEW

class ContradictionEngine:
    """
    Generalized contradiction detection system comparing multi-source evidence:
    User input vs OCR evidence vs Barcode vs Database vs Historical Scans.
    """

    def analyze_contradictions(
        self,
        scan_id: str,
        user_product_name: Optional[str],
        ocr_product_name: Optional[str],
        user_gtin: Optional[str],
        ocr_gtin: Optional[str],
        barcode_gtin: Optional[str],
        current_net_qty: Optional[str] = None,
        historical_net_qty: Optional[str] = None
    ) -> ContradictionReport:
        contradictions: List[ContradictionObject] = []

        # 1. Product Identity Mismatch Check (User Input vs Image Evidence)
        if user_product_name and ocr_product_name:
            u_clean = user_product_name.lower().strip()
            o_clean = ocr_product_name.lower().strip()

            # Token overlap check
            u_words = set(w for w in re_split(u_clean) if len(w) > 2)
            o_words = set(w for w in re_split(o_clean) if len(w) > 2)

            common_words = u_words & o_words
            # If user claimed a product name but label image contains completely different words
            if u_clean not in o_clean and o_clean not in u_clean and not common_words:
                contradictions.append(ContradictionObject(
                    type="PRODUCT_IDENTITY_CONFLICT",
                    severity="HIGH",
                    sources=[
                        ContradictionSource(source_type="USER_INPUT", value=user_product_name),
                        ContradictionSource(source_type="IMAGE_EVIDENCE", value=ocr_product_name)
                    ],
                    confidence=0.94,
                    explanation=(
                        f"User-declared product identity ('{user_product_name}') contradicts the product identity "
                        f"extracted from image evidence ('{ocr_product_name}'). Human review required."
                    ),
                    recommended_action="REQUEST_MORE_EVIDENCE"
                ))

        # 2. GTIN / Barcode Identifier Conflict Check
        gtins = {
            "USER_INPUT": user_gtin,
            "OCR_EVIDENCE": ocr_gtin,
            "BARCODE_DECODER": barcode_gtin
        }
        active_gtins = {k: v for k, v in gtins.items() if v and v.strip()}
        unique_values = set(active_gtins.values())

        if len(unique_values) > 1:
            sources = [ContradictionSource(source_type=k, value=v) for k, v in active_gtins.items()]
            contradictions.append(ContradictionObject(
                type="DATA_CONSISTENCY_CONFLICT",
                severity="MEDIUM",
                sources=sources,
                confidence=0.88,
                explanation="Multiple conflicting GTIN/barcode values were detected across user input, OCR, and barcode decoder.",
                recommended_action="MARK_UNDER_INVESTIGATION"
            ))

        # 3. Packaging Quantity Change Signal Check (Current vs Historical)
        if current_net_qty and historical_net_qty and current_net_qty.strip() != historical_net_qty.strip():
            contradictions.append(ContradictionObject(
                type="PACKAGING_QUANTITY_CHANGE_SIGNAL",
                severity="LOW",
                sources=[
                    ContradictionSource(source_type="IMAGE_EVIDENCE", value=f"Current: {current_net_qty}"),
                    ContradictionSource(source_type="HISTORICAL_SCAN", value=f"Previous: {historical_net_qty}")
                ],
                confidence=0.85,
                explanation=f"Net quantity statement changed from historical pack size '{historical_net_qty}' to current '{current_net_qty}'.",
                recommended_action="MARK_UNDER_INVESTIGATION"
            ))

        has_c = len(contradictions) > 0
        override = "NEEDS_REVIEW" if has_c else None

        return ContradictionReport(
            has_contradictions=has_c,
            scan_id=scan_id,
            contradictions=contradictions,
            suggested_verdict_override=override
        )

def re_split(text: str) -> List[str]:
    import re
    return re.findall(r"\w+", text)
