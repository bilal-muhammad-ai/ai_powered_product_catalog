from __future__ import annotations

from typing import Protocol

from app.services.ai_services.product_index.store import SparseEmbedding


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one normalized dense vector per text."""


class HuggingFaceEmbedder:
    """Local Hugging Face embedding model, loaded with HF_TOKEN.

    Same load and encode path as the Glancy ingest script:
    SentenceTransformer(model_name, token=...) and encode(..., normalize_embeddings=True).
    """

    def __init__(self, model_name: str, token: str) -> None:
        if not token:
            raise RuntimeError("Missing required environment variable: HF_TOKEN")
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, token=token)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()


class SparseEmbedder(Protocol):
    def embed(self, texts: list[str]) -> list[SparseEmbedding]:
        """Return one sparse vector per text."""


class FastEmbedSparseEmbedder:
    """Lexical BM25 vectors from FastEmbed, stored beside the dense passage vector."""

    def __init__(self, model_name: str) -> None:
        from fastembed import SparseTextEmbedding

        self._model = SparseTextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list[SparseEmbedding]:
        if not texts:
            return []
        return [
            SparseEmbedding(
                indices=[int(index) for index in embedding.indices],
                values=[float(value) for value in embedding.values],
            )
            for embedding in self._model.embed(texts)
        ]
