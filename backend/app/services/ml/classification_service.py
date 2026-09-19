import numpy as np
from typing import Dict, Any, List
from ai.context_classifier import ContextClassifier
from ml.inference.classifier import MLProductClassifier

class ClassificationService:
    """
    Standardized service for Product Classification.
    """
    def __init__(self):
        self.ml_classifier = MLProductClassifier()
        self.heuristic_classifier = ContextClassifier()

    def classify(self, ocr_tokens: List[Dict[str, Any]], image_np: np.ndarray = None) -> Dict[str, Any]:
        """
        Classify product category.
        """
        ml_result = self.ml_classifier.classify(text_tokens=ocr_tokens, image_np=image_np)
        
        if ml_result.get("status") == "MODEL_NOT_TRAINED":
            # Fallback to text heuristics
            h_result = self.heuristic_classifier.classify_context(ocr_tokens)
            return {
                "category": h_result.get("product_category", "UNKNOWN"),
                "subcategory": None,
                "confidence": h_result.get("context_confidence", 0.0),
                "model_version": "heuristic-nlp-v1",
                "status": "MODEL_NOT_TRAINED",
                "method": "NLP_HEURISTIC"
            }
            
        return {
            "category": ml_result.get("category", "UNKNOWN"),
            "subcategory": ml_result.get("subcategory"),
            "confidence": ml_result.get("confidence", 0.0),
            "model_version": ml_result.get("model_version"),
            "status": "SUCCESS",
            "method": "ML_MODEL"
        }
