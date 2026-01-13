from typing import List
import os
from openai import OpenAI
from src.modules.memory.domain.embedding import EmbeddingService
from src.foundation.logging import logger

class OpenAIEmbeddingService(EmbeddingService):
    """
    Embedding Service using OpenAI's API.
    Defaults to 'text-embedding-3-small'.
    """
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
             # Fallback to config or error
             logger.warning("OpenAIEmbeddingService: No API Key provided.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        logger.info(f"OpenAIEmbeddingService initialized (Model: {self.model})")

    def embed_query(self, text: str) -> List[float]:
        # Clean text
        text = text.replace("\n", " ")
        return self._get_embedding(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # OpenAI supports batching? Yes.
        clean_texts = [t.replace("\n", " ") for t in texts]
        return self._get_batch_embeddings(clean_texts)

    def _get_embedding(self, text: str) -> List[float]:
        try:
            response = self.client.embeddings.create(input=[text], model=self.model)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI Embedding Error: {e}")
            return []

    def _get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
             # OpenAI Batch Limit is usually high, but we should handle huge batches if needed.
             # For now assume reasonably small batches.
            response = self.client.embeddings.create(input=texts, model=self.model)
            # Response data is list of objects, usually ordered by index
            # Check sorting just in case
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            logger.error(f"OpenAI Batch Embedding Error: {e}")
            return [[] for _ in texts]
