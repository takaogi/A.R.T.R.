import os
import numpy as np
import onnxruntime as ort
from typing import List
from tokenizers import Tokenizer
from huggingface_hub import snapshot_download
from src.foundation.logging import logger
from src.modules.memory.domain.embedding import EmbeddingService
from src.foundation.paths.manager import PathManager

class E5OnnxEmbeddingService(EmbeddingService):
    """
    Embedding Service using E5 Model (ONNX version).
    Defaults to 'Xenova/multilingual-e5-small' for lightweight, no-torch inference.
    """
    def __init__(self, model_id: str = "Xenova/multilingual-e5-small", device: str = "cpu"):
        self.model_id = model_id
        self.device = device
        self.model_path = self._ensure_model()
        self.tokenizer = Tokenizer.from_file(os.path.join(self.model_path, "tokenizer.json"))
        # Enable Padding & Truncation for batch processing
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding(pad_id=self.tokenizer.token_to_id("<pad>") or 0, pad_token="<pad>", length=512)
        
        # Load ONNX Session
        sess_options = ort.SessionOptions()
        # sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Search for ONNX file (prefer quantized)
        potential_files = [
            "model_quantized.onnx",
            "model.onnx", 
            "onnx/model_quantized.onnx",
            "onnx/model_int8.onnx",
            "onnx/model.onnx"
        ]
        
        onnx_file = None
        for f in potential_files:
            if os.path.exists(os.path.join(self.model_path, f)):
                onnx_file = f
                break
                
        if not onnx_file:
            raise FileNotFoundError(f"Could not find valid ONNX model in {self.model_path}")
            
        providers = ["CPUExecutionProvider"]
        if self.device == "cuda" and "CUDAExecutionProvider" in ort.get_available_providers():
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            
        self.session = ort.InferenceSession(os.path.join(self.model_path, onnx_file), sess_options, providers=providers)
        logger.info(f"E5OnnxEmbeddingService initialized with {model_id} (File: {onnx_file}) on {providers[0]}")

    def _ensure_model(self) -> str:
        """Download model if not present."""
        cache_dir = PathManager.get_instance().get_models_dir() / "embedding"
        
        # We assume common standard cache path or local dir
        # For simplicity, we trust hf_hub's cache or download to specific local dir
        local_dir = cache_dir / self.model_id.replace("/", "_")
        
        if not local_dir.exists():
            logger.info(f"Downloading {self.model_id} to {local_dir}...")
            snapshot_download(repo_id=self.model_id, local_dir=str(local_dir))
        
        return str(local_dir)

    def _mean_pooling(self, model_output, attention_mask):
        """
        Mean Pooling - Take attention mask into account for correct averaging
        """
        token_embeddings = model_output # First element of model_output contains all token embeddings
        
        input_mask_expanded = np.expand_dims(attention_mask, -1) # convert to (Batch, Seq, 1)
        input_mask_expanded = np.broadcast_to(input_mask_expanded, token_embeddings.shape).astype(float)
        
        sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
        sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
        
        return sum_embeddings / sum_mask

    def _embed(self, texts: List[str]) -> List[List[float]]:
        encoded = self.tokenizer.encode_batch(texts)
        
        input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        
        # ONNX Inference
        model_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask
        }
        
        # Check if model needs token_type_ids
        input_names = [node.name for node in self.session.get_inputs()]
        if "token_type_ids" in input_names:
            model_inputs["token_type_ids"] = np.array([e.type_ids for e in encoded], dtype=np.int64)

        outputs = self.session.run(None, model_inputs)
        last_hidden_state = outputs[0]
        
        # Pooling
        embeddings = self._mean_pooling(last_hidden_state, attention_mask)
        
        # Normalization (L2)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        # E5 requires "query: " prefix for asymmetric tasks
        return self._embed([f"query: {text}"])[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # E5 requires "passage: " prefix (or simply no prefix if symmetric? usually passage:)
        prefixed = [f"passage: {t}" for t in texts]
        return self._embed(prefixed)
