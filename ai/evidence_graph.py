from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class GraphNode(BaseModel):
    id: str
    type: str  # OCR_TOKEN, FIELD, CONTEXT, RULE, VERDICT, OFFICER_DECISION
    label: str
    details: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str  # SUPPORTS, EVALUATED_BY, CONTRIBUTES_TO, OVERRIDDEN_BY
    details: Dict[str, Any] = Field(default_factory=dict)

class EvidenceGraphResponse(BaseModel):
    scan_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    summary: Dict[str, Any] = Field(default_factory=dict)

class EvidenceGraphBuilder:
    """
    Constructs a backward-traceable Evidence Graph linking:
    Image Region -> OCR Tokens -> Extracted Fields -> Product Context -> Rules -> Verdict -> Officer Decision.
    """
    def build_graph(self, scan_data: Dict[str, Any]) -> EvidenceGraphResponse:
        scan_id = scan_data.get("scan_id", "UNKNOWN")
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        # 1. Add Image Quality Node
        q_node_id = f"img_quality_{scan_id}"
        quality_info = scan_data.get("quality", {})
        nodes.append(GraphNode(
            id=q_node_id,
            type="IMAGE_QUALITY",
            label=f"Image Quality: {quality_info.get('status', 'UNKNOWN')}",
            details=quality_info
        ))

        # 2. Add OCR Token Nodes
        ocr_tokens = scan_data.get("ocr_tokens", [])
        for tok in ocr_tokens:
            tok_id = f"ocr_{tok.get('token_id', tok.get('id', ''))}"
            nodes.append(GraphNode(
                id=tok_id,
                type="OCR_TOKEN",
                label=f"OCR Token: '{tok.get('text', '')}'",
                details={
                    "confidence": tok.get("confidence", 0.0),
                    "polygon": tok.get("polygon", []),
                    "language": tok.get("language", "en"),
                    "model_version": tok.get("model_version", "2026.1")
                }
            ))
            # Edge: Image Quality -> OCR Token
            edges.append(GraphEdge(
                source=q_node_id,
                target=tok_id,
                relationship="PROCESSED_BY"
            ))

        # 3. Add Extracted Field Nodes and Link to Supporting OCR Tokens
        fields = scan_data.get("extracted_fields", {})
        if isinstance(fields, list):
            fields_dict = {f.get("field_name", f"f_{i}"): f for i, f in enumerate(fields)}
        else:
            fields_dict = fields

        for fname, fval in fields_dict.items():
            if not isinstance(fval, dict):
                continue
            field_node_id = f"field_{fname}"
            nodes.append(GraphNode(
                id=field_node_id,
                type="FIELD",
                label=f"Field: {fname} = {fval.get('normalized_value') or fval.get('raw_value', 'ABSENT')}",
                details={
                    "field_name": fname,
                    "raw_value": fval.get("raw_value", ""),
                    "normalized_value": fval.get("normalized_value", ""),
                    "confidence": fval.get("confidence", 0.0),
                    "extraction_method": fval.get("extraction_method", "UNKNOWN")
                }
            ))

            # Edge: OCR Tokens -> Field
            ocr_evidence_ids = fval.get("ocr_evidence_ids") or []
            for ev_id in ocr_evidence_ids:
                tok_id = f"ocr_{ev_id}"
                edges.append(GraphEdge(
                    source=tok_id,
                    target=field_node_id,
                    relationship="SUPPORTS",
                    details={"field": fname}
                ))

        # 4. Add Context Node
        context_node_id = f"context_{scan_id}"
        market_context = scan_data.get("market_context", "packaged_retail_product")
        nodes.append(GraphNode(
            id=context_node_id,
            type="CONTEXT",
            label=f"Context: {market_context}",
            details={"category": scan_data.get("category", "food"), "market_context": market_context}
        ))

        # 5. Add Rule Nodes and Link Fields -> Rules
        checks = scan_data.get("checks_performed", [])
        for chk in checks:
            rule_id = chk.get("rule_id", "LM_UNKNOWN")
            rule_node_id = f"rule_{rule_id}"

            # Only add rule node if not already added
            if not any(n.id == rule_node_id for n in nodes):
                nodes.append(GraphNode(
                    id=rule_node_id,
                    type="RULE",
                    label=f"Rule {rule_id}: {chk.get('rule_name', '')}",
                    details={
                        "status": chk.get("status", "NOT_CHECKED"),
                        "reason": chk.get("reason", ""),
                        "confidence": chk.get("confidence", 0.9),
                        "version": scan_data.get("rule_version", "2026.1")
                    }
                ))
                # Link Context -> Rule
                edges.append(GraphEdge(
                    source=context_node_id,
                    target=rule_node_id,
                    relationship="APPLIES_RULE"
                ))

            # Link Fields evaluated by this Rule
            reason_text = (chk.get("reason") or "").lower()
            for fname in fields_dict:
                if fname.lower() in reason_text or fname.replace("_", "") in reason_text:
                    edges.append(GraphEdge(
                        source=f"field_{fname}",
                        target=rule_node_id,
                        relationship="EVALUATED_BY"
                    ))

        # 6. Add Verdict Node
        verdict_node_id = f"verdict_{scan_id}"
        verdict_status = scan_data.get("status", "NEEDS_REVIEW")
        nodes.append(GraphNode(
            id=verdict_node_id,
            type="VERDICT",
            label=f"Screening Verdict: {verdict_status}",
            details={
                "public_label": scan_data.get("public_label", ""),
                "screening_confidence": scan_data.get("screening_confidence", 0.0),
                "disclaimer": scan_data.get("disclaimer", "")
            }
        ))

        # Link Rules -> Verdict
        for chk in checks:
            rule_id = chk.get("rule_id", "LM_UNKNOWN")
            edges.append(GraphEdge(
                source=f"rule_{rule_id}",
                target=verdict_node_id,
                relationship="CONTRIBUTES_TO",
                details={"status": chk.get("status")}
            ))

        return EvidenceGraphResponse(
            scan_id=scan_id,
            nodes=nodes,
            edges=edges,
            summary={
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "verdict": verdict_status
            }
        )
