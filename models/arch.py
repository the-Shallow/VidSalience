import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models

class Encoder(nn.Module):
    def __init__(self, pretrained=True):
        super().__init__()

        vgg = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1 if pretrained else None)
        features = list(vgg.features)

        for idx in [23,30]:
            if isinstance(features[idx], nn.MaxPool2d):
                features[idx] = nn.MaxPool2d(kernel_size=2,stride=1, padding=0)
        
        for idx in [24,26,28]:
            if isinstance(features[idx], nn.Conv2d):
                old = features[idx]
                features[idx] = nn.Conv2d(
                    in_channels=old.in_channels,
                    out_channels=old.out_channels,
                    kernel_size=old.kernel_size,
                    stride=old.stride,
                    padding=2,
                    dilation=2,
                    bias=(old.bias is not None),
                )
                features[idx].weight.data.copy_(old.weight.data)
                if old.bias is not None:
                    features[idx].bias.data.copy_(old.bias.data)
        
        self.features = nn.ModuleList(features)

    def forward(self,x):
        feat15, feat22, feat29 = None, None, None
        # print(self.features)
        for i, layer in enumerate(self.features):
            x = layer(x)

            if i == 15:
                feat15 = x
            elif i == 22:
                feat22 = x
            elif i == 29:
                feat29 = x
        
        return feat15, feat22, feat29, x
    

class ASPPBranch(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, dilation):
        super().__init__()
        padding = 0 if kernel_size == 1 else dilation
        self.block = nn.Sequential(
            nn.Conv2d(
                in_channels=in_channels,
                out_channels=out_channels,
                kernel_size=kernel_size,
                padding=padding,
                dilation=dilation,
                bias=True
            ),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.block(x)
    
class GlobalContextBranch(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=1, bias=True)
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self,x):
        h,w = x.shape[2:]
        pooled = F.adaptive_avg_pool2d(x, output_size=1)
        pooled = self.conv(pooled)
        pooled = self.relu(pooled)
        pooled = F.interpolate(pooled, size=(h,w), mode="bilinear", align_corners=False)
        return pooled
    

class ASPP(nn.Module):
    def __init__(self, in_channels, out_channels=256):
        super().__init__()

        self.branch1 = ASPPBranch(in_channels, out_channels, kernel_size=1, dilation=1)
        self.branch2 = ASPPBranch(in_channels, out_channels, kernel_size=3, dilation=4)
        self.branch3 = ASPPBranch(in_channels, out_channels, kernel_size=3, dilation=8)
        self.branch4 = ASPPBranch(in_channels, out_channels, kernel_size=3, dilation=12)
        self.branch5 = GlobalContextBranch(in_channels, out_channels)

        self.project = nn.Sequential(
            nn.Conv2d(in_channels=out_channels*5, out_channels=out_channels, kernel_size=1, bias=True),
            nn.ReLU(inplace=True)
        )

    def forward(self,x):
        b1 = self.branch1(x)
        b2 = self.branch2(x)
        b3 = self.branch3(x)
        b4 = self.branch4(x)
        b5 = self.branch5(x)

        x = torch.cat([b1, b2, b3, b4, b5], dim=1)
        x = self.project(x)
        return x
    
class DecoderBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=3, padding=1, bias=True),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        x = self.conv(x)
        return x
    
class Decoder(nn.Module):
    def __init__(self, in_channels=256):
        super().__init__()
        self.block1 = DecoderBlock(in_channels, 128)
        self.block2 = DecoderBlock(128, 64)
        self.block3 = DecoderBlock(64,32)
        self.final_conv = nn.Conv2d(32,1, kernel_size=3, padding=1, bias=True)

    def forward(self, x):
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.final_conv(x)
        return x