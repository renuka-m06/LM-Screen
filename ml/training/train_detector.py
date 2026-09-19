import argparse
import os

def train_yolo_detector(data_yaml: str, epochs: int, batch_size: int, weights_dir: str):
    """
    Train a YOLOv8 model for package and panel detection.
    """
    print(f"Starting YOLO detection training with data={data_yaml}, epochs={epochs}")
    
    try:
        from ultralytics import YOLO
        
        # Initialize YOLOv8n (nano) as the base model
        model = YOLO('yolov8n.pt') 
        
        # Train the model
        results = model.train(
            data=data_yaml,
            epochs=epochs,
            batch=batch_size,
            project=weights_dir,
            name='panel_detector',
            exist_ok=True
        )
        
        print(f"Training completed. Weights saved in {weights_dir}/panel_detector/weights/")
        
        # Export to ONNX for production inference if needed
        model.export(format='onnx')
        
    except ImportError:
        print("ultralytics package not found. Please install requirements to train.")
    except Exception as e:
        print(f"Training failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--out", type=str, default="models/training_runs")
    
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    
    train_yolo_detector(args.data, args.epochs, args.batch, args.out)
