from transformers import AutoModel, AutoTokenizer
import torch
from config import settings
import os

tokenizer = None
model = None

def load_embedding_model():
    global tokenizer, model
    path = settings.bge_m3_path
    if os.path.exists(path):
        tokenizer = AutoTokenizer.from_pretrained(path)
        model = AutoModel.from_pretrained(path)
    else:
        tokenizer, model = None, None

def get_embedding(text: str) -> list:
    if model is None:
        from chromadb.utils import embedding_functions
        ef = embedding_functions.DefaultEmbeddingFunction()
        return ef([text])[0]
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    embedding = outputs.last_hidden_state[:, 0, :].squeeze().tolist()
    return embedding

load_embedding_model()
