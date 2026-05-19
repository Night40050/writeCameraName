# Transfer Learning Gesture Recognition Demo

## Overview

This module demonstrates **transfer learning** for gesture recognition using a pre-trained MobileNetV2 model. It is a **self-contained demonstration** that does NOT interfere with the existing MediaPipe-based gesture classifier used in the main AirSign application.

## What is Transfer Learning?

**Transfer learning** is a machine learning technique where a model trained on one task is repurposed for a related task. Instead of training a neural network from scratch (which requires massive datasets and computational resources), we:

1. **Start with a pre-trained model** - Use a model already trained on a large dataset (e.g., ImageNet with 1.2M images)
2. **Freeze the base layers** - Keep the learned feature extractors (edges, textures, shapes) unchanged
3. **Replace the final layer** - Add a new classification head specific to our task
4. **Train only the new layer** - Fine-tune just the final layer on our smaller dataset

### Benefits of Transfer Learning

- ✅ **Requires less data** - Can work with hundreds of samples instead of millions
- ✅ **Faster training** - Only training the final layer is much quicker
- ✅ **Better performance** - Leverages features learned from large-scale datasets
- ✅ **Lower computational cost** - No need for expensive GPU clusters

## Why MobileNetV2?

**MobileNetV2** was chosen for this demonstration because:

1. **Lightweight Architecture** 
   - Only ~3.5M parameters (vs 138M for VGG16)
   - Designed for mobile and embedded devices
   - Fast inference suitable for real-time applications

2. **Efficient Design**
   - Uses depthwise separable convolutions
   - Inverted residual structure with linear bottlenecks
   - Excellent accuracy-to-size ratio

3. **Pre-trained on ImageNet**
   - Already learned robust visual features
   - Trained on 1.2M images across 1000 categories
   - Strong transfer learning baseline

4. **Perfect for Gesture Recognition**
   - Small enough to run on edge devices
   - Fast enough for real-time video processing
   - Proven effective for hand/gesture tasks

## Model Architecture

```
Input (64x64 RGB) 
    ↓
Resize to 224x224 (MobileNetV2 requirement)
    ↓
MobileNetV2 Base (FROZEN)
├── Convolutional layers
├── Inverted residual blocks
└── Feature extraction (1280 features)
    ↓
Classification Head (TRAINABLE)
├── Dropout (0.2)
└── Linear (1280 → 5 classes)
    ↓
Output: [DRAW, ERASE, SELECT, SCROLL, IDLE]
```

**Trainable Parameters:** ~6,405 (only the final layer)  
**Frozen Parameters:** ~2.2M (entire MobileNetV2 base)

## Gesture Classes

The model is trained to recognize 5 gesture types:

| Class | Description | Use Case |
|-------|-------------|----------|
| **DRAW** | Index finger extended | Drawing on canvas |
| **ERASE** | Two fingers extended (peace sign) | Erasing content |
| **SELECT** | Closed fist | Clicking/selecting UI elements |
| **SCROLL** | Open palm with all fingers | Scrolling or panning |
| **IDLE** | No hand detected | Background/no gesture |

## Synthetic Data Generation

Since this is a demonstration, we generate **synthetic training data** programmatically:

- **500 samples per class** (2,500 total images)
- **64x64 pixel images** with hand-like shapes
- **Geometric primitives** (circles, lines, ellipses) simulate hand poses
- **Random augmentations** (rotation, translation, noise)
- **80/20 train/validation split** (2,000 train, 500 validation)

### Why Synthetic Data?

- ✅ No need to collect and label real images
- ✅ Demonstrates the training pipeline
- ✅ Reproducible and version-controlled
- ✅ Easy to modify and experiment with

**Note:** For production use, you would replace this with real hand images captured from video frames.

## Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Optimizer** | Adam | Adaptive learning rate, works well for fine-tuning |
| **Learning Rate** | 0.001 | Standard for transfer learning |
| **Loss Function** | CrossEntropyLoss | Multi-class classification |
| **Batch Size** | 32 | Balances memory and gradient stability |
| **Epochs** | 10 | Sufficient for demonstration |
| **Image Size** | 64x64 → 224x224 | Resized to MobileNetV2 input size |

## Usage

### 1. Install Dependencies

```bash
cd airsign/training
pip install -r requirements.txt
```

### 2. Run Training

```bash
python train_gesture_demo.py
```

### 3. Expected Output

The script will:
1. Generate 2,500 synthetic images (500 per class)
2. Split into training (2,000) and validation (500) sets
3. Load pre-trained MobileNetV2 and freeze base layers
4. Train only the classification head for 10 epochs
5. Print metrics after each epoch:
   - Training loss and accuracy
   - Validation loss and accuracy
6. Save outputs to `outputs/`:
   - `gesture_model.pth` - Trained model weights
   - `learning_curve.png` - Loss and accuracy plots

### Example Output

```
Epoch  1/10 | Train Loss: 1.2345 | Train Acc: 45.67% | Val Loss: 1.1234 | Val Acc: 50.12%
Epoch  2/10 | Train Loss: 0.8765 | Train Acc: 65.43% | Val Loss: 0.8123 | Val Acc: 68.90%
...
Epoch 10/10 | Train Loss: 0.1234 | Train Acc: 95.67% | Val Loss: 0.2345 | Val Acc: 92.34%
```

## Future Integration with AirSign

This demonstration model could potentially **replace the MediaPipe gesture classifier** in the future:

### Current System (MediaPipe)
- ✅ No training required
- ✅ Works out-of-the-box
- ✅ Robust hand tracking
- ❌ Limited to predefined gestures
- ❌ Rule-based classification (finger angles, distances)
- ❌ Hard to customize

### Potential ML System (MobileNetV2)
- ✅ Fully customizable gestures
- ✅ Can learn complex patterns
- ✅ Adaptable to user-specific gestures
- ❌ Requires training data
- ❌ Needs periodic retraining
- ❌ More complex deployment

### Integration Steps (Future Work)

1. **Data Collection**
   - Capture real hand images from webcam
   - Label gestures manually or semi-automatically
   - Build a dataset of 1000+ images per gesture

2. **Model Training**
   - Train on real data instead of synthetic
   - Experiment with data augmentation
   - Fine-tune hyperparameters

3. **Model Export**
   - Convert to ONNX format for faster inference
   - Optimize for CPU/edge deployment
   - Quantize for mobile devices

4. **Integration**
   - Replace `core/gesture_classifier.py` logic
   - Add model loading in initialization
   - Run inference on hand crop from MediaPipe
   - Map predictions to gesture actions

5. **Continuous Learning**
   - Collect user corrections
   - Retrain periodically
   - Implement active learning

## File Structure

```
training/
├── train_gesture_demo.py    # Main training script
├── README.md                 # This file
├── requirements.txt          # Python dependencies
└── outputs/                  # Generated outputs
    ├── gesture_model.pth     # Trained model weights
    └── learning_curve.png    # Training visualization
```

## Technical Details

### Data Preprocessing

1. **Synthetic generation** - Create hand-like shapes with OpenCV
2. **Color conversion** - BGR → RGB (OpenCV to PyTorch)
3. **Resize** - 64x64 → 224x224 (MobileNetV2 input size)
4. **Normalization** - ImageNet mean/std: `[0.485, 0.456, 0.406]` / `[0.229, 0.224, 0.225]`
5. **Tensor conversion** - NumPy array → PyTorch tensor

### Training Loop

```python
for epoch in range(NUM_EPOCHS):
    # Training phase
    model.train()
    for images, labels in train_loader:
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
    
    # Validation phase
    model.eval()
    with torch.no_grad():
        for images, labels in val_loader:
            outputs = model(images)
            # Calculate metrics
```

### Model Saving

The model is saved using PyTorch's state dict:

```python
torch.save(model.state_dict(), 'gesture_model.pth')
```

To load later:

```python
model = create_transfer_learning_model()
model.load_state_dict(torch.load('gesture_model.pth'))
model.eval()
```

## Limitations

1. **Synthetic Data** - Not representative of real hand images
2. **Simple Shapes** - Geometric primitives don't capture hand complexity
3. **No Temporal Information** - Single frames, no motion tracking
4. **Fixed Gestures** - Predefined set, not user-customizable
5. **Demonstration Only** - Not production-ready

## References

- **MobileNetV2 Paper:** [Sandler et al., 2018](https://arxiv.org/abs/1801.04381)
- **Transfer Learning:** [CS231n Stanford Course](http://cs231n.stanford.edu/transfer-learning/)
- **PyTorch Transfer Learning Tutorial:** [Official Docs](https://pytorch.org/tutorials/beginner/transfer_learning_tutorial.html)

## License

This demonstration module is part of the AirSign project and follows the same license.

---

**Note:** This is a standalone demonstration module. It does NOT modify or interfere with the existing MediaPipe-based gesture recognition system used in the main AirSign application.
