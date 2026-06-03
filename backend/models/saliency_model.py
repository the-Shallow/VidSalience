import torch
import torch.nn as nn
import torch.nn.functional as F
from models.arch import UNet


class SaliencyModel(nn.Module):
    def __init__(self, pretrained=True):
        super().__init__()
        self.unet = UNet(in_channels=3, out_channels=1)

    @staticmethod
    def normalize_map(x, eps=1e-8):
        x = F.relu(x)
        x = x / (x.sum(dim=(2,3), keepdim=True) + eps)
        return x

    def forward(self, x):
        x = self.unet(x)
        x = self.normalize_map(x)
        return x