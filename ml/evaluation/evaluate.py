import argparse
from typing import Dict, Any

def evaluate_detection(model_path: str, dataset_yaml: str) -> Dict[str, Any]:
    """
    Evaluates the YOLO package/panel detector on a validation/test set.
    """
    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        metrics = model.val(data=dataset_yaml)
        
        return {
            "status": "EVALUATED",
            "mAP_50_95": metrics.box.map,
            "mAP_50": metrics.box.map50,
            "precision": metrics.box.p.mean(),
            "recall": metrics.box.r.mean()
        }
    except Exception as e:
        return {
            "status": "NOT EVALUATED",
            "reason": f"Failed to run detection evaluation: {e}"
        }

def evaluate_classification(model_path: str, dataset_path: str) -> Dict[str, Any]:
    """
    Evaluates the product context classifier.
    """
    return {
        "status": "NOT EVALUATED",
        "reason": "TRAINED MODEL/VALIDATED DATASET NOT AVAILABLE"
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate LM-Screen ML models")
    parser.add_argument("--task", type=str, choices=["detection", "classification", "all"], required=True)
    parser.add_argument("--model", type=str, required=True, help="Path to model weights")
    parser.add_argument("--data", type=str, required=True, help="Path to dataset config/folder")
    
    args = parser.parse_args()
    
    if args.task in ["detection", "all"]:
        print("\n--- Detection Evaluation ---")
        res = evaluate_detection(args.model, args.data)
        for k, v in res.items():
            print(f"{k}: {v}")
            
    if args.task in ["classification", "all"]:
        print("\n--- Classification Evaluation ---")
        res = evaluate_classification(args.model, args.data)
        for k, v in res.items():
            print(f"{k}: {v}")

if __name__ == "__main__":
    main()
