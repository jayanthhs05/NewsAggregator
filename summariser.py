import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import os


CACHE_DIR = "./model_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def initialize_summarizer():
    model_path = os.path.join(CACHE_DIR, "sshleifer_distilbart-cnn-12-6")

    if not os.path.exists(model_path):
        print("Downloading model...")

        tokenizer = AutoTokenizer.from_pretrained(
            "sshleifer/distilbart-cnn-12-6", cache_dir=CACHE_DIR
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            "sshleifer/distilbart-cnn-12-6",
            cache_dir=CACHE_DIR,
            torch_dtype=torch.float16,
        )
        tokenizer.save_pretrained(model_path)
        model.save_pretrained(model_path)
        print("Model cached successfully")

    return pipeline(
        "summarization",
        model=model_path,
        device=0 if torch.cuda.is_available() else -1,
        torch_dtype=torch.float16,
        truncation=True,
    )


def summarize_text(text, summarizer, max_length=130, min_length=30):
    return summarizer(
        text,
        max_length=max_length,
        min_length=min_length,
        do_sample=False,
        clean_up_tokenization_spaces=True,
    )[0]["summary_text"]