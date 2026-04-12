# Fine-tuning Qwen-VL for POI frame detection

QLoRA fine-tuning pipeline that adapts Qwen2.5-VL or Qwen3-VL to the
Person of Interest detection schema. The trained adapter drops into the
existing NIM / LM Studio inference path with zero schema changes.

## Quick start

```bash
cd poi-brain/finetune
pip install -r requirements.txt

# 1. Prepare training data from existing bounding-box annotations
python prepare_dataset.py \
    --from-bounding-boxes ../../public/bounding_boxes \
    --frames-dir ./raw_frames \
    --output ./train.jsonl

# 2. Fine-tune (7B model, QLoRA 4-bit, fits in 24 GB VRAM)
python train_qwen_vl.py \
    --model-name Qwen/Qwen2.5-VL-7B-Instruct \
    --dataset ./train.jsonl \
    --output-dir ./adapter_out \
    --epochs 3 \
    --lora-rank 64

# 3. Merge adapter into base model for deployment
python train_qwen_vl.py \
    --model-name Qwen/Qwen2.5-VL-7B-Instruct \
    --output-dir ./adapter_out \
    --merge-and-save ./merged_model
```

## Supported models

| Model | VRAM (QLoRA 4-bit) | Notes |
|---|---|---|
| `Qwen/Qwen2.5-VL-7B-Instruct` | ~24 GB | Default, fast iteration |
| `Qwen/Qwen2.5-VL-72B-Instruct` | ~80 GB | Best quality, needs DGX Spark |
| `Qwen/Qwen3-VL-32B-Instruct` | ~40 GB | Strong middle ground |
| `Qwen/Qwen3-VL-8B-Instruct` | ~20 GB | Lightweight, good for testing |

## Data format

Each line of the JSONL file follows the Qwen-VL chat format:

```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "image", "image": "path/to/frame.jpg"},
        {"type": "text", "text": "Analyze this NYC traffic camera frame..."}
      ]
    },
    {
      "role": "assistant",
      "content": [
        {"type": "text", "text": "{\"events\": [{\"timestamp\": \"00:42\", \"description\": \"...\", \"isDangerous\": true}]}"}
      ]
    }
  ]
}
```

The assistant response is the same `FrameEvent` JSON schema used by
`poi-brain` and the Next.js frontend, so a fine-tuned model is a
drop-in replacement.

## Preparing data from existing annotations

The `prepare_dataset.py` script supports two input formats:

1. **CSV labels**: `frame_path,events_json` columns
2. **Bounding-box JSON**: The `public/bounding_boxes/*_boxes.json` format
   already in the repo — converts box coordinates and video-category
   labels into natural-language event descriptions

## Training arguments

| Arg | Default | Notes |
|---|---|---|
| `--model-name` | `Qwen/Qwen2.5-VL-7B-Instruct` | Any Qwen-VL HuggingFace ID |
| `--quantization` | `4bit` | `4bit` / `8bit` / `none` |
| `--lora-rank` | `64` | Higher = more capacity, more VRAM |
| `--lora-alpha` | `128` | Typically 2× rank |
| `--lora-target-modules` | `q_proj,k_proj,v_proj,o_proj` | Language model attention layers |
| `--epochs` | `3` | 1-5 is typical for fine-tuning |
| `--batch-size` | `1` | VLMs are memory-heavy; use gradient accumulation |
| `--gradient-accumulation-steps` | `8` | Effective batch = batch_size × this |
| `--learning-rate` | `2e-5` | Standard for LoRA fine-tuning |
| `--wandb-project` | none | Set to enable W&B experiment tracking |
| `--merge-and-save` | none | Merge adapter into base and save full model |

## Device support

The script auto-detects the best available accelerator:

| Device | Quantization | Notes |
|---|---|---|
| **CUDA** (DGX Spark, RTX) | 4-bit, 8-bit, none | Full QLoRA support |
| **MPS** (Apple Silicon) | none only | BitsAndBytes not available on MPS; uses fp32 |
| **CPU** | none only | Very slow, only for smoke-testing |

## After training

Load the fine-tuned adapter in LM Studio by pointing at the merged
model directory, or serve it via vLLM / SGLang / NIM with the adapter
path. The detection schema is identical to the base model — no
frontend or backend changes required.
