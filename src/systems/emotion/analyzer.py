import sys
from src.utils.logger import logger

try:
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("Torch/Transformers not available. Using Mock EmotionAnalyzer.")
    TORCH_AVAILABLE = False
except OSError:
    logger.warning("Torch DLL load failed. Using Mock EmotionAnalyzer.")
    TORCH_AVAILABLE = False

# Remove average_pool helper (now in embedding.py)

class EmotionAnalyzer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmotionAnalyzer, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def initialize(self):
        if self.initialized:
            return

        logger.info("Initializing EmotionAnalyzer (Intensity Focus)...")
        
        # 0. Initialize Embedding Service
        from src.systems.core.embedding import EmbeddingService
        self.embedding_service = EmbeddingService()
        self.embedding_service.initialize()

        if not TORCH_AVAILABLE:
            logger.warning("Running in MOCK MODE due to missing dependencies.")
            self.mock_mode = True
            self.initialized = True
            return

        self.mock_mode = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"EmotionAnalyzer Device: {self.device}")

        try:
            # 1. Load Intensity Model (WRIME) -> Only this remains here
            logger.info("Loading WRIME (Intensity)...")
            self.wrime_name = 'patrickramos/bert-base-japanese-v2-wrime-fine-tune'
            self.wrime_tokenizer = AutoTokenizer.from_pretrained(self.wrime_name)
            self.wrime_model = AutoModelForSequenceClassification.from_pretrained(self.wrime_name).to(self.device)
        except Exception as e:
            logger.error(f"Failed to load WRIME model: {e}. Switching to Mock Mode.")
            self.mock_mode = True
            self.initialized = True
            return

        # 3. Define Anchors
        self.anchors = {
            "Praise_Appearance": "かわいい。美しい。スタイルいいね。服似合ってるよ。自分好みだ。",
            "Praise_Ability": "かっこいい。頼りになる。天才。仕事ができる。頭いい。尊敬する。",
            "Confession": "好きだ。愛してる。付き合って。結婚しよう。ずっと一緒にいたい。",
            "Skinship": "（頭を撫でる）。キスする。抱きしめる。手を繋ぐ。触れる。",
            "Teasing": "へー、意外とドジだね。顔赤いよ。からかう。冗談だよ。反応が面白い。図星でしょ。",
            "Comfort_Give": "大丈夫？辛かったね。よしよし。守るよ。泣いてもいいよ。私がついてる。",
            "Comfort_Seek": "助けて。辛い。疲れた。慰めて。話聞いて。寂しい。構って。",
            "Serious": "大事な話がある。真面目に聞いて。相談に乗って。",
            "Rejection": "嫌いだ。あっち行け。触るな。近寄るな。不快だ。ウザい。",
            "Attack": "死ね。消えろ。クズ。馬鹿。役立たず。最低だ。"
        }
        self.anchor_keys = list(self.anchors.keys())
        self._precompute_anchors()

        # 4. Intensity Map
        self.category_map = {
            "Praise_Appearance": [0],         # Joy
            "Praise_Ability":    [0, 7],      # Joy, Trust
            "Confession":        [0, 7, 2],   # Joy, Trust, Anticipation
            "Skinship":          [0, 7],      # Joy, Trust
            "Teasing":           [3, 0],      # Surprise, Joy
            "Comfort_Give":      [0, 7],      # Joy, Trust
            "Comfort_Seek":      [1, 5],      # Sadness, Fear
            "Serious":           [2, 5],      # Anticipation, Fear
            "Rejection":         [6, 4],      # Disgust, Anger
            "Attack":            [4, 6]       # Anger, Disgust
        }
        
        self.initialized = True
        logger.info("EmotionAnalyzer Initialized.")

    def _precompute_anchors(self):
        anchor_texts = [self.anchors[k] for k in self.anchor_keys]
        # Use EmbeddingService batch
        self.anchor_embeddings = self.embedding_service.get_batch_embeddings(anchor_texts, mode="passage")

    def get_embedding(self, text: str, mode="query"):
        """Deprecated alias for compatibility, delegates to service."""
        return self.embedding_service.get_embedding(text, mode=mode)

    def analyze(self, text: str):
        if not self.initialized:
            self.initialize()
            
        if self.mock_mode:
            # Simple keyword matching fallback
            cat = "Normal"
            score = 0.5
            if "すごい" in text or "かわいい" in text: cat = "Praise_Appearance"; score = 0.9
            elif "バカ" in text or "死ね" in text: cat = "Attack"; score = 0.9
            return {
                "text": text,
                "category": cat,
                "confidence": score * 100,
                "intensity": score
            }


        # A. Detect Intent (E5 via Service)
        query_embed = self.embedding_service.get_embedding(text, mode="query").to(self.device).unsqueeze(0)
        
        scores = (query_embed @ self.anchor_embeddings.T) * 100
        best_idx = torch.argmax(scores).item()
        category = self.anchor_keys[best_idx]
        confidence = scores[0, best_idx].item()

        # B. Detect Intensity (WRIME)
        inputs = self.wrime_tokenizer(text, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.wrime_model(**inputs)
            raw_intensities = outputs.logits[0][:8].tolist()
        
        # C. Calculate Unified Intensity
        target_dims = self.category_map.get(category, [])
        if not target_dims:
            final_intensity = 0.0
        else:
            relevant_scores = [raw_intensities[i] for i in target_dims]
            final_intensity = max(0.0, max(relevant_scores))

        return {
            "text": text,
            "category": category,
            "confidence": confidence,
            "intensity": final_intensity
        }
