"""
train_qwen_vl.py — Fine-tune Qwen2.5-VL / Qwen3-VL on custom frame detection data.

Uses QLoRA (4-bit quantization + LoRA adapters) so the full training run fits
inside 24 GB VRAM for 7B models, or 80 GB for 72B models. Runs on CUDA, MPS
(Apple Silicon), or CPU — auto-detected at runtime.

Usage:
    python train_qwen_vl.py \
        --model-name Qwen/Qwen2.5-VL-7B-Instruct \
        --dataset ./train.jsonl \
        --output-dir ./adapter_out \
        --epochs 3 \
        --batch-size 1 \
        --lora-rank 64 \
        --quantization 4bit

After training, the adapter weights are saved to --output-dir. To merge them
into the base model for deployment:

    python train_qwen_vl.py \
        --model-name Qwen/Qwen2.5-VL-7B-Instruct \
        --output-dir ./adapter_out \
        --merge-and-save ./merged_model
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import torch
from datasets import Dataset
from PIL import Image
from peft import LoraConfig, TaskType, get_peft_model, PeftModel
from transformers import (
    AutoProcessor,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)

# -------------------------------------------------------------------------
# Device detection (mirrors poi-brain/app/pipeline/device_probe.py)
# -------------------------------------------------------------------------

def detect_device() -> str:
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        print(f"[device] CUDA detected: {name}")
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        print("[device] Apple MPS detected")
        return "mps"
    print("[device] Falling back to CPU")
    return "cpu"


# -------------------------------------------------------------------------
# Model loading
# -------------------------------------------------------------------------

def load_model_and_processor(
    model_name: str,
    quantization: str,
    device: str,
):
    """Load the base Qwen-VL model with optional quantization."""
    # Try to import the Qwen-VL specific class; fall back to AutoModel
    try:
        from transformers import Qwen2VLForConditionalGeneration
        model_cls = Qwen2VLForConditionalGeneration
    except ImportError:
        from transformers import AutoModelForVision2Seq
        model_cls = AutoModelForVision2Seq

    quant_config = None
    model_kwargs: dict[str, Any] = {
        "trust_remote_code": True,
    }

    if quantization == "4bit" and device == "cuda":
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        model_kwargs["quantization_config"] = quant_config
        model_kwargs["device_map"] = "auto"
    elif quantization == "8bit" and device == "cuda":
        quant_config = BitsAndBytesConfig(load_in_8bit=True)
        model_kwargs["quantization_config"] = quant_config
        model_kwargs["device_map"] = "auto"
    else:
        # No quantization — load in bf16 or fp32
        if device == "cuda":
            model_kwargs["torch_dtype"] = torch.bfloat16
            model_kwargs["device_map"] = "auto"
        elif device == "mps":
            model_kwargs["torch_dtype"] = torch.float32
        else:
            model_kwargs["torch_dtype"] = torch.float32

    print(f"[model] Loading {model_name} with quantization={quantization}")
    model = model_cls.from_pretrained(model_name, **model_kwargs)

    processor = AutoProcessor.from_pretrained(
        model_name,
        trust_remote_code=True,
    )

    # Ensure pad token is set
    if processor.tokenizer.pad_token is None:
        processor.tokenizer.pad_token = processor.tokenizer.eos_token

    return model, processor


# -------------------------------------------------------------------------
# LoRA setup
# -------------------------------------------------------------------------

def apply_lora(model, lora_rank: int, lora_alpha: int, target_modules: list[str]):
    """Wrap the model with LoRA adapters."""
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        target_modules=target_modules,
        bias="none",
    )

    model.enable_input_require_grads()
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model


# -------------------------------------------------------------------------
# Dataset
# -------------------------------------------------------------------------

def load_jsonl_dataset(path: str) -> Dataset:
    """Load a JSONL file where each line has a 'messages' key in Qwen-VL chat format."""
    rows: list[dict] = []
    with open(path) as f:
        for line in f:
            rows.append(json.loads(line.strip()))
    return Dataset.from_list(rows)


def make_collator(processor, max_image_tokens: int):
    """
    Build a data collator that processes Qwen-VL chat messages into
    model-ready tensors. Each sample has 'messages' with interleaved
    image and text content parts.
    """

    def collate_fn(batch: list[dict]) -> dict:
        texts: list[str] = []
        image_sets: list[list[Image.Image]] = []

        for sample in batch:
            messages = sample["messages"]
            # Apply the chat template to get the full text prompt
            text = processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
            texts.append(text)

            # Collect all images from the conversation
            images: list[Image.Image] = []
            for msg in messages:
                content = msg.get("content", [])
                if isinstance(content, str):
                    continue
                for part in content:
                    if part.get("type") == "image":
                        img_path = part["image"]
                        if os.path.exists(img_path):
                            images.append(Image.open(img_path).convert("RGB"))
                        else:
                            # Create a placeholder image for missing files
                            images.append(Image.new("RGB", (224, 224), (128, 128, 128)))
            image_sets.append(images)

        # Flatten images for processor
        all_images = [img for imgs in image_sets for img in imgs] if any(image_sets) else None

        # Process through the Qwen-VL processor
        inputs = processor(
            text=texts,
            images=all_images if all_images else None,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

        # For causal LM training, labels = input_ids with padding masked
        labels = inputs["input_ids"].clone()
        labels[labels == processor.tokenizer.pad_token_id] = -100
        inputs["labels"] = labels

        return inputs

    return collate_fn


# -------------------------------------------------------------------------
# Merge adapter into base model
# -------------------------------------------------------------------------

def merge_and_save(model_name: str, adapter_dir: str, output_dir: str):
    """Load the base model + LoRA adapter and save the merged model."""
    print(f"[merge] Loading base model {model_name}")
    try:
        from transformers import Qwen2VLForConditionalGeneration
        model_cls = Qwen2VLForConditionalGeneration
    except ImportError:
        from transformers import AutoModelForVision2Seq
        model_cls = AutoModelForVision2Seq

    base_model = model_cls.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    print(f"[merge] Loading adapter from {adapter_dir}")
    model = PeftModel.from_pretrained(base_model, adapter_dir)
    model = model.merge_and_unload()

    print(f"[merge] Saving merged model to {output_dir}")
    model.save_pretrained(output_dir)

    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    processor.save_pretrained(output_dir)

    print(f"[merge] Done. Model saved to {output_dir}")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune Qwen2.5-VL / Qwen3-VL on custom frame detection data"
    )

    # Model
    parser.add_argument("--model-name", type=str, default="Qwen/Qwen2.5-VL-7B-Instruct",
                        help="HuggingFace model ID (default: Qwen/Qwen2.5-VL-7B-Instruct)")
    parser.add_argument("--quantization", choices=["4bit", "8bit", "none"], default="4bit",
                        help="Quantization mode for QLoRA (default: 4bit)")

    # Data
    parser.add_argument("--dataset", type=str, default="./train.jsonl",
                        help="Path to training JSONL")
    parser.add_argument("--val-dataset", type=str, default=None,
                        help="Path to validation JSONL (optional)")
    parser.add_argument("--max-image-tokens", type=int, default=1280,
                        help="Max image tokens for Qwen-VL dynamic resolution")

    # LoRA
    parser.add_argument("--lora-rank", type=int, default=64)
    parser.add_argument("--lora-alpha", type=int, default=128)
    parser.add_argument("--lora-target-modules", type=str,
                        default="q_proj,k_proj,v_proj,o_proj",
                        help="Comma-separated list of target modules")

    # Training
    parser.add_argument("--output-dir", type=str, default="./adapter_out")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--save-steps", type=int, default=100)

    # Experiment tracking
    parser.add_argument("--wandb-project", type=str, default=None,
                        help="Weights & Biases project name (optional)")

    # Merge
    parser.add_argument("--merge-and-save", type=str, default=None,
                        help="If set, merge adapter into base model and save to this path")

    # Resume
    parser.add_argument("--resume-from-checkpoint", type=str, default=None)

    args = parser.parse_args()

    # Handle merge-only mode
    if args.merge_and_save:
        merge_and_save(args.model_name, args.output_dir, args.merge_and_save)
        return

    device = detect_device()

    # Quantization requires CUDA
    if args.quantization != "none" and device != "cuda":
        print(f"[warn] Quantization={args.quantization} requires CUDA; switching to none")
        args.quantization = "none"

    model, processor = load_model_and_processor(
        args.model_name,
        args.quantization,
        device,
    )

    target_modules = [m.strip() for m in args.lora_target_modules.split(",")]
    model = apply_lora(model, args.lora_rank, args.lora_alpha, target_modules)

    # Load datasets
    train_ds = load_jsonl_dataset(args.dataset)
    val_ds = load_jsonl_dataset(args.val_dataset) if args.val_dataset else None

    print(f"[data] Training samples: {len(train_ds)}")
    if val_ds:
        print(f"[data] Validation samples: {len(val_ds)}")

    # WandB setup
    report_to = "none"
    if args.wandb_project:
        os.environ["WANDB_PROJECT"] = args.wandb_project
        report_to = "wandb"

    # Compute dtype for training
    bf16 = device == "cuda" and torch.cuda.is_bf16_supported()
    fp16 = device == "cuda" and not bf16

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        max_grad_norm=args.max_grad_norm,
        bf16=bf16,
        fp16=fp16,
        gradient_checkpointing=True,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=3,
        report_to=report_to,
        remove_unused_columns=False,
        dataloader_pin_memory=False,
    )

    collator = make_collator(processor, args.max_image_tokens)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
    )

    print("[train] Starting training...")
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)

    print(f"[train] Saving adapter to {args.output_dir}")
    model.save_pretrained(args.output_dir)
    processor.save_pretrained(args.output_dir)

    print("[train] Done.")


if __name__ == "__main__":
    main()
