import torch
from torch.utils.data import Dataset, DataLoader
from transformers import DebertaV2Tokenizer, DebertaV2ForSequenceClassification
from transformers import AdamW, get_linear_schedule_with_warmup
from tqdm.auto import tqdm
import pandas as pd
from sklearn.model_selection import train_test_split
import numpy as np

CONFIG = {
    "model_name": "microsoft/deberta-v3-small",
    "max_length": 512,
    "batch_size": 32,
    "gradient_accumulation_steps": 2,
    "learning_rate": 5e-5,
    "epochs": 3,
    "warmup_ratio": 0.05,
    "mixed_precision": True,
    "device": "cuda" if torch.cuda.is_available() else "cpu",
}

class NewsDataset(Dataset):
    def __init__(self, texts, labels, tokenizer):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.encodings = tokenizer(
            texts,
            max_length=CONFIG["max_length"],
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        return {
            "input_ids": self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


def load_data():
    real = pd.read_csv(
        "fake-news-detector-files/True.csv", usecols=["title", "text"]
    ).sample(20000)
    fake = pd.read_csv(
        "fake-news-detector-files/Fake.csv", usecols=["title", "text"]
    ).sample(20000)

    real["label"] = 1
    fake["label"] = 0

    df = pd.concat([real, fake])
    df["text"] = df["title"] + " " + df["text"]

    return train_test_split(df["text"], df["label"], test_size=0.1, random_state=42)


def train():
    model = DebertaV2ForSequenceClassification.from_pretrained(
        CONFIG["model_name"],
        num_labels=2,
    ).to(CONFIG["device"])

    tokenizer = DebertaV2Tokenizer.from_pretrained(CONFIG["model_name"])

    X_train, X_test, y_train, y_test = load_data()

    train_dataset = NewsDataset(X_train.tolist(), y_train.tolist(), tokenizer)
    test_dataset = NewsDataset(X_test.tolist(), y_test.tolist(), tokenizer)

    train_loader = DataLoader(
        train_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=True,
        pin_memory=True,
        num_workers=4,
        persistent_workers=True,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=CONFIG["batch_size"] * 2,
        pin_memory=True,
        num_workers=4,
    )

    optimizer = AdamW(model.parameters(), lr=CONFIG["learning_rate"])

    total_steps = len(train_loader) * CONFIG["epochs"]
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * CONFIG["warmup_ratio"]),
        num_training_steps=total_steps,
    )

    scaler = torch.amp.GradScaler(enabled=CONFIG["mixed_precision"])

    for epoch in range(CONFIG["epochs"]):
        model.train()
        torch.cuda.empty_cache()

        progress_bar = tqdm(
            train_loader, desc=f"Epoch {epoch+1}", leave=False, dynamic_ncols=True
        )

        for step, batch in enumerate(progress_bar):
            inputs = {
                k: v.to(CONFIG["device"], non_blocking=True) for k, v in batch.items()
            }

            with torch.amp.autocast(
                device_type="cuda", enabled=CONFIG["mixed_precision"]
            ):
                outputs = model(**inputs)
                loss = outputs.loss / CONFIG["gradient_accumulation_steps"]

            scaler.scale(loss).backward()

            if (step + 1) % CONFIG["gradient_accumulation_steps"] == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                scheduler.step()

            progress_bar.set_postfix(
                {
                    "loss": f"{loss.item()*CONFIG['gradient_accumulation_steps']:.3f}",
                    "lr": f"{scheduler.get_last_lr()[0]:.1e}",
                    "mem": f"{torch.cuda.memory_allocated()/1e9:.1f}GB",
                }
            )

        model.eval()
        correct = 0
        total = 0

        with torch.inference_mode():
            for batch in tqdm(test_loader, desc="Validating", leave=False):
                inputs = {
                    k: v.to(CONFIG["device"], non_blocking=True)
                    for k, v in batch.items()
                }
                outputs = model(**inputs)
                correct += (outputs.logits.argmax(-1) == inputs["labels"]).sum().item()
                total += inputs["labels"].size(0)

        print(f"\nEpoch {epoch+1} | Accuracy: {correct/total:.2%}\n")
    torch.save(model.state_dict(), "fake_news_detector.pth")


if __name__ == "__main__":
    train()
