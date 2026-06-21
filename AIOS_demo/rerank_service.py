from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
from config import settings
import os

rerank_tokenizer = None
rerank_model = None

def load_rerank_model():
    global rerank_tokenizer, rerank_model
    path = settings.reranker_path
    if os.path.exists(path):
        rerank_tokenizer = AutoTokenizer.from_pretrained(path)
        rerank_model = AutoModelForSequenceClassification.from_pretrained(path)
    else:
        rerank_tokenizer, rerank_model = None, None

def rerank(query: str, documents: list, top_n: int = 3) -> list:
    if rerank_model is None:
        return documents[:top_n]
    pairs = [[query, doc] for doc in documents]
    with torch.no_grad():
        inputs = rerank_tokenizer(pairs, padding=True, truncation=True, return_tensors="pt", max_length=512)
        scores = rerank_model(**inputs).logits.squeeze().tolist()
    indexed = list(enumerate(scores if isinstance(scores, list) else [scores]))
    indexed.sort(key=lambda x: x[1], reverse=True)
    return [documents[i] for i, _ in indexed[:top_n]]

load_rerank_model()
