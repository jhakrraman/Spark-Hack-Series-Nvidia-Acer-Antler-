"""
prepare_dataset.py — Convert raw frame annotations into Qwen-VL training JSONL.

Reads a directory of JPEG frames and a labels file (CSV or JSONL) and
produces the chat-formatted JSONL expected by train_qwen_vl.py.

Usage:
    python prepare_dataset.py \
        --frames-dir ./raw_frames \
        --labels ./labels.csv \
        --output ./train.jsonl \
        --val-split 0.1

The labels file can be either:
  - CSV with columns: frame_path, events_json
  - JSONL with keys:   frame_path, events (list of {timestamp, description, isDangerous})

If --from-bounding-boxes is set, the script instead reads the Person of
Interest bounding-box JSON format (public/bounding_boxes/*_boxes.json)
and converts each annotated frame into a training row.
"""

import argparse
import csv
import json
import os
import random
from pathlib import Path
from typing import Any


SYSTEM_PROMPT = (
    "Analyze this NYC traffic camera frame. Identify any hazards, "
    "incidents, or notable activity. Return JSON with an events array."
)


def build_message(image_path: str, events: list[dict[str, Any]]) -> dict:
    return {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": SYSTEM_PROMPT},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"events": events}, ensure_ascii=False),
                    }
                ],
            },
        ]
    }


def load_csv_labels(path: str) -> list[tuple[str, list[dict]]]:
    rows: list[tuple[str, list[dict]]] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events = json.loads(row["events_json"])
            rows.append((row["frame_path"], events))
    return rows


def load_jsonl_labels(path: str) -> list[tuple[str, list[dict]]]:
    rows: list[tuple[str, list[dict]]] = []
    with open(path) as f:
        for line in f:
            obj = json.loads(line.strip())
            rows.append((obj["frame_path"], obj["events"]))
    return rows


def load_bounding_boxes(boxes_dir: str, frames_dir: str) -> list[tuple[str, list[dict]]]:
    """Convert bounding-box JSON files into (frame_path, events) pairs."""
    rows: list[tuple[str, list[dict]]] = []
    boxes_path = Path(boxes_dir)
    for json_file in sorted(boxes_path.glob("*_boxes.json")):
        video_name = json_file.stem.replace("_boxes", "")
        with open(json_file) as f:
            data = json.load(f)

        frames = data if isinstance(data, list) else data.get("frames", [])
        for i, frame_info in enumerate(frames):
            frame_file = f"{video_name}_frame_{i:04d}.jpg"
            frame_path = os.path.join(frames_dir, frame_file)

            events: list[dict] = []
            boxes = frame_info if isinstance(frame_info, list) else frame_info.get("boxes", [])
            for box in boxes:
                label = box.get("label", "unknown object")
                is_dangerous = any(
                    kw in label.lower()
                    for kw in ["fight", "weapon", "fall", "assault", "rob", "steal", "fire"]
                )
                ts_min = i // 60
                ts_sec = i % 60
                events.append(
                    {
                        "timestamp": f"{ts_min:02d}:{ts_sec:02d}",
                        "description": label,
                        "isDangerous": is_dangerous,
                    }
                )

            if events:
                rows.append((frame_path, events))

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Qwen-VL fine-tuning dataset")
    parser.add_argument("--frames-dir", type=str, default="./raw_frames")
    parser.add_argument("--labels", type=str, default=None, help="CSV or JSONL labels file")
    parser.add_argument("--from-bounding-boxes", type=str, default=None,
                        help="Path to bounding_boxes/ dir (alternative to --labels)")
    parser.add_argument("--output", type=str, default="./train.jsonl")
    parser.add_argument("--val-output", type=str, default=None,
                        help="Validation split output path (default: <output>_val.jsonl)")
    parser.add_argument("--val-split", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.from_bounding_boxes:
        rows = load_bounding_boxes(args.from_bounding_boxes, args.frames_dir)
    elif args.labels:
        if args.labels.endswith(".csv"):
            rows = load_csv_labels(args.labels)
        else:
            rows = load_jsonl_labels(args.labels)
    else:
        parser.error("Provide either --labels or --from-bounding-boxes")

    random.seed(args.seed)
    random.shuffle(rows)

    split_idx = int(len(rows) * (1 - args.val_split))
    train_rows = rows[:split_idx]
    val_rows = rows[split_idx:]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for frame_path, events in train_rows:
            msg = build_message(frame_path, events)
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    val_path = args.val_output or str(output_path).replace(".jsonl", "_val.jsonl")
    with open(val_path, "w") as f:
        for frame_path, events in val_rows:
            msg = build_message(frame_path, events)
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    print(f"Wrote {len(train_rows)} training rows to {output_path}")
    print(f"Wrote {len(val_rows)} validation rows to {val_path}")


if __name__ == "__main__":
    main()
