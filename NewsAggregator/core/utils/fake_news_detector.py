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

    fake_score = probabilities[0, 1].item()
    is_fake = fake_score > 0.5

    del inputs, outputs, probabilities
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return is_fake, fake_score


def lol():
    print(
        detect_fake_news(
            "In today’s fast-paced world, technology has become an integral part of our daily lives. From the moment we wake up to the moment we go to bed, we are surrounded by gadgets and devices that help us stay connected, entertained, and informed. Smartphones, laptops, and tablets have revolutionized the way we work, learn, and communicate. The internet has made it possible to access information from anywhere in the world, at any time. Social media platforms have connected people from different corners of the globe, enabling them to share their thoughts, experiences, and ideas in real-time. However, with all these advancements, there are also challenges. The overuse of technology has led to concerns about privacy, data security, and the impact of screen time on mental health. People are becoming more aware of the need to strike a balance between embracing technology and ensuring that it doesn’t negatively affect their well-being. Additionally, the rise of artificial intelligence and automation is changing the landscape of the job market, with some jobs becoming obsolete while new ones are being created. This has raised questions about the future of work and the skills required to thrive in an increasingly automated world. As we continue to advance, it is crucial to think about how we can harness the power of technology in a responsible and sustainable way that benefits society as a whole."
        )
    )
