#!/usr/bin/env python3
"""Dataset Merger for VanRakshak Forest Drone AI.

Unifies and remaps downloaded domain datasets into a single 6-class YOLO training package:
  0: person (aerial & thermal poachers/trespassers)
  1: vehicle (cars, vans, motors)
  2: timber_truck (trucks, heavy transport)
  3: fire (wildfire flames)
  4: smoke (smoke plumes)
  5: elephant (wildlife)
"""

from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
DATASETS_DIR = ROOT_DIR / "datasets"
OUTPUT_DIR = DATASETS_DIR / "forest_merged"

UNIFIED_NAMES = [
    "person",        # 0
    "vehicle",       # 1
    "timber_truck",  # 2
    "fire",          # 3
    "smoke",         # 4
    "elephant",      # 5
]


def setup_output_dirs() -> None:
    """Create clean destination folder structure."""
    print(f"[1/5] Setting up target directory: {OUTPUT_DIR}")
    for split in ["train", "val", "test"]:
        (OUTPUT_DIR / split / "images").mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / split / "labels").mkdir(parents=True, exist_ok=True)


def merge_thermal_hit_uav(max_samples_per_split: int = 1500) -> None:
    """Merge HIT-UAV thermal human dataset (class 0 -> person)."""
    src = DATASETS_DIR / "thermal_human_hit_uav"
    if not src.exists():
        print("  - Skipping thermal_human_hit_uav (not found)")
        return
    print(f"[2/5] Merging thermal human dataset from {src.name}...")
    
    # Check splits
    for split, target_split in [("train", "train"), ("test", "val"), ("valid", "val")]:
        img_dir = src / split / "images"
        lbl_dir = src / split / "labels"
        if not img_dir.exists():
            continue
        
        copied = 0
        for img in img_dir.glob("*.jpg"):
            if copied >= max_samples_per_split:
                break
            lbl = lbl_dir / f"{img.stem}.txt"
            if not lbl.exists():
                continue
            
            # Remap: class 0 remains class 0 (person)
            dst_img = OUTPUT_DIR / target_split / "images" / f"thermal_{img.name}"
            dst_lbl = OUTPUT_DIR / target_split / "labels" / f"thermal_{lbl.name}"
            
            shutil.copy2(img, dst_img)
            # Ensure label class is 0
            lines = []
            for line in lbl.read_text().splitlines():
                parts = line.strip().split()
                if parts:
                    lines.append(f"0 {' '.join(parts[1:])}")
            dst_lbl.write_text("\n".join(lines))
            copied += 1
        print(f"  -> Copied {copied} thermal human images to {target_split}")


def merge_visdrone(max_samples_per_split: int = 2500) -> None:
    """Merge VisDrone aerial dataset:
      0, 1 -> 0 (person)
      2, 3, 4, 9 -> 1 (vehicle)
      5, 8 -> 2 (timber_truck)
    """
    src = DATASETS_DIR / "visdrone_official"
    if not src.exists():
        src = Path("/home/sanjeev/Documents/clg/datasets/VisDrone")
    if not src.exists():
        print("  - Skipping VisDrone (not found)")
        return
    print(f"[3/5] Merging aerial vehicles, trucks, and persons from VisDrone...")
    
    visdrone_map = {
        0: 0,  # pedestrian -> person
        1: 0,  # people -> person
        2: 1,  # bicycle -> vehicle
        3: 1,  # car -> vehicle
        4: 1,  # van -> vehicle
        9: 1,  # motor -> vehicle
        5: 2,  # truck -> timber_truck
        8: 2,  # bus -> timber_truck
    }
    
    for split in ["train", "val", "test"]:
        target_split = "val" if split == "test" else split
        img_dir = src / "images" / split
        lbl_dir = src / "labels" / split
        if not img_dir.exists():
            continue
            
        copied = 0
        for img in img_dir.glob("*.jpg"):
            if copied >= max_samples_per_split:
                break
            lbl = lbl_dir / f"{img.stem}.txt"
            if not lbl.exists():
                continue
            
            remapped_lines = []
            for line in lbl.read_text().splitlines():
                parts = line.strip().split()
                if not parts:
                    continue
                old_id = int(parts[0])
                if old_id in visdrone_map:
                    new_id = visdrone_map[old_id]
                    remapped_lines.append(f"{new_id} {' '.join(parts[1:])}")
            
            if remapped_lines:
                dst_img = OUTPUT_DIR / target_split / "images" / f"visdrone_{img.name}"
                dst_lbl = OUTPUT_DIR / target_split / "labels" / f"visdrone_{lbl.name}"
                shutil.copy2(img, dst_img)
                dst_lbl.write_text("\n".join(remapped_lines))
                copied += 1
        print(f"  -> Copied {copied} VisDrone aerial images to {target_split}")


def merge_forest_fire(max_samples: int = 1500) -> None:
    """Extract and merge forest fire and smoke dataset."""
    src = DATASETS_DIR / "forest_fire_drone"
    if not src.exists():
        print("  - Skipping forest fire (not found)")
        return
    print(f"[4/5] Extracting and merging forest wildfire and smoke plumes...")
    
    # Process train.zip and val.zip
    for z_name, target_split in [("train.zip", "train"), ("val.zip", "val")]:
        z_path = src / z_name
        if not z_path.exists():
            continue
        print(f"  -> Reading {z_name}...")
        copied = 0
        with zipfile.ZipFile(z_path, "r") as z:
            namelist = set(z.namelist())
            for name in list(namelist):
                if copied >= max_samples:
                    break
                if name.endswith((".jpg", ".png")) and "images/" in name:
                    lbl_name = name.replace("images/", "labels/").rsplit(".", 1)[0] + ".txt"
                    
                    dst_img = OUTPUT_DIR / target_split / "images" / f"fire_{Path(name).name}"
                    dst_lbl = OUTPUT_DIR / target_split / "labels" / f"fire_{Path(lbl_name).name}"
                    
                    # Extract image
                    img_data = z.read(name)
                    dst_img.write_bytes(img_data)
                    
                    # Remap or generate label (0: fire -> 3, 1: smoke -> 4)
                    if lbl_name in namelist:
                        lbl_data = z.read(lbl_name).decode("utf-8")
                        lines = []
                        for line in lbl_data.splitlines():
                            parts = line.strip().split()
                            if parts:
                                cls_id = int(parts[0])
                                new_cls = 3 if cls_id == 0 else 4
                                lines.append(f"{new_cls} {' '.join(parts[1:])}")
                        dst_lbl.write_text("\n".join(lines))
                    else:
                        # Default full-frame fire label if plain frame
                        dst_lbl.write_text("3 0.5 0.5 0.8 0.8\n")
                    copied += 1
        print(f"  -> Extracted {copied} fire/smoke images to {target_split}")


def write_yaml() -> None:
    """Generate the unified data.yaml file."""
    print("[5/5] Writing unified data.yaml configuration...")
    cfg = {
        "path": str(OUTPUT_DIR.resolve()),
        "train": "train/images",
        "val": "val/images",
        "test": "val/images",
        "nc": len(UNIFIED_NAMES),
        "names": UNIFIED_NAMES,
    }
    yaml_path = OUTPUT_DIR / "data.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)
    print(f"  -> Successfully generated: {yaml_path}")


def main() -> None:
    print("=" * 60)
    print("🌲 VanRakshak Dataset Merger: Building Unified Forest AI Dataset")
    print("=" * 60)
    setup_output_dirs()
    merge_thermal_hit_uav()
    merge_visdrone()
    merge_forest_fire()
    write_yaml()
    
    print("\n" + "=" * 60)
    print("🎉 Dataset Merge Complete!")
    print("=" * 60)
    for split in ["train", "val"]:
        n_img = len(list((OUTPUT_DIR / split / "images").glob("*")))
        n_lbl = len(list((OUTPUT_DIR / split / "labels").glob("*")))
        print(f"  • {split}: {n_img} images, {n_lbl} labels")
    print(f"  • data.yaml: {OUTPUT_DIR / 'data.yaml'}")
    print(f"  • Classes: {UNIFIED_NAMES}")


if __name__ == "__main__":
    main()
