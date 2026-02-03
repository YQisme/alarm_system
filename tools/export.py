from ultralytics import YOLO

# Load the YOLO26 model
model = YOLO("yolo26m.pt")

# Export the model to TensorRT format
model.export(format="engine",int8=True) 