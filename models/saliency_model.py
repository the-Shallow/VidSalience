import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
from models.arch import Encoder, ASPP , Decoder


class SaliencyModel(nn.Module):
    def __init__(self, pretrained=True):
        super().__init__()
        self.encoder = Encoder(pretrained=pretrained)
        self.aspp = ASPP(in_channels=1280, out_channels=256)
        self.decoder = Decoder(in_channels=256)

    @staticmethod
    def normalize_map(x, eps=1e-8):
        x = F.relu(x)
        x = x / (x.sum(dim=(2,3), keepdim=True) + eps)
        return x

    def forward(self, x):
        input_h, input_w = x.shape[2:]
        feat10, feat14, feat18, _ = self.encoder(x)
        target_size = feat18.shape[2:]
        feat10 = F.interpolate(feat10, size=target_size, mode="bilinear", align_corners=False)
        feat14 = F.interpolate(feat14, size=target_size, mode="bilinear", align_corners=False)

        fused = torch.cat([feat10,feat14, feat18], dim = 1)

        x = self.aspp(fused)
        x = self.decoder(x)

        x = F.interpolate(x, size=(input_h, input_w), mode="bilinear", align_corners=False)
        x = self.normalize_map(x)
        return x
    
# if __name__ == "__main__":
#     transform = transforms.Compose([
#         transforms.Resize((256, 192)),
#         transforms.ToTensor()
#     ])
#     img = "dataset/images/train/COCO_train2014_000000000009.jpg"
#     img = Image.open(img).convert("RGB")
#     img = transform(img)
#     img = img.unsqueeze(0)
#     print("Input shape", img.shape)
#     saliency_mod = SaliencyModel()
#     feat10, feat14, feat18, final = saliency_mod.encoder(img)
#     print(feat10.shape, feat14.shape, feat18.shape, final.shape)