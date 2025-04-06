import os
import requests
from transformers import AutoModel, AutoTokenizer

def download_huggingface_model(model_name, cache_dir):
    print(f"Checking for model: {model_name} in {cache_dir}")

    # Downloading model and tokenizer
    model = AutoModel.from_pretrained(model_name, cache_dir=cache_dir)
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
    print(f"Model and tokenizer for {model_name} are ready.")

def download_file(url, destination_file):
    """Helper function to download a file from a URL to a destination."""
    response = requests.get(url, stream=True)
    with open(destination_file, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded {url} as {destination_file}")

def download_fasttext_model(url, cache_dir):
    """Download FastText models."""
    model_filename = os.path.join(cache_dir, "lid.176.bin")
    if not os.path.isfile(model_filename):
        print(f"Downloading FastText model to {cache_dir}")
        download_file(url, model_filename)
    else:
        print(f"FastText model already exists at {cache_dir}")

if __name__ == '__main__':
    model_names = [
        # LV-BERT models
        "AiLab-IMCS-UL/lvbert",
        "SkyWater21/lvbert-lv-go-emotions",
        "SkyWater21/lvbert-lv-go-emotions-ekman",
        "SkyWater21/lvbert-lv-emotions-ekman",

        # RuBERT models
        "DeepPavlov/rubert-base-cased",
        "seara/rubert-base-cased-ru-go-emotions",
        "SkyWater21/rubert-base-cased-ru-go-emotions-ekman",
    ]

    # Download hugingface models
    for model_name in model_names:
        download_huggingface_model(model_name, cache_dir="./models")

    # Download FastText lid.176.bin model
    fasttext_url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
    download_fasttext_model(fasttext_url, cache_dir="./models")

    print("All models are downloaded and cached.")
