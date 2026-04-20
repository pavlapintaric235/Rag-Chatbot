from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingService:
    """
    Thin wrapper around a SentenceTransformer embedding model.
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts. Normalized embeddings help make similarity
        search behavior more stable across inputs.
        """
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=settings.embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a single query string.
        """
        embeddings = self.embed_texts([query])
        return embeddings[0]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(settings.embedding_model_name)