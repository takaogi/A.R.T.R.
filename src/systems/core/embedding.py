import sys
from src.utils.logger import logger

try:
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModel
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("Torch/Transformers not available. Using Mock EmbeddingService.")
    TORCH_AVAILABLE = False
except OSError:
    logger.warning("Torch DLL load failed. Using Mock EmbeddingService.")
    TORCH_AVAILABLE = False

def average_pool(last_hidden_states, attention_mask):
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

class EmbeddingService:
    """
    Singleton service for generating text embeddings using E5.
    Decoupled from EmotionAnalyzer to allow shared usage with Memory systems.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def initialize(self):
        if self.initialized:
            return

        logger.info("Initializing EmbeddingService (E5)...")
        
        if not TORCH_AVAILABLE:
            logger.warning("Running EmbeddingService in MOCK MODE.")
            self.mock_mode = True
            self.initialized = True
            return

        self.mock_mode = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"EmbeddingService Device: {self.device}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained('intfloat/multilingual-e5-small')
            self.model = AutoModel.from_pretrained('intfloat/multilingual-e5-small').to(self.device)
        except Exception as e:
            logger.error(f"Failed to load E5 model: {e}. Switching to Mock Mode.")
            self.mock_mode = True
            self.initialized = True
            return

        self.initialized = True
        logger.info("EmbeddingService Initialized.")

    def get_embedding(self, text: str, mode="query"):
        """
        Returns normalized embedding vector for the text.
        Prefixes 'query: ' or 'passage: ' based on mode.
        Returns 1D numpy array or torch tensor (cpu).
        """
        if not self.initialized:
            self.initialize()

        if self.mock_mode:
            import numpy as np
            return np.zeros(384)

        prefix = "query: " if mode == "query" else "passage: "
        input_text = f"{prefix}{text}"
        
        batch_dict = self.tokenizer([input_text], max_length=512, padding=True, truncation=True, return_tensors='pt').to(self.device)
        with torch.no_grad():
            outputs = self.model(**batch_dict)
            embed = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
            embed = F.normalize(embed, p=2, dim=1)
            
        return embed[0].cpu() # Keep as tensor or convert to numpy? ArchivalMemory expects list/numpy.
        # Let's return CPU tensor, caller can convert. Or standardizing on numpy might be safer.
        # Original code returned tensor if not handled. Let's return CPU tensor to be safe with existing logic,
        # but ArchivalMemory did .cpu().numpy() checks.
        
    def get_batch_embeddings(self, texts: list[str], mode="passage"):
        """
        Batch processing for efficiency (e.g. precomputing anchors).
        """
        if not self.initialized:
            self.initialize()
            
        if self.mock_mode:
            if TORCH_AVAILABLE:
                return torch.zeros((len(texts), 384)).to(self.device)
            else:
                import numpy as np
                return np.zeros((len(texts), 384))

        prefix = "query: " if mode == "query" else "passage: "
        input_texts = [f"{prefix}{t}" for t in texts]
        
        batch_dict = self.tokenizer(input_texts, max_length=512, padding=True, truncation=True, return_tensors='pt').to(self.device)
        with torch.no_grad():
            outputs = self.model(**batch_dict)
            embed = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
            embed = F.normalize(embed, p=2, dim=1)
            
        return embed # Returns tensor on device
