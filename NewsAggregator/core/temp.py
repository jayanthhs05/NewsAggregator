from huggingface_hub import snapshot_download
from transformers import AutoTokenizer, AutoModelForSequenceClassification


MODEL_NAME = "microsoft/deberta-v3-small"
SAVE_PATH = "core/ml_models/f"


snapshot_download(
    repo_id=MODEL_NAME,
    local_dir=SAVE_PATH,
    local_dir_use_symlinks=False,
    ignore_patterns=["*.msgpack", "*.h5", "*.tflite"],
)


print(f"Model saved to: {SAVE_PATH}")
