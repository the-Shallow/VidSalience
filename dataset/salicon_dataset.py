import os
from pathlib import Path

import torch
from torch.utils.data import Dataset
from PIL import Image
from torchvision import transforms

class SALICONDataset(Dataset):
    def __init__(self, root_dir, split="train", image_size = (256, 192)):
        self.root_dir = Path(root_dir)
        self.split = split
        self.img_size = image_size

        self.img_dir = self.root_dir / "images" / split
        self.map_dir = self.root_dir / "maps" / split if split in ["train", "val"] else None

        self.image_paths = sorted([
            p for p in self.img_dir.iterdir()
        ])

        self.image_transform = transforms.Compose([
            transforms.Resize(image_size),
            transforms.ToTensor()
        ])

        self.map_transform = transforms.Compose([
            transforms.Resize(image_size),
            transforms.ToTensor()
        ])

    def __len__(self):
        return len(self.image_paths)

    def get_map_path(self, img_path):
        stem = img_path.stem

        for ext in [".png", ".jpg", ".jpeg"]:
            candidate = self.map_dir / f"{stem}{ext}"
            if candidate.exists():
                return candidate
            
    def normalize_map(self, sal_map, eps = 1e-8):
        sal_map = sal_map.float()
        sal_map = sal_map.clamp(min=0)
        sal_map = sal_map / (sal_map.sum() + eps)
        return sal_map
    
    def __getitem__(self,idx):
        img_path = self.image_paths[idx]
        img = Image.open(img_path).convert("RGB")
        img = self.image_transform(img)

        sample = {
            "image": img,
            "image_path": str(img_path)
        }

        map_path = self.get_map_path(img_path)
        sal_map = Image.open(map_path).convert("L")
        sal_map = self.map_transform(sal_map)
        sal_map = self.normalize_map(sal_map)

        sample["map"] = sal_map
        sample["map_path"] = str(map_path)
        return sample 