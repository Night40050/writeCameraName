#!/usr/bin/env python3
"""
Transfer Learning Gesture Recognition Demo
===========================================
This script demonstrates transfer learning using a pre-trained MobileNetV2 model
to classify hand gestures. It generates synthetic training data and trains only
the final classification layer.

This is a self-contained demonstration that does NOT interfere with the existing
MediaPipe-based gesture classifier in the main AirSign application.
"""

import os
import sys
from pathlib import Path
import numpy as np
import cv2
import matplotlib.pyplot as plt
from typing import Tuple, List
import random

# Check for PyTorch
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    from torchvision import models, transforms
except ImportError:
    print("ERROR: PyTorch is not installed.")
    print("Please install required packages:")
    print("  pip install torch torchvision matplotlib")
    sys.exit(1)

# ── Configuration ────────────────────────────────────────────────────────────
GESTURE_CLASSES = ["DRAW", "ERASE", "SELECT", "SCROLL", "IDLE"]
NUM_CLASSES = len(GESTURE_CLASSES)
SAMPLES_PER_CLASS = 500
IMAGE_SIZE = 64
TRAIN_SPLIT = 0.8
BATCH_SIZE = 32
NUM_EPOCHS = 10
LEARNING_RATE = 0.001

# Output directories
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Device configuration
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")


# ── Synthetic Data Generation ───────────────────────────────────────────────
def generate_hand_like_shape(img_size: int = 64, gesture_type: str = "DRAW") -> np.ndarray:
    """
    Generate a synthetic hand-like shape for a given gesture type.
    Uses simple geometric shapes to simulate different hand poses.
    """
    img = np.zeros((img_size, img_size, 3), dtype=np.uint8)
    
    # Add some background noise
    noise = np.random.randint(0, 30, (img_size, img_size, 3), dtype=np.uint8)
    img = cv2.add(img, noise)
    
    # Center point
    cx, cy = img_size // 2, img_size // 2
    
    # Generate different shapes based on gesture type
    if gesture_type == "DRAW":
        # Extended index finger (vertical line + circle at tip)
        cv2.line(img, (cx, cy + 10), (cx, cy - 25), (180, 150, 120), 8)
        cv2.circle(img, (cx, cy - 25), 5, (200, 170, 140), -1)
        # Palm
        cv2.ellipse(img, (cx, cy + 15), (15, 20), 0, 0, 360, (180, 150, 120), -1)
        
    elif gesture_type == "ERASE":
        # Two fingers extended (peace sign)
        cv2.line(img, (cx - 5, cy + 10), (cx - 8, cy - 25), (180, 150, 120), 7)
        cv2.line(img, (cx + 5, cy + 10), (cx + 8, cy - 25), (180, 150, 120), 7)
        cv2.circle(img, (cx - 8, cy - 25), 4, (200, 170, 140), -1)
        cv2.circle(img, (cx + 8, cy - 25), 4, (200, 170, 140), -1)
        # Palm
        cv2.ellipse(img, (cx, cy + 15), (15, 20), 0, 0, 360, (180, 150, 120), -1)
        
    elif gesture_type == "SELECT":
        # Closed fist (filled circle)
        cv2.circle(img, (cx, cy), 18, (180, 150, 120), -1)
        cv2.circle(img, (cx, cy), 18, (150, 120, 90), 2)
        
    elif gesture_type == "SCROLL":
        # Open palm (larger ellipse with fingers)
        cv2.ellipse(img, (cx, cy), (20, 25), 0, 0, 360, (180, 150, 120), -1)
        for i in range(-2, 3):
            x_offset = i * 8
            cv2.line(img, (cx + x_offset, cy - 15), (cx + x_offset, cy - 30), 
                    (180, 150, 120), 5)
            cv2.circle(img, (cx + x_offset, cy - 30), 3, (200, 170, 140), -1)
            
    elif gesture_type == "IDLE":
        # No hand (just noise/background)
        # Add some random shapes to simulate background
        for _ in range(3):
            x, y = random.randint(10, img_size-10), random.randint(10, img_size-10)
            r = random.randint(3, 8)
            color = tuple(random.randint(20, 60) for _ in range(3))
            cv2.circle(img, (x, y), r, color, -1)
    
    # Add random rotation
    angle = random.uniform(-30, 30)
    M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
    img = cv2.warpAffine(img, M, (img_size, img_size))
    
    # Add random translation
    tx = random.randint(-5, 5)
    ty = random.randint(-5, 5)
    M = np.float32([[1, 0, tx], [0, 1, ty]])
    img = cv2.warpAffine(img, M, (img_size, img_size))
    
    return img


def generate_synthetic_dataset() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate synthetic training and validation datasets.
    Returns: (X_train, y_train, X_val, y_val)
    """
    print("\n" + "="*60)
    print("Generating Synthetic Dataset")
    print("="*60)
    
    all_images = []
    all_labels = []
    
    for class_idx, gesture_name in enumerate(GESTURE_CLASSES):
        print(f"Generating {SAMPLES_PER_CLASS} samples for class '{gesture_name}'...")
        for _ in range(SAMPLES_PER_CLASS):
            img = generate_hand_like_shape(IMAGE_SIZE, gesture_name)
            all_images.append(img)
            all_labels.append(class_idx)
    
    # Convert to numpy arrays
    X = np.array(all_images, dtype=np.uint8)
    y = np.array(all_labels, dtype=np.int64)
    
    # Shuffle the data
    indices = np.random.permutation(len(X))
    X = X[indices]
    y = y[indices]
    
    # Split into train and validation
    split_idx = int(len(X) * TRAIN_SPLIT)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    
    print(f"\nDataset created:")
    print(f"  Training samples:   {len(X_train)}")
    print(f"  Validation samples: {len(X_val)}")
    print(f"  Image size:         {IMAGE_SIZE}x{IMAGE_SIZE}")
    print(f"  Number of classes:  {NUM_CLASSES}")
    
    return X_train, y_train, X_val, y_val


# ── PyTorch Dataset ──────────────────────────────────────────────────────────
class GestureDataset(Dataset):
    """Custom Dataset for gesture images."""
    
    def __init__(self, images: np.ndarray, labels: np.ndarray, transform=None):
        self.images = images
        self.labels = labels
        self.transform = transform
    
    def __len__(self) -> int:
        return len(self.images)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        image = self.images[idx]
        label = self.labels[idx]
        
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if self.transform:
            image = self.transform(image)
        
        return image, label


# ── Model Definition ─────────────────────────────────────────────────────────
def create_transfer_learning_model(num_classes: int = NUM_CLASSES) -> nn.Module:
    """
    Create a transfer learning model using pre-trained MobileNetV2.
    Freezes all layers except the final classification head.
    """
    print("\n" + "="*60)
    print("Creating Transfer Learning Model")
    print("="*60)
    
    # Load pre-trained MobileNetV2
    print("Loading pre-trained MobileNetV2...")
    model = models.mobilenet_v2(pretrained=True)
    
    # Freeze all layers
    print("Freezing base model layers...")
    for param in model.parameters():
        param.requires_grad = False
    
    # Replace the classifier head
    # MobileNetV2's classifier is a Sequential with:
    # - Dropout(0.2)
    # - Linear(1280, 1000)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(in_features, num_classes)
    )
    
    print(f"Replaced classification head: {in_features} -> {num_classes} classes")
    
    # Count trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Trainable parameters: {trainable_params:,} / {total_params:,}")
    
    return model


# ── Training Functions ───────────────────────────────────────────────────────
def train_epoch(model: nn.Module, dataloader: DataLoader, criterion, optimizer, device) -> Tuple[float, float]:
    """Train for one epoch. Returns (avg_loss, accuracy)."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for images, labels in dataloader:
        images, labels = images.to(device), labels.to(device)
        
        # Forward pass
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        # Statistics
        running_loss += loss.item() * images.size(0)
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()
    
    avg_loss = running_loss / total
    accuracy = 100.0 * correct / total
    return avg_loss, accuracy


def validate(model: nn.Module, dataloader: DataLoader, criterion, device) -> Tuple[float, float]:
    """Validate the model. Returns (avg_loss, accuracy)."""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)
            
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item() * images.size(0)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    avg_loss = running_loss / total
    accuracy = 100.0 * correct / total
    return avg_loss, accuracy


def train_model(model: nn.Module, train_loader: DataLoader, val_loader: DataLoader, 
                num_epochs: int = NUM_EPOCHS) -> dict:
    """
    Train the model and return training history.
    """
    print("\n" + "="*60)
    print("Training Model")
    print("="*60)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    history = {
        'train_loss': [],
        'train_acc': [],
        'val_loss': [],
        'val_acc': []
    }
    
    print(f"\nTraining for {num_epochs} epochs...")
    print(f"Optimizer: Adam (lr={LEARNING_RATE})")
    print(f"Loss function: CrossEntropyLoss")
    print(f"Batch size: {BATCH_SIZE}")
    print("\n" + "-"*60)
    
    for epoch in range(num_epochs):
        # Train
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, DEVICE)
        
        # Validate
        val_loss, val_acc = validate(model, val_loader, criterion, DEVICE)
        
        # Store history
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)
        
        # Print progress
        print(f"Epoch {epoch+1:2d}/{num_epochs} | "
              f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | "
              f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%")
    
    print("-"*60)
    print("Training completed!")
    
    return history


# ── Visualization ────────────────────────────────────────────────────────────
def plot_learning_curves(history: dict, save_path: Path):
    """Plot and save learning curves."""
    print("\n" + "="*60)
    print("Generating Learning Curves")
    print("="*60)
    
    epochs = range(1, len(history['train_loss']) + 1)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Loss plot
    ax1.plot(epochs, history['train_loss'], 'b-o', label='Training Loss', linewidth=2)
    ax1.plot(epochs, history['val_loss'], 'r-s', label='Validation Loss', linewidth=2)
    ax1.set_xlabel('Epoch', fontsize=12)
    ax1.set_ylabel('Loss', fontsize=12)
    ax1.set_title('Training and Validation Loss', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Accuracy plot
    ax2.plot(epochs, history['train_acc'], 'b-o', label='Training Accuracy', linewidth=2)
    ax2.plot(epochs, history['val_acc'], 'r-s', label='Validation Accuracy', linewidth=2)
    ax2.set_xlabel('Epoch', fontsize=12)
    ax2.set_ylabel('Accuracy (%)', fontsize=12)
    ax2.set_title('Training and Validation Accuracy', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Learning curves saved to: {save_path}")
    
    # Print final metrics
    print(f"\nFinal Metrics:")
    print(f"  Training Loss:      {history['train_loss'][-1]:.4f}")
    print(f"  Training Accuracy:  {history['train_acc'][-1]:.2f}%")
    print(f"  Validation Loss:    {history['val_loss'][-1]:.4f}")
    print(f"  Validation Accuracy: {history['val_acc'][-1]:.2f}%")


# ── Main Execution ───────────────────────────────────────────────────────────
def main():
    """Main training pipeline."""
    print("\n" + "="*60)
    print("TRANSFER LEARNING GESTURE RECOGNITION DEMO")
    print("="*60)
    print(f"PyTorch version: {torch.__version__}")
    print(f"Device: {DEVICE}")
    
    # Set random seeds for reproducibility
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    # 1. Generate synthetic dataset
    X_train, y_train, X_val, y_val = generate_synthetic_dataset()
    
    # 2. Create data transforms
    # MobileNetV2 expects 224x224 RGB images normalized with ImageNet stats
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                           std=[0.229, 0.224, 0.225])
    ])
    
    # 3. Create datasets and dataloaders
    train_dataset = GestureDataset(X_train, y_train, transform=transform)
    val_dataset = GestureDataset(X_val, y_val, transform=transform)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    
    # 4. Create model
    model = create_transfer_learning_model(NUM_CLASSES)
    model = model.to(DEVICE)
    
    # 5. Train model
    history = train_model(model, train_loader, val_loader, NUM_EPOCHS)
    
    # 6. Save model
    model_path = OUTPUT_DIR / "gesture_model.pth"
    torch.save(model.state_dict(), model_path)
    print(f"\n" + "="*60)
    print(f"Model saved to: {model_path}")
    print("="*60)
    
    # 7. Plot and save learning curves
    curve_path = OUTPUT_DIR / "learning_curve.png"
    plot_learning_curves(history, curve_path)
    
    print("\n" + "="*60)
    print("TRAINING COMPLETE!")
    print("="*60)
    print(f"\nOutputs saved in: {OUTPUT_DIR}")
    print(f"  - Model weights: gesture_model.pth")
    print(f"  - Learning curves: learning_curve.png")
    print("\nThis model demonstrates transfer learning but is NOT integrated")
    print("with the main AirSign application (which uses MediaPipe).")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
