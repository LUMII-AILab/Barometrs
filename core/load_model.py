from keybert import KeyBERT
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline, AutoModel
from sentence_transformers import SentenceTransformer, models
from path_config import models_path, stopwords_path
import os
import torch

print('CUDA available:', torch.cuda.is_available())

# decode model name from short name
def get_model_name(short_name: str):
    # check if model full name is provided
    if short_name in [
        'AiLab-IMCS-UL/lvbert',
        'SkyWater21/lvbert-lv-go-emotions',
        'SkyWater21/lvbert-lv-go-emotions-ekman',
        'DeepPavlov/rubert-base-cased',
        'seara/rubert-base-cased-ru-go-emotions',
        'SkyWater21/rubert-base-cased-ru-go-emotions-ekman'
    ]:
        return short_name

    if short_name == 'lvbert':
        return 'AiLab-IMCS-UL/lvbert'
    elif short_name == 'lvbert-lv-go-emotions':
        return 'SkyWater21/lvbert-lv-go-emotions'
    elif short_name == 'lvbert-lv-go-emotions-ekman':
        return 'SkyWater21/lvbert-lv-go-emotions-ekman'
    elif short_name == 'rubert-base-cased':
        return 'DeepPavlov/rubert-base-cased'
    elif short_name == 'rubert-base-cased-ru-go-emotions':
        return 'seara/rubert-base-cased-ru-go-emotions'
    elif short_name == 'rubert-base-cased-ru-go-emotions-ekman':
        return 'SkyWater21/rubert-base-cased-ru-go-emotions-ekman'
    else:
        return None


def get_pipeline_for_model(model_shortname: str):
    model_name = get_model_name(model_shortname)
    model, tokenizer = get_classifier_model_and_tokenizer(model_name)
    model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    return pipeline("text-classification", model=model, tokenizer=tokenizer, top_k=None, max_length=512,
                    truncation=True, device=0 if torch.cuda.is_available() else -1)

def get_classifier_model_and_tokenizer(model_shortname: str):
    model_name = get_model_name(model_shortname)
    model_directory = models_path()
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, local_files_only=True, cache_dir=model_directory
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True, cache_dir=model_directory)
    return model, tokenizer

def get_embedding_model_and_tokenizer(model_shortname: str):
    model_name = get_model_name(model_shortname)
    model_directory = models_path()
    model = AutoModel.from_pretrained(
        model_name, local_files_only=True, cache_dir=model_directory, output_hidden_states=True
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True, cache_dir=model_directory)
    return model, tokenizer

def get_keybert_model(model_shortname: str):
    model_name = get_model_name(model_shortname)
    model_directory = models_path()
    transformer_model = models.Transformer(
        model_name_or_path=model_name,
        tokenizer_name_or_path=model_name,
        cache_dir=model_directory
    )
    pooling_model = models.Pooling(
        transformer_model.get_word_embedding_dimension(),
        pooling_mode_mean_tokens=True
    )
    st_model = SentenceTransformer(
        modules=[transformer_model, pooling_model],
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )

    return KeyBERT(model=st_model)

def get_keybert_model_by_language_and_prediction_type(language: str, prediction_type: str):
    if language == 'lv' and prediction_type == 'normal':
        return get_keybert_model('lvbert-lv-go-emotions')
    elif language == 'lv' and prediction_type == 'ekman':
        return get_keybert_model('lvbert-lv-go-emotions-ekman')
    elif language == 'ru' and prediction_type == 'normal':
        return get_keybert_model('rubert-base-cased-ru-go-emotions')
    elif language == 'ru' and prediction_type == 'ekman':
        return get_keybert_model('rubert-base-cased-ru-go-emotions-ekman')
    else:
        return None

def get_stopwords(language: str):
    path = stopwords_path(language + '.txt')
    if not os.path.exists(path):
        return None
    with open(path, 'r') as file:
        stopwords = file.read().splitlines()
    return stopwords