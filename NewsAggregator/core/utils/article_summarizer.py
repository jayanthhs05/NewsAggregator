import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import os
from pathlib import Path
from django.conf import settings


os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["CUDA_VISIBLE_DEVICES"] = "0" if torch.cuda.is_available() else ""

CACHE_DIR = Path(settings.BASE_DIR) / "core/ml_models/summarizer/"
os.makedirs(CACHE_DIR, exist_ok=True)


def initialize_summarizer():
    model_path = CACHE_DIR / "sshleifer_distilbart-cnn-12-6"

    if not model_path.exists():
        print("Downloading and caching model...")
        tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
        model = AutoModelForSeq2SeqLM.from_pretrained(
            "sshleifer/distilbart-cnn-12-6",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        )
        model.save_pretrained(model_path)
        tokenizer.save_pretrained(model_path)

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model_path = CACHE_DIR / "sshleifer_distilbart-cnn-12-6"

    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_path,
        device_map="auto" if torch.cuda.is_available() else None,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )

    return pipeline(
        "summarization",
        model=model,
        tokenizer=tokenizer,
        framework="pt",
        torch_dtype=torch.float16,
        batch_size=1,
    )


def summarize_article(text, summarizer=None, max_length=130, min_length=30):
    if not summarizer:
        summarizer = initialize_summarizer()

    try:
        torch.cuda.empty_cache() if torch.cuda.is_available() else None

        max_chunk_length = 1024
        chunks = [
            text[i : i + max_chunk_length]
            for i in range(0, len(text), max_chunk_length)
        ]

        summaries = []
        for chunk in chunks:
            result = summarizer(
                chunk,
                max_length=max_length,
                min_length=min_length,
                do_sample=False,
                clean_up_tokenization_spaces=True,
                truncation=True,
            )
            summaries.append(result[0]["summary_text"])

            del chunk, result
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        return " ".join(summaries)

    except RuntimeError as e:

        if "CUDA out of memory" in str(e):
            print("Falling back to CPU due to memory constraints")
            summarizer.model = summarizer.model.cpu()
            return summarize_article(text, summarizer)
        raise


# summarize_article("In today’s fast-paced world, technology has become an integral part of our daily lives. From the moment we wake up to the moment we go to bed, we are surrounded by gadgets and devices that help us stay connected, entertained, and informed. Smartphones, laptops, and tablets have revolutionized the way we work, learn, and communicate. The internet has made it possible to access information from anywhere in the world, at any time. Social media platforms have connected people from different corners of the globe, enabling them to share their thoughts, experiences, and ideas in real-time. However, with all these advancements, there are also challenges. The overuse of technology has led to concerns about privacy, data security, and the impact of screen time on mental health. People are becoming more aware of the need to strike a balance between embracing technology and ensuring that it doesn’t negatively affect their well-being. Additionally, the rise of artificial intelligence and automation is changing the landscape of the job market, with some jobs becoming obsolete while new ones are being created. This has raised questions about the future of work and the skills required to thrive in an increasingly automated world. As we continue to advance, it is crucial to think about how we can harness the power of technology in a responsible and sustainable way that benefits society as a whole.")
