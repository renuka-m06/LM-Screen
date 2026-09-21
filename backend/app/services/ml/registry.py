import os
from typing import Dict, Any, List
from datetime import datetime

class ModelStatus:
    MODEL_READY = "MODEL_READY"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_LOAD_ERROR = "MODEL_LOAD_ERROR"
    MODEL_INCOMPATIBLE = "MODEL_INCOMPATIBLE"
    MODEL_DISABLED = "MODEL_DISABLED"

class ModelRegistry:
    """
    Lightweight model registry and configuration system.
    Provides explicit states for ML availability.
    """
    _registry = {}

    @classmethod
    def register_model(cls, config: Dict[str, Any]):
        """
        Registers a model with its configuration.
        """
        model_name = config.get("model_name")
        if not model_name:
            raise ValueError("Model configuration must include 'model_name'")
            
        file_path = config.get("file_path", "")
        
        status = ModelStatus.MODEL_DISABLED
        if config.get("enabled", True):
            if os.path.exists(file_path):
                status = ModelStatus.MODEL_READY
            else:
                status = ModelStatus.MODEL_NOT_FOUND

        cls._registry[model_name] = {
            "model_name": model_name,
            "model_type": config.get("model_type", "unknown"),
            "model_version": config.get("model_version", "v0"),
            "file_path": file_path,
            "enabled": config.get("enabled", True),
            "status": status,
            "classes": config.get("classes", []),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": config.get("metadata", {})
        }

    @classmethod
    def get_model(cls, model_name: str) -> Dict[str, Any]:
        """
        Retrieves model config, re-evaluating physical availability on each request.
        """
        if model_name not in cls._registry:
            return None
            
        cfg = cls._registry[model_name]
        
        # Check current physical state
        if cfg["enabled"]:
            if os.path.exists(cfg["file_path"]):
                cfg["status"] = ModelStatus.MODEL_READY
            else:
                cfg["status"] = ModelStatus.MODEL_NOT_FOUND
        
        return cfg

    @classmethod
    def get_all_models(cls) -> List[Dict[str, Any]]:
        return [cls.get_model(name) for name in cls._registry.keys()]

# Initialize the YOLO Panel Detector in the registry
ModelRegistry.register_model({
    "model_name": "yolov8-panel-detector",
    "model_type": "object_detection",
    "model_version": "v1",
    "file_path": "models/detector.pt", # Relative to execution root
    "enabled": True,
    "classes": [
        "package", "front_panel", "back_panel", "nutrition_panel", 
        "ingredients_panel", "barcode", "declaration_label", "warning_area"
    ],
    "metadata": {
        "framework": "ultralytics/yolov8",
        "description": "Detects core information panels and boundaries on FMCG products."
    }
})
