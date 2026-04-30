import torch
import torch.nn as nn
import os
import yaml
from pathlib import Path
from torch.utils.data import DataLoader
from tqdm import tqdm
from dataset.salicon_dataset import SALICONDataset
from models.saliency_model import SaliencyModel

class KLDivergenceLoss(nn.Module):
    def __init__(self,eps=1e-8):
        super().__init__()
        self.eps = eps

    def forward(self, pred, target):
        pred = pred.clamp(min=self.eps)
        target = target.clamp(min=self.eps)

        loss = target * torch.log(target/pred)
        loss = loss.sum(dim=(1,2,3))
        return loss.mean()
    

# class Training(nn.Train)

def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    running_loss = 0.0
    pbar = tqdm(loader, desc="Training", leave=False)
    for batch in pbar:
        images = batch["image"].to(device)
        targets = batch["map"].to(device)

        # print(f"Image size: {images.shape} and target size: {targets.size}")

        optimizer.zero_grad()

        preds = model(images)
        # print(f"Preds : {preds.shape}")
        loss = criterion(preds, targets)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        pbar.set_postfix(loss=f"{loss.item():.4f}")
    
    return running_loss / len(loader)


@torch.no_grad()
def validate_one_epoch(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0

    pbar = tqdm(loader, desc="Validation", leave=False)
    for batch in pbar:
        images = batch["image"].to(device)
        targets = batch["map"].to(device)
        
        preds = model(images)
        loss = criterion(preds, targets)
        
        running_loss += loss.item()
        pbar.set_postfix(val_loss=f"{loss.item():.4f}")
    
    return running_loss / len(loader)


def save_checkpoint(state, save_path):
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state,save_path)

def train():
    path = "configs/config.yaml"
    with open(path,"r") as f:
        config  = yaml.safe_load(f)


    root_dir = config["dataset"]["root_dir"]
    image_size = tuple(config["dataset"]["image_size"])

    batch_size = int(config["dataloader"]["batch_size"])
    num_workers = int(config["dataloader"]["num_workers"])

    epochs = int(config["training"]["epochs"])
    lr = float(config["training"]["lr"])

    save_dir = config["paths"]["save_dir"]
    pretrained = config["model"]["pretrained"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)
    # print("torch version:", torch.__version__)
    # print("cuda available:", torch.cuda.is_available())
    # print("torch cuda version:", torch.version.cuda)
    # print("device count:", torch.cuda.device_count())

    train_dataset = SALICONDataset(root_dir=root_dir, split="train", image_size=image_size)
    val_dataset = SALICONDataset(root_dir=root_dir, split="val", image_size=image_size)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True if device.type == "cuda" else False
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True if device.type == "cuda" else False
    )

    model = SaliencyModel(pretrained=pretrained).to(device)
    criterion = KLDivergenceLoss()
    optimizer = torch.optim.Adam(model.parameters(),lr=lr)

    best_val_loss = float("inf")

    for epoch in range(1, epochs + 1):
        print(f"\nEpoch {epoch}/{epochs}")

        train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_loss = validate_one_epoch(model, val_loader, criterion, device)

        print(f"Train Loss: {train_loss}")
        print(f"Val Loss: {val_loss}")

        save_checkpoint(
            {
                "epoch":epoch,
                "model_state_dict":model.state_dict(),
                "optimizer_state_dict":optimizer.state_dict(),
                "train_loss": train_loss,
                "val_loss":val_loss
            },
            os.path.join(save_dir,"last.pth")
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            save_checkpoint(
                {
                    "epoch":epoch,
                    "model_state_dict":model.state_dict(),
                    "optimizer_state_dict":optimizer.state_dict(),
                    "train_loss": train_loss,
                    "val_loss":val_loss
                },
                os.path.join(save_dir,"best.pth")
            )
            print("Best checkpoint saved.")