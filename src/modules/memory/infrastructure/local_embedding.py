
from typing import List
import numpy as np
from fastembed import TextEmbedding
from src.modules.memory.domain.embedding import EmbeddingService
from src.foundation.logging import logger

class LocalEmbeddingService(EmbeddingService):
    """
    Embedding Service using fastembed (ONNX).
    Supports E5 models locally on CPU/GPU via ONNX Runtime.
    """
    def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
        """
        Args:
            model_name: "intfloat/multilingual-e5-small" (Default, fast) 
                        or "intfloat/multilingual-e5-large" (Accurate)
                        or any supported by fastembed.
        """
        self.model_name = model_name
        logger.info(f"LocalEmbeddingService initializing with model: {self.model_name}")
        
        try:
            # Silence warning about MiniLM pooling change in newer fastembed versions
            import warnings
            warnings.filterwarnings("ignore", message="The model .* now uses mean pooling")
            
            # TextEmbedding handles download/caching
            self.model = TextEmbedding(model_name=self.model_name)
            logger.info("LocalEmbeddingService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize LocalEmbeddingService: {e}")
            raise e

    def embed_query(self, text: str) -> List[float]:
        """
        Embeds a single query.
        For E5, fastembed usually handles prefixes or expects them?
        FastEmbed E5 implementation usually handles "query: " internally depending on usage?
        Actually, FastEmbed docs say:
        "FastEmbed supports E5... The model expects 'query: ' prefix for queries."
        Wait, for ".embed()", does it add it?
        Usually, users need to add it unless using specific methods.
        However, `TextEmbedding` is generic.
        Let's assume we need to add standard E5 prefixes to be safe, 
        or check if FastEmbed does it.
        
        According to FastEmbed repo:
        "For E5 models... you should use 'query: ' prefix for queries and 'passage: ' for documents."
        So we will add it.
        """
        try:
            # Prefix handling
            # E5 requires "query: " / "passage: ".
            # MiniLM / others do not.
            # FastEmbed doesn't handle this automatically per model (yet).
            # Heuristic: Check model name.
            input_text = text.replace("\n", " ")
            if "e5" in self.model_name.lower():
                 input_text = f"query: {input_text}"
            
            # Generator - get first result
            embeddings = list(self.model.embed([input_text]))
            return embeddings[0].tolist()
        except Exception as e:
            logger.error(f"Local Embedding Error (Query): {e}")
            return []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds documents.
        Prefix: 'passage: '
        """
        try:
            clean_texts = []
            for t in texts:
                clean = t.replace("\n", " ")
                if "e5" in self.model_name.lower():
                    clean = f"passage: {clean}"
                clean_texts.append(clean)
            
            embeddings = list(self.model.embed(clean_texts))
            return [e.tolist() for e in embeddings]
        except Exception as e:
            logger.error(f"Local Embedding Error (Batch): {e}")
            return [[] for _ in texts]
