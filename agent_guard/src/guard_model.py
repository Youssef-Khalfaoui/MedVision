"""
Agent 0 - Guard Agent Model.
Frozen TorchXRayVision DenseNet121 backbone + simple Linear classifier head.
Outputs a single logit (CXR vs. Not-CXR).
"""
import torch
import torch.nn as nn
import torchxrayvision as xrv

class GuardAgent(nn.Module):
    def __init__(self):
        super().__init__()
        # Load the same CXR-pretrained backbone as Agent 1
        self.backbone = xrv.models.DenseNet(weights="densenet121-res224-chex")
        for param in self.backbone.parameters():
            param.requires_grad = False  # Freeze backbone

        # xrv's DenseNet can have either:
        #   - self.classifier  (nn.Conv2d or nn.Linear)  — older / single-task
        #   - self.classifiers (nn.ModuleList of nn.Linear per class) — newer multi-label
        # We replace whichever exists with a single binary classifier.
        if hasattr(self.backbone, 'classifier') and self.backbone.classifier is not None:
            if hasattr(self.backbone.classifier, 'in_features'):
                in_features = self.backbone.classifier.in_features
            elif hasattr(self.backbone.classifier, 'in_channels'):
                in_features = self.backbone.classifier.in_channels
            else:
                in_features = 1024  # DenseNet121 default
        elif hasattr(self.backbone, 'classifiers') and len(self.backbone.classifiers) > 0:
            in_features = self.backbone.classifiers[0].in_features
        else:
            in_features = 1024  # DenseNet121 default

        self.backbone.classifier = nn.Linear(in_features, 1)

    def forward(self, x):
        # xrv expects normalized [-1024, 1024] 1-channel input.
        features = self.backbone.features(x)
        features = torch.relu(features)
        pooled = torch.nn.functional.adaptive_avg_pool2d(features, (1, 1))
        flat = torch.flatten(pooled, 1)
        logits = self.backbone.classifier(flat)
        return logits

if __name__ == "__main__":
    model = GuardAgent()
    dummy = torch.randn(2, 1, 224, 224)
    out = model(dummy)
    print("Output shape:", out.shape)  # Should be [2, 1]
    print("Smoke test passed.")
