import torch
from transformers import DebertaV2Tokenizer, DebertaV2ForSequenceClassification


def predict_fake_news(text, model_path="fake_news_detector.pth"):

    if not hasattr(predict_fake_news, "model"):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        predict_fake_news.model = DebertaV2ForSequenceClassification.from_pretrained(
            "microsoft/deberta-v3-small", num_labels=2
        )

        state_dict = torch.load(model_path, map_location=device)
        predict_fake_news.model.load_state_dict(state_dict)
        predict_fake_news.model.to(device)
        predict_fake_news.model.eval()

        predict_fake_news.tokenizer = DebertaV2Tokenizer.from_pretrained(
            "microsoft/deberta-v3-small"
        )
        predict_fake_news.device = device

    combined_text = text.strip()

    inputs = predict_fake_news.tokenizer(
        combined_text,
        max_length=512,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    ).to(predict_fake_news.device)

    with torch.no_grad(), torch.amp.autocast(device_type="cuda"):
        outputs = predict_fake_news.model(**inputs)
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)

    fake_score = probabilities[0, 1].item()
    is_fake = fake_score > 0.5

    del inputs, outputs, logits, probabilities
    torch.cuda.empty_cache()

    return is_fake, fake_score
