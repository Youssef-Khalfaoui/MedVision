"""
Agent 1 v2 - ConvNeXtV2Predictor Architecture
ConvNeXtV2-Base (MIMIC-CXR/PadChest-pretrained, via timm) backbone
+ HierarchicalGAT head + Platt calibration + hierarchy enforcement.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import timm
from torch_geometric.nn import GATConv

CATEGORIES = [
    "No Finding", "Enlarged Cardiomediastinum", "Cardiomegaly", "Lung Opacity",
    "Lung Lesion", "Edema", "Consolidation", "Pneumonia", "Atelectasis",
    "Pneumothorax", "Pleural Effusion", "Pleural Other", "Fracture",
    "Support Devices",
]
NUM_LABELS = len(CATEGORIES)
LABEL_TO_IDX = {name: i for i, name in enumerate(CATEGORIES)}

HIERARCHY_EDGES = [
    ("Enlarged Cardiomediastinum", "Cardiomegaly"),
    ("Lung Opacity", "Lung Lesion"),
    ("Lung Opacity", "Edema"),
    ("Lung Opacity", "Consolidation"),
    ("Lung Opacity", "Pneumonia"),
    ("Lung Opacity", "Atelectasis"),
    ("Pneumonia", "Consolidation"),
]

def build_hierarchy_edge_index():
    edges = []
    for parent, child in HIERARCHY_EDGES:
        p, c = LABEL_TO_IDX[parent], LABEL_TO_IDX[child]
        edges.append((p, c))
        edges.append((c, p))
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    return edge_index

class HierarchicalGAT(nn.Module):
    def __init__(self, input_dim=1024, hidden_dim=256, num_layers=3, heads=4, dropout=0.3):
        super().__init__()
        self.num_labels = NUM_LABELS
        self.node_proj = nn.ModuleList([nn.Linear(input_dim, hidden_dim) for _ in range(NUM_LABELS)])
        self.gat_layers = nn.ModuleList()
        in_dim = hidden_dim
        for i in range(num_layers):
            concat = (i < num_layers - 1)
            out_dim = hidden_dim // heads if concat else hidden_dim
            self.gat_layers.append(GATConv(in_dim, out_dim, heads=heads, concat=concat, dropout=dropout))
            in_dim = out_dim * heads if concat else out_dim
        self.dropout = nn.Dropout(dropout)
        self.output_head = nn.Linear(in_dim, 1)
        self.register_buffer("hierarchy_edge_index", build_hierarchy_edge_index())
        self.register_buffer("cooccurrence_edge_index", None)

    def set_cooccurrence_edges(self, edge_index: torch.Tensor):
        self.cooccurrence_edge_index = edge_index.to(self.hierarchy_edge_index.device)

    def _get_edge_index(self):
        if self.cooccurrence_edge_index is not None:
            return torch.cat([self.hierarchy_edge_index, self.cooccurrence_edge_index], dim=1)
        return self.hierarchy_edge_index

    def forward(self, image_features: torch.Tensor) -> torch.Tensor:
        batch_size = image_features.size(0)
        device = image_features.device
        edge_index = self._get_edge_index().to(device)
        node_feats = torch.stack([proj(image_features) for proj in self.node_proj], dim=1)
        hidden_dim = node_feats.size(-1)
        flat_feats = node_feats.reshape(batch_size * NUM_LABELS, hidden_dim)
        batch_edge_index = []
        for b in range(batch_size):
            offset = b * NUM_LABELS
            batch_edge_index.append(edge_index + offset)
        batch_edge_index = torch.cat(batch_edge_index, dim=1)
        x = flat_feats
        for i, gat in enumerate(self.gat_layers):
            x = gat(x, batch_edge_index)
            if i < len(self.gat_layers) - 1:
                x = F.elu(x)
                x = self.dropout(x)
        logits = self.output_head(x)
        logits = logits.view(batch_size, NUM_LABELS)
        return logits

class PlattCalibration(nn.Module):
    def __init__(self, num_labels=NUM_LABELS):
        super().__init__()
        self.A = nn.Parameter(torch.ones(num_labels))
        self.B = nn.Parameter(torch.zeros(num_labels))
    def forward(self, raw_logits: torch.Tensor) -> torch.Tensor:
        return self.A * raw_logits + self.B

def enforce_hierarchy(probs: torch.Tensor) -> torch.Tensor:
    probs = probs.clone()
    for parent, child in HIERARCHY_EDGES:
        p_idx, c_idx = LABEL_TO_IDX[parent], LABEL_TO_IDX[child]
        probs[:, c_idx] = torch.minimum(probs[:, c_idx], probs[:, p_idx])
    return probs

CONVNEXT_HUB_REPO = "hieuphamha/cxrlt2026-task1-convnextv2"
CONVNEXT_WEIGHTS_FILE = "convnextv2_base_mimic-cxr_padchest_csra_dbcas.safetensors"

class ConvNeXtV2Backbone(nn.Module):
    def __init__(self, pretrained=True):
        super().__init__()
        self.backbone = timm.create_model("convnextv2_base", pretrained=False, num_classes=0, drop_path_rate=0.2, global_pool="avg")
        self.output_dim = self.backbone.num_features
        if pretrained:
            self._load_cxr_pretrained_weights()

    def _load_cxr_pretrained_weights(self):
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file
        ckpt_path = hf_hub_download(CONVNEXT_HUB_REPO, CONVNEXT_WEIGHTS_FILE)
        full_state = load_file(ckpt_path)
        backbone_state = {k[len("backbone."):]: v for k, v in full_state.items() if k.startswith("backbone.")}
        missing, unexpected = self.backbone.load_state_dict(backbone_state, strict=False)
        print(f"[ConvNeXtV2Backbone] Loaded CXR-pretrained backbone weights. Missing: {len(missing)}, unexpected: {len(unexpected)}")
        if len(missing) > 0: print(f"[ConvNeXtV2Backbone] WARNING - missing keys (first 5): {missing[:5]}")

    def forward(self, x):
        return self.backbone(x)

class ConvNeXtPredictor(nn.Module):
    def __init__(self, pretrained_backbone=True, gat_hidden_dim=256, gat_layers=3, gat_heads=4, dropout=0.3):
        super().__init__()
        self.backbone = ConvNeXtV2Backbone(pretrained=pretrained_backbone)
        self.gat_head = HierarchicalGAT(input_dim=self.backbone.output_dim, hidden_dim=gat_hidden_dim, num_layers=gat_layers, heads=gat_heads, dropout=dropout)
        self.calibration = PlattCalibration()

    def set_cooccurrence_edges(self, edge_index: torch.Tensor):
        self.gat_head.set_cooccurrence_edges(edge_index)

    def forward(self, images: torch.Tensor, apply_hierarchy: bool = True):
        features = self.backbone(images)
        raw_logits = self.gat_head(features)
        calibrated_logits = self.calibration(raw_logits)
        probs = torch.sigmoid(calibrated_logits)
        if apply_hierarchy: probs = enforce_hierarchy(probs)
        return {"raw_logits": raw_logits, "calibrated_logits": calibrated_logits, "probabilities": probs}

if __name__ == "__main__":
    model = ConvNeXtPredictor()
    dummy_images = torch.randn(2, 3, 512, 512)
    out = model(dummy_images)
    print("raw_logits shape:", out["raw_logits"].shape)
    print("calibrated_logits shape:", out["calibrated_logits"].shape)
    print("probabilities shape:", out["probabilities"].shape)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {n_params:,}")
