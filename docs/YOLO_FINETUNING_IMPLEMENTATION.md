# YOLOv8 Fine-Tuning for Forest Surveillance — Agent Execution Plan

**Project:** VanRakshak
**Goal:** Fine-tune `yolov8n.pt` on forest/aerial surveillance data to detect forest-specific threats (chainsaw operator, illegal logger, unauthorized vehicle in forest, campfire/smoke, wildlife near road) with higher accuracy than generic COCO weights, then integrate the resulting weights into the backend so the demo can show a domain-trained model.
**Execution model:** Each agent task is self-contained with explicit commands, file targets, acceptance criteria, and rollback. Tasks 1–4 run on Google Colab (free GPU). Tasks 5–7 run locally. Tasks must be executed **in order**; if an acceptance criterion fails, stop and report.

---

## Why fine-tune?

| Metric | Generic YOLOv8n (COCO) | Fine-tuned VanRakshak-Forest |
|---|---|---|
| Detects `person` | ✅ | ✅ |
| Aerial/top-down person | ⚠️ Poor | ✅ Better |
| `chainsaw`, `axe` | ❌ Not in COCO | ✅ |
| Smoke/fire plume | ❌ | ✅ |
| Elephant at distance | ⚠️ Marginal | ✅ |
| Forest vehicle vs road vehicle | ❌ | ✅ |

You don't need perfect accuracy. You need to be able to say to judges: **"We trained our own forest-specific model."**

---

## Dataset strategy

Use **Roboflow Universe** — free, pre-labeled, exports directly in YOLOv8 format.

### Recommended datasets to combine

| Dataset | Classes useful | Roboflow URL |
|---|---|---|
| Aerial Person Detection | `person` (top-down) | Search: "aerial person detection" |
| Forest Fire Detection | `fire`, `smoke` | Search: "forest fire yolo" |
| Wildlife Detection | `elephant`, `deer`, `animal` | Search: "wildlife detection yolo" |
| Vehicle Aerial | `car`, `truck` in forest roads | Search: "aerial vehicle detection" |
| Illegal Logging | `chainsaw`, `person`, `log` | Search: "deforestation detection" |

**Target:** ~800–1500 total images across classes. More is better but not required.

> Roboflow slugs below are placeholders — search roboflow.com/universe for each category and use the dataset with the most images. The download format must always be `"yolov8"`.

---

## Agent Task 1 — Set up Colab environment

**Scope:** Google Colab notebook (create new at colab.research.google.com)
**Runtime:** GPU → T4 (free tier sufficient)
**Estimated time:** 5 minutes
**Dependencies:** none

### Instructions

Create a new Colab notebook. In the first cell:

```python
# Cell 1 — Install dependencies
!pip install ultralytics roboflow onnxsim --quiet
import ultralytics
print(ultralytics.__version__)
ultralytics.checks()
```

> **Version note:** this plan targets ultralytics 8.2.x. If your installed version is 8.3+, confirm the train args used in Task 3 are still accepted (the removed `flipud` arg must NOT be passed — see Task 3).

```python
# Cell 2 — Verify GPU
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
```

### Acceptance criteria

- `CUDA available: True`
- No import errors

---

## Agent Task 2 — Download and merge datasets from Roboflow

**Scope:** Colab notebook — data preparation
**Estimated time:** 15–20 minutes
**Dependencies:** Task 1

### Instructions

```python
# Cell 3 — Authenticate with Roboflow
# Create a free account at roboflow.com, get your API key from Settings > API
from roboflow import Roboflow

RF_API_KEY = "YOUR_ROBOFLOW_API_KEY"  # Replace with your key
rf = Roboflow(api_key=RF_API_KEY)
```

```python
# Cell 4 — Download forest fire dataset (use real slugs from your search)
project = rf.workspace().project("forest-fire-detection-ys9cx")
dataset_fire = project.version(1).download("yolov8", location="/content/datasets/fire")
```

```python
# Cell 5 — Download aerial person dataset
project = rf.workspace().project("person-detection-aeria1")
dataset_person = project.version(1).download("yolov8", location="/content/datasets/person")
```

```python
# Cell 6 — Download wildlife dataset
project = rf.workspace().project("wildlife-detection-y6eik")
dataset_wildlife = project.version(1).download("yolov8", location="/content/datasets/wildlife")
```

```python
# Cell 7 — Merge datasets into a single directory structure
import os, shutil, yaml
from pathlib import Path

MERGED = Path("/content/vanrakshak_forest")
for split in ["train", "valid", "test"]:
    (MERGED / split / "images").mkdir(parents=True, exist_ok=True)
    (MERGED / split / "labels").mkdir(parents=True, exist_ok=True)

# Collect all class names across datasets
all_classes = set()
dataset_dirs = [
    "/content/datasets/fire",
    "/content/datasets/person",
    "/content/datasets/wildlife",
]

for ds_dir in dataset_dirs:
    data_yaml = Path(ds_dir) / "data.yaml"
    if data_yaml.exists():
        with open(data_yaml) as f:
            cfg = yaml.safe_load(f)
        all_classes.update(cfg.get("names", []))

# Normalize class list — must be consistent across all label files
CLASS_MAP = {name: i for i, name in enumerate(sorted(all_classes))}
print("Final class map:", CLASS_MAP)
```

```python
# Cell 8 — Copy images and remap label class IDs (fail loudly on unknown classes)
def remap_labels(src_label_dir, dst_label_dir, src_classes, global_class_map):
    """Remap class IDs in label files to match the merged class map."""
    Path(dst_label_dir).mkdir(parents=True, exist_ok=True)
    for lbl_file in Path(src_label_dir).glob("*.txt"):
        new_lines = []
        for line in lbl_file.read_text().strip().splitlines():
            parts = line.split()
            if not parts:
                continue
            old_id = int(parts[0])
            if old_id >= len(src_classes):
                raise ValueError(f"{lbl_file.name}: class id {old_id} out of range for {src_classes}")
            class_name = src_classes[old_id]
            new_id = global_class_map.get(class_name)
            if new_id is None:
                # Never silently keep an unmapped id — it could collide with a
                # different class in the merged map.
                raise ValueError(f"{lbl_file.name}: class '{class_name}' not in merged class map")
            new_lines.append(f"{new_id} " + " ".join(parts[1:]))
        (Path(dst_label_dir) / lbl_file.name).write_text("\n".join(new_lines))

for ds_dir in dataset_dirs:
    data_yaml = Path(ds_dir) / "data.yaml"
    if not data_yaml.exists():
        print(f"SKIP (no data.yaml): {ds_dir}")
        continue
    with open(data_yaml) as f:
        cfg = yaml.safe_load(f)
    src_classes = cfg.get("names", [])
    for split in ["train", "valid", "test"]:
        src_img = Path(ds_dir) / split / "images"
        src_lbl = Path(ds_dir) / split / "labels"
        if src_img.exists():
            for img in src_img.glob("*"):
                shutil.copy(img, MERGED / split / "images" / img.name)
        if src_lbl.exists():
            remap_labels(src_lbl, MERGED / split / "labels", src_classes, CLASS_MAP)

print("Merged dataset:")
for split in ["train", "valid", "test"]:
    n = len(list((MERGED / split / "images").glob("*")))
    print(f"  {split}: {n} images")
```

```python
# Cell 9 — Write merged data.yaml
data_yaml_content = {
    "path": str(MERGED),
    "train": "train/images",
    "val": "valid/images",
    "test": "test/images",
    "nc": len(CLASS_MAP),
    "names": sorted(CLASS_MAP.keys()),
}
with open(MERGED / "data.yaml", "w") as f:
    yaml.dump(data_yaml_content, f)

print("data.yaml written:")
print(yaml.dump(data_yaml_content))

# Sanity check: no label file may contain a class id >= nc
for split in ["train", "valid", "test"]:
    for lbl in (MERGED / split / "labels").glob("*.txt"):
        for line in lbl.read_text().strip().splitlines():
            if not line:
                continue
            assert int(line.split()[0]) < len(CLASS_MAP), f"{lbl} has out-of-range class id"
print("Label sanity check passed.")
```

### Acceptance criteria

- `train` split has at least 500 images
- `valid` split has at least 100 images
- `data.yaml` has consistent `nc` and `names` fields (`len(names) == nc`)
- No label files contain class IDs >= `nc` (the sanity check prints "passed")

---

## Agent Task 3 — Fine-tune YOLOv8n

**Scope:** Colab notebook — training
**Estimated time:** 30–90 minutes (T4 GPU, depends on dataset size)
**Dependencies:** Task 2

### Instructions

```python
# Cell 10 — Train
from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # Start from pretrained COCO weights

results = model.train(
    data="/content/vanrakshak_forest/data.yaml",
    epochs=50,           # 50 is enough for a hackathon; increase to 100 for better accuracy
    imgsz=640,
    batch=16,            # Reduce to 8 if Colab runs out of VRAM
    patience=15,         # Early stopping: stop if no improvement for 15 epochs
    device=0,            # GPU
    project="/content/vanrakshak_runs",
    name="forest_v1",
    pretrained=True,     # Use COCO pretrained weights as starting point
    optimizer="AdamW",
    lr0=0.001,
    lrf=0.01,
    mosaic=1.0,          # Data augmentation
    fliplr=0.5,
    degrees=45.0,        # Rotation augmentation for aerial views
    translate=0.1,
    scale=0.5,
    verbose=True,
)

print("Training complete!")
print(f"Best mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
```

> **Do NOT pass `flipud`.** It was removed in ultralytics >= 8.3 and will crash `train()`. Vertical-flip augmentation is covered by `degrees` rotation + `scale` for aerial imagery.

```python
# Cell 11 — Evaluate on validation set
metrics = model.val(data="/content/vanrakshak_forest/data.yaml")
print(f"mAP50:    {metrics.box.map50:.3f}")
print(f"mAP50-95: {metrics.box.map:.3f}")
print(f"Precision:{metrics.box.mp:.3f}")
print(f"Recall:   {metrics.box.mr:.3f}")
```

### Acceptance criteria

- Training completes without OOM errors
- `mAP50` >= 0.40 (acceptable for a small dataset hackathon fine-tune)
- Best weights saved at `/content/vanrakshak_runs/forest_v1/weights/best.pt`

### If training OOMs

Reduce `batch=8` and `imgsz=416`.

---

## Agent Task 4 — Export and download weights

**Scope:** Colab notebook — export
**Estimated time:** 5 minutes
**Dependencies:** Task 3

```python
# Cell 12 — Locate best weights
import os
best_pt = "/content/vanrakshak_runs/forest_v1/weights/best.pt"
print(f"Best weights: {os.path.getsize(best_pt) / 1e6:.1f} MB")

# Cell 13 — Export to ONNX for edge deployment (optional but recommended)
model_best = YOLO(best_pt)
model_best.export(format="onnx", dynamic=True, simplify=True)  # needs onnxsim (installed in Task 1)
print("ONNX export complete")

# Cell 14 — Download to local machine
from google.colab import files
files.download(best_pt)
files.download(best_pt.replace(".pt", ".onnx"))

# Cell 15 — Also save the class map for reference
import json
with open("/content/vanrakshak_class_map.json", "w") as f:
    json.dump(CLASS_MAP, f, indent=2)
files.download("/content/vanrakshak_class_map.json")
```

### Acceptance criteria

- `best.pt` downloaded locally (size should be ~6–7 MB for yolov8n)
- `best.onnx` downloaded (for edge/Jetson deployment)
- `vanrakshak_class_map.json` downloaded

---

## Agent Task 5 — Integrate fine-tuned weights into VanRakshak

**Scope:** `backend/` directory — local machine
**Estimated time:** 15 minutes
**Dependencies:** Task 4 (weights downloaded)

### Step 1 — Copy the weights into the backend

```bash
cp ~/Downloads/best.pt vanrakshak/backend/vanrakshak-forest-v1.pt
cp ~/Downloads/best.onnx vanrakshak/backend/vanrakshak-forest-v1.onnx
cp ~/Downloads/vanrakshak_class_map.json vanrakshak/backend/
```

### Step 2 — Update `backend/app/weights.py` registry

Add a local-only entry to `DEFAULT_WEIGHTS_URLS` and relax the type annotation (the dict currently types values as `str`, which cannot hold `None`):

```python
DEFAULT_WEIGHTS_URLS: dict[str, str | None] = {
    "rtdetr-l.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/rtdetr-l.pt",
    "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
    "vanrakshak-forest-v1.pt": None,  # local only — no remote URL
}
```

In `ensure_model_weights`, change the URL guard so a local-only model fails with a clear message instead of a generic ValueError. Replace:

```python
url = custom_url or DEFAULT_WEIGHTS_URLS.get(filename)
if not url or not (url.startswith("https://github.com/") or url.startswith("https://huggingface.co/")):
    raise ValueError("model URL must use an approved HTTPS host")
```

with:

```python
url = custom_url or DEFAULT_WEIGHTS_URLS.get(filename)
if url is None:
    raise FileNotFoundError(f"Local-only model '{filename}' not found at {file_path}")
if not (url.startswith("https://github.com/") or url.startswith("https://huggingface.co/")):
    raise ValueError("model URL must use an approved HTTPS host")
```

### Step 3 — Add model selection to `backend/app/config.py`

In the `Settings` class, add:

```python
detection_model: str = "yolov8n.pt"  # set to "vanrakshak-forest-v1.pt" for the fine-tuned model
```

### Step 4 — Config-driven model + robust path resolution in `backend/app/video.py`

Change the `process_video` signature from `model_name: str = "yolov8n.pt"` to:

```python
def process_video(payload: bytes, sample_every_n_frames: int = 2, model_name: str | None = None, tracker_name: str = "bytetrack.yaml", confidence_threshold: float = 0.35, on_sample: ... = None) -> VideoDetectionResponse:
```At the top of the `try:` block (after the imports), resolve the model name — first from config, then to a real file path so it works regardless of the process working directory (`Path` is already imported at the top of `video.py`):

```python
from .config import get_settings

if model_name is None:
    model_name = get_settings().detection_model


def _resolve_model_path(name: str) -> str:
    candidates = [
        Path(name),                                    # cwd-relative (backend/ when run normally)
        Path(__file__).resolve().parent.parent / name, # backend/<name>
    ]
    from .weights import get_weights_dir
    candidates.append(get_weights_dir() / name)        # MODEL_CACHE_DIR (default ./weights)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return name  # ultralytics builtin / auto-download
```

Then change the model-loading line from:

```python
model = RTDETR(model_name) if model_name.lower().startswith("rtdetr") else YOLO(model_name)
```

to:

```python
# The rtdetr check must use the ORIGINAL model name, not the resolved path:
# an absolute path never startswith "rtdetr", which would silently load
# RT-DETR weights through YOLO() instead of RTDETR().
is_rtdetr = model_name.lower().startswith("rtdetr")
model_path = _resolve_model_path(model_name)
model = RTDETR(model_path) if is_rtdetr else YOLO(model_path)
```

### Step 5 — Update `backend/app/policies.py` for the new classes

Extend `WildlifeProximityPolicy.evaluate` (line ~30) so the fine-tuned model's extra wildlife classes are recognized:

```python
if data.get("class_name") not in {"elephant", "wildlife", "animal", "deer", "horse"}:
```

> **Expected behavior change:** the demo clip `04_wildlife_elephants_monitoring.mp4` already contains `horse` detections — horses will now trigger `WILDLIFE_ALERT` + `DISPATCH_RANGER`. This is intended (documented demo behavior change).

Add a new `ForestFirePolicy` class:

```python
class ForestFirePolicy(Policy):
    policy_id = "forest_fire"

    def evaluate(self, data: dict[str, Any]) -> list[PolicyDecision]:
        if data.get("class_name") not in {"fire", "smoke", "wildfire"}:
            return []
        return [PolicyDecision(
            policy_id=self.policy_id,
            decision="RECOMMEND_ALERT",
            severity="CRITICAL",
            track_id=data.get("track_id"),
            confidence=float(data.get("confidence", 0)),
            evidence_refs=data.get("evidence_refs", []),
            recommended_actions=["ALERT_BEACON_ON", "DISPATCH_RANGER"],
        )]
```

Register it in `PolicyEngine.__init__`:

```python
self.policies = policies or [
    HumanIntrusionPolicy(),
    VehicleIntrusionPolicy(),
    WildlifeProximityPolicy(),
    RailwayConflictPolicy(),
    ThermalFirePolicy(),
    ForestFirePolicy(),  # ← add this
]
```

> **Consistency:** `ThermalFirePolicy` still returns `UNSUPPORTED_INPUT` for `input_type == "thermal"`; the new fire policy only fires on RGB `fire`/`smoke`/`wildfire` class detections. `FIRE_SUPPRESSANT_DEPLOY` remains `UNAVAILABLE` (Phase 2) — the policy recommends beacon + ranger dispatch, not suppression.

### Acceptance criteria

- `cd backend && .venv/bin/python -c "from app.video import process_video; print('ok')"` prints `ok`
- `cd backend && .venv/bin/pytest -q` still passes (update any policy tests that asserted the old wildlife class set)
- With `detection_model=vanrakshak-forest-v1.pt` set, `process_video` loads the fine-tuned weights (see Task 7 for the full API check)

---

## Agent Task 6 — Model registry docs + gitignore verification

**Scope:** `.gitignore` (verify only), `backend/README_MODELS.md` (new file)
**Estimated time:** 5 minutes
**Dependencies:** Task 5

### Instructions

**Step 1 — Verify gitignore (no changes needed).** The repo `.gitignore` already contains `*.pt`, `*.onnx`, and `weights/` — the fine-tuned weights are already excluded. Confirm with:

```bash
cd vanrakshak && git status --porcelain | grep -E "vanrakshak-forest" || echo "weights are untracked (OK)"
```

If that prints anything other than the echo message, add the two filenames to `.gitignore`.

**Step 2 — Create `backend/README_MODELS.md`:**

```markdown
# VanRakshak Model Registry

## vanrakshak-forest-v1.pt
- Base: YOLOv8n pretrained on COCO
- Fine-tuned on: Combined forest surveillance datasets (Roboflow)
- Classes: [list from vanrakshak_class_map.json]
- Training: 50 epochs, imgsz=640, AdamW
- mAP50: [fill after training]
- Use: Primary detection model in production

## yolov8n.pt
- Base: YOLOv8n pretrained on COCO (80 classes)
- Use: Fallback / development / CI (no custom weights needed)

## rtdetr-l.pt
- Base: RT-DETR large
- Use: High-accuracy benchmark mode
```

### Acceptance criteria

- `git status --porcelain` shows the weights as untracked (or the `.gitignore` addition was made and confirmed)
- `README_MODELS.md` documents training provenance for judges

---

## Agent Task 7 — End-to-end validation (final gate)

**Scope:** local verification against the real pipeline; no code changes unless a fix is required
**Estimated time:** 15 minutes
**Dependencies:** Tasks 5–6

### Step 1 — Direct pipeline check with the fine-tuned model

```bash
cd vanrakshak/backend && .venv/bin/python - <<'PY'
from pathlib import Path
from app.video import process_video

clip = Path("../demo_videos/04_wildlife_elephants_monitoring.mp4").read_bytes()

generic = process_video(clip, model_name="yolov8n.pt")
forest = process_video(clip, model_name="vanrakshak-forest-v1.pt")

from collections import Counter
g = Counter(d["class"] for f in generic.frames for d in f.detections)
f = Counter(d["class"] for f in forest.frames for d in f.detections)
print("generic classes:", dict(g))
print("forest classes:  ", dict(f))
print("DETECTION-COUNT-COMPARISON generic:", sum(g.values()), "| forest:", sum(f.values()))
PY
```

The counts are detection counts, not mAP — use them only for the judge comparison. Record both outputs.

### Step 2 — Full API check with the fine-tuned model

```bash
cd vanrakshak/backend
# temporarily point the backend at the fine-tuned model (leading newline in
# case .env does not end with one)
echo -e "\nDETECTION_MODEL=vanrakshak-forest-v1.pt" >> .env
.venv/bin/python -m uvicorn app.main:app --port 8002 &
BACKEND_PID=$!
sleep 4
curl -s -X POST http://127.0.0.1:8002/detect/video -F "file=@../demo_videos/04_wildlife_elephants_monitoring.mp4" \
  | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print('source:', d['source'], '| frames:', len(d['frames']))"
kill "$BACKEND_PID"
# revert
sed -i '/DETECTION_MODEL=vanrakshak-forest-v1.pt/d' .env
```

### Step 3 — Full suites

```bash
cd vanrakshak/backend && .venv/bin/pytest -q
cd vanrakshak/frontend && npm test && npm run typecheck && npm run build
```

### Step 4 — Benchmark comparison for judges

```bash
cd vanrakshak && bash scripts/run_evals.sh   # repo-root script; must complete successfully
```

### Definition of Done (greenlight)

- Custom-class detections (`fire`/`smoke`/`chainsaw`/etc., or an improved aerial-person/elevated recall on the elephant clip) are visible in the Step 1 comparison
- Step 2 API check returns `source: YOLO` with detections while the fine-tuned model is configured
- Full backend + frontend suites pass (Step 3)
- `run_evals.sh` completes with all four benchmark videos (Step 4)
- `README_MODELS.md` is filled in with the real mAP50 and class list

---

## SIH judge talking points

1. **"We trained our own model"** — fine-tuned on forest surveillance data, not just generic COCO
2. **"Aerial viewpoint optimized"** — used rotation/scale augmentations specifically for drone-angle imagery
3. **"New threat classes"** — chainsaw operators, campfire/smoke not detectable by stock YOLOv8
4. **"Quantified improvement"** — show the detection-count comparison table between generic and fine-tuned

---

## Known limitations

- Small dataset (< 2000 images) means accuracy won't match production models
- Roboflow free tier has download limits — use one Roboflow account per person if needed
- Fine-tuned model will degrade on classes not in training data (e.g., very rare animal species)
- ONNX export must be re-done on the target hardware (Jetson) for TensorRT optimization
- Detection counts in the benchmark comparison are not mAP — the model card (`README_MODELS.md`) should carry the real validation mAP50 from Task 3
