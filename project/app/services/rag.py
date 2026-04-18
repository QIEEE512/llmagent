from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import List

from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings


@dataclass
class RetrievedChunk:
    text: str
    score: float
    index: int


def chunk_text(text: str, chunk_chars: int = 1200, overlap: int = 150) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    # normalize whitespace a bit
    text = "\n".join([ln.rstrip() for ln in text.splitlines()])

    out: List[str] = []
    i = 0
    n = len(text)
    step = max(1, chunk_chars - overlap)
    while i < n:
        chunk = text[i : i + chunk_chars].strip()
        if chunk:
            out.append(chunk)
        i += step
    return out


def retrieve_tfidf(query: str, chunks: List[str], top_k: int = 5) -> List[RetrievedChunk]:
    query = (query or "").strip()
    if not chunks:
        return []

    # If query is empty, just return first few chunks.
    if not query:
        return [RetrievedChunk(text=c, score=1.0, index=i) for i, c in enumerate(chunks[:top_k])]

    vec = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\\b\\w+\\b",
    )

    try:
        X = vec.fit_transform(chunks)
        q = vec.transform([query])
        sims = cosine_similarity(q, X)[0]
    except Exception:
        # Some inputs may cause sklearn to fail (e.g., empty vocabulary).
        # Fallback: return the first few chunks to keep the pipeline alive.
        return [RetrievedChunk(text=c, score=1.0, index=i) for i, c in enumerate(chunks[:top_k])]

    ranked = sorted(enumerate(sims.tolist()), key=lambda x: x[1], reverse=True)
    out: List[RetrievedChunk] = []
    for idx, score in ranked[:top_k]:
        if math.isfinite(score) and score > 0:
            out.append(RetrievedChunk(text=chunks[idx], score=float(score), index=int(idx)))
    return out


def _get_openai_client() -> OpenAI:
    key = (
        settings.openai_api_key
        or settings.dashscope_api_key
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("APP_DASHSCOPE_API_KEY")
    )
    if not key:
        raise RuntimeError("missing model key")

    # DashScope compatible-mode
    if settings.dashscope_api_key and not settings.openai_api_key:
        return OpenAI(api_key=key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    return OpenAI(api_key=key)


def _request_timeout_seconds(default: float) -> float:
    raw = os.environ.get("APP_MODEL_TIMEOUT_SECONDS")
    if not raw:
        return float(default)
    try:
        v = float(raw)
        return v if v > 0 else float(default)
    except Exception:
        return float(default)


def embed_texts(texts: List[str], model: str = "text-embedding-v4") -> List[List[float]]:
    """Embed a list of texts using Qwen embedding model via OpenAI compatible API."""
    if not texts:
        return []

    client = _get_openai_client()
    timeout_s = _request_timeout_seconds(15)

    # OpenAI compatible embeddings API
    resp = client.embeddings.create(model=model, input=texts, timeout=timeout_s)

    # resp.data is list with .embedding
    return [d.embedding for d in resp.data]


def retrieve_embeddings(query: str, chunks: List[str], top_k: int = 5, model: str = "text-embedding-v4") -> List[RetrievedChunk]:
    """Retrieve top chunks by cosine similarity in embedding space."""
    query = (query or "").strip()
    if not chunks:
        return []
    if not query:
        return [RetrievedChunk(text=c, score=1.0, index=i) for i, c in enumerate(chunks[:top_k])]

    # 1) embed query + chunks
    vecs = embed_texts([query] + chunks, model=model)
    if not vecs or len(vecs) != 1 + len(chunks):
        return []

    q = vecs[0]
    docs = vecs[1:]

    def cos(a: List[float], b: List[float]) -> float:
        dot = 0.0
        na = 0.0
        nb = 0.0
        for x, y in zip(a, b):
            dot += float(x) * float(y)
            na += float(x) * float(x)
            nb += float(y) * float(y)
        if na <= 0 or nb <= 0:
            return 0.0
        return dot / math.sqrt(na * nb)

    sims = [(i, cos(q, v)) for i, v in enumerate(docs)]
    sims.sort(key=lambda x: x[1], reverse=True)

    out: List[RetrievedChunk] = []
    for idx, score in sims[:top_k]:
        if math.isfinite(score) and score > 0:
            out.append(RetrievedChunk(text=chunks[idx], score=float(score), index=int(idx)))
    return out
