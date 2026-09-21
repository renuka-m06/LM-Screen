import pytest
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from backend.app.services.ml.registry import ModelRegistry, ModelStatus
from ml.inference.detector import MLPackageDetector
from backend.app.services.ml.detection_service import DetectionService

def test_model_registry():
    model = ModelRegistry.get_model("yolov8-panel-detector")
    assert model is not None
    assert model["model_name"] == "yolov8-panel-detector"
    assert model["status"] in [ModelStatus.MODEL_READY, ModelStatus.MODEL_NOT_FOUND, ModelStatus.MODEL_LOAD_ERROR]

def test_ml_package_detector_missing_weights():
    # If we initialize it without weights, it should fall back properly
    detector = MLPackageDetector(model_name="yolov8-panel-detector")
    
    # Create dummy image
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    result = detector.detect(image)
    assert result["status"] in [ModelStatus.MODEL_NOT_FOUND, ModelStatus.MODEL_LOAD_ERROR]
    assert "model_name" in result

def test_bbox_validation():
    detector = MLPackageDetector(model_name="yolov8-panel-detector")
    
    # Valid
    assert detector._validate_bbox([10, 10, 50, 50], (100, 100, 3)) == True
    
    # Invalid (width/height <= 0)
    assert detector._validate_bbox([50, 50, 10, 10], (100, 100, 3)) == False
    
    # Out of bounds
    assert detector._validate_bbox([-10, 10, 50, 50], (100, 100, 3)) == False
    assert detector._validate_bbox([10, 10, 150, 150], (100, 100, 3)) == False

def test_detection_service_fallback():
    service = DetectionService()
    
    # Create dummy image
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    result = service.detect(image)
    # The heuristic might detect nothing on a black image
    assert result["method"] == "COMPUTER_VISION_HEURISTIC"
    
    # If heuristic detects something, it should have confidence UNKNOWN
    if result["detections"]:
        assert result["detections"][0]["confidence"] == "UNKNOWN"
        assert result["detections"][0]["source"] == "HEURISTIC"
