"""Embedding service — generates vector embeddings using Sentence-Transformers.

Uses the `all-MiniLM-L6-v2` model (free, local, 384 dimensions).
The model is loaded lazily on first use to avoid slow startup.
"""

import logging
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)

# Model is loaded lazily — not at import time
_model = None


def _get_model():
    """Lazily load the Sentence-Transformers model.

    Returns the model singleton. First call downloads/loads the model
    (~80MB, takes a few seconds). Subsequent calls return the cached instance.
    """
    global _model
    if _model is None:
        logger.info("Loading Sentence-Transformers model (all-MiniLM-L6-v2)...")
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("✅ Model loaded successfully")
    return _model


def generate_embedding(text: str) -> list[float]:
    """Generate a 384-dimensional embedding vector for the given text.

    Args:
        text: The input text (resume or job description).

    Returns:
        A list of 384 floats representing the text embedding.
    """
    model = _get_model()

    # Sentence-Transformers handles tokenization and truncation internally.
    # For very long texts, we chunk and average the embeddings for better coverage.
    max_chars = 5000  # approximate limit for good embedding quality

    if len(text) <= max_chars:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    # For longer texts: chunk into overlapping segments, embed each, mean-pool
    chunks = _chunk_text(text, chunk_size=max_chars, overlap=500)
    embeddings = model.encode(chunks, normalize_embeddings=True)

    # Mean pooling across chunks, then re-normalize
    mean_embedding = np.mean(embeddings, axis=0)
    norm = np.linalg.norm(mean_embedding)
    if norm > 0:
        mean_embedding = mean_embedding / norm

    return mean_embedding.tolist()


def compute_cosine_similarity(embedding_a: list[float], embedding_b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors.

    Used as a fallback when pgvector's <=> operator isn't available.

    Args:
        embedding_a: First embedding vector.
        embedding_b: Second embedding vector.

    Returns:
        Cosine similarity score between 0 and 1.
    """
    a = np.array(embedding_a)
    b = np.array(embedding_b)

    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    similarity = dot_product / (norm_a * norm_b)
    # Clamp to [0, 1] — normalized embeddings should already be in this range
    return float(max(0.0, min(1.0, similarity)))


def _chunk_text(text: str, chunk_size: int = 5000, overlap: int = 500) -> list[str]:
    """Split text into overlapping chunks for embedding long documents.

    Args:
        text: The full text to chunk.
        chunk_size: Maximum characters per chunk.
        overlap: Number of overlapping characters between chunks.

    Returns:
        List of text chunks.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap

    return chunks if chunks else [text]
