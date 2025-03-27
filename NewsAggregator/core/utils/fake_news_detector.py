import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
from transformers import DebertaV2Tokenizer, DebertaV2ForSequenceClassification
from pathlib import Path
from django.conf import settings

MODEL_DIR = Path(settings.BASE_DIR) / "core/ml_models/fake_news_detector"


def detect_fake_news(text, model_dir=MODEL_DIR):
    if not hasattr(detect_fake_news, "model"):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        required_files = {
            "config.json": "Model configuration",
            "pytorch_model.bin": "Model weights",
            "tokenizer_config.json": "Tokenizer settings",
        }

        for f in required_files:
            if not (model_dir / f).exists():
                raise FileNotFoundError(f"Missing required file: {model_dir/f}")

        detect_fake_news.model = DebertaV2ForSequenceClassification.from_pretrained(
            model_dir, local_files_only=True, num_labels=2
        )

        detect_fake_news.tokenizer = DebertaV2Tokenizer.from_pretrained(
            model_dir, local_files_only=True
        )

        detect_fake_news.model = detect_fake_news.model.to(device).eval()
        torch.cuda.empty_cache() if device.type == "cuda" else None

    inputs = detect_fake_news.tokenizer(
        text.strip(),
        max_length=512,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    ).to(detect_fake_news.model.device)

    with torch.no_grad(), torch.amp.autocast(
        device_type="cuda" if detect_fake_news.model.device.type == "cuda" else "cpu",
        enabled=detect_fake_news.model.device.type == "cuda",
    ):
        outputs = detect_fake_news.model(**inputs)
        probabilities = torch.softmax(outputs.logits, dim=1)

    fake_score = probabilities[0, 1].item() * 100
    is_fake = fake_score > 50

    del inputs, outputs, probabilities
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return is_fake, fake_score