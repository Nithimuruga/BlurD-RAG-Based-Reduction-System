from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import torch
import numpy as np
from typing import List, Dict, Optional
import logging
from app.services.detection_pipeline import BaseDetector, DetectionCandidate, EntityType
from app.utils.serialization import convert_numpy_types

logger = logging.getLogger(__name__)

class HuggingFaceDetector(BaseDetector):
    """Hugging Face transformer-based PII detection"""
    
    def __init__(self, model_name: str = "dbmdz/bert-large-cased-finetuned-conll03-english"):
        super().__init__("huggingface_ner")
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.ner_pipeline = None
        
        # Entity label mappings from model to our types
        self._label_mapping = {
            "PERSON": EntityType.PERSON,
            "PER": EntityType.PERSON,
            "ORGANIZATION": EntityType.ORGANIZATION,
            "ORG": EntityType.ORGANIZATION,
            "LOCATION": EntityType.LOCATION,
            "LOC": EntityType.LOCATION,
            "GPE": EntityType.LOCATION,
            "DATE_TIME": EntityType.DATE,
            "DATE": EntityType.DATE,
            "EMAIL_ADDRESS": EntityType.EMAIL,
            "EMAIL": EntityType.EMAIL,
            "PHONE_NUMBER": EntityType.PHONE,
            "PHONE": EntityType.PHONE,
            "CREDIT_CARD": EntityType.CREDIT_CARD,
            "IBAN_CODE": EntityType.IBAN,
            "IP_ADDRESS": EntityType.IP_ADDRESS,
            "URL": EntityType.URL,
            "US_SSN": EntityType.SSN,
            "SSN": EntityType.SSN,
            "US_PASSPORT": EntityType.CUSTOM,
            "PASSPORT": EntityType.CUSTOM,
            "US_DRIVER_LICENSE": EntityType.CUSTOM,
            "DRIVER_LICENSE": EntityType.CUSTOM,
            "MEDICAL_LICENSE": EntityType.CUSTOM,
            "CRYPTO": EntityType.CUSTOM,
            "NRP": EntityType.CUSTOM,  # Named Person Recognition
        }
        
        self._load_model()
    
    def _load_model(self):
        """Load Hugging Face model and tokenizer"""
        try:
            # Check if CUDA is available
            device = 0 if torch.cuda.is_available() else -1
            
            # Try to load the specified model, fallback to alternatives
            model_alternatives = [
                self.model_name,
                "dbmdz/bert-large-cased-finetuned-conll03-english",
                "dslim/bert-base-NER",
                "Jean-Baptiste/roberta-large-ner-english"
            ]
            
            for model_name in model_alternatives:
                try:
                    logger.info(f"Attempting to load model: {model_name}")
                    
                    # Create NER pipeline
                    self.ner_pipeline = pipeline(
                        "ner",
                        model=model_name,
                        tokenizer=model_name,
                        aggregation_strategy="simple",
                        device=device
                    )
                    
                    self.model_name = model_name
                    logger.info(f"Successfully loaded model: {model_name}")
                    break
                    
                except Exception as e:
                    logger.warning(f"Failed to load model {model_name}: {e}")
                    continue
            
            if not self.ner_pipeline:
                logger.error("Failed to load any Hugging Face NER model")
                self.enabled = False
                
        except Exception as e:
            logger.error(f"Error initializing Hugging Face detector: {e}")
            self.enabled = False
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Detect PII using Hugging Face model"""
        if not self.ner_pipeline or not self.enabled:
            return []
        
        candidates = []
        
        try:
            # Split text into chunks if too long
            max_length = 512
            text_chunks = self._split_text(text, max_length)
            
            for chunk_start, chunk_text in text_chunks:
                # Run NER on chunk
                entities = self.ner_pipeline(chunk_text)
                
                for entity in entities:
                    # Map entity label to our EntityType
                    entity_type = self._map_entity_label(entity["entity_group"])
                    
                    if entity_type:
                        # Calculate absolute positions in original text
                        start_char = chunk_start + entity["start"]
                        end_char = chunk_start + entity["end"]
                        
                        # Convert NumPy score to Python native float if needed
                        score = float(entity["score"]) if isinstance(entity["score"], (np.number, np.ndarray)) else entity["score"]
                        
                        candidate = DetectionCandidate(
                            id=None,
                            type=entity_type,
                            text=entity["word"],
                            bbox=None,
                            confidence=score,
                            start_char=start_char,
                            end_char=end_char,
                            source=self.name,
                            metadata={
                                "model_name": self.model_name,
                                "original_label": entity["entity_group"],
                                "raw_score": score,
                                "model_confidence": score
                            }
                        )
                        candidates.append(candidate)
            
        except Exception as e:
            logger.error(f"Error in Hugging Face detection: {e}")
        
        return candidates
    
    def _split_text(self, text: str, max_length: int) -> List[tuple]:
        """Split text into chunks for processing"""
        chunks = []
        
        if len(text) <= max_length:
            return [(0, text)]
        
        # Split by sentences or paragraphs when possible
        sentences = text.split('. ')
        current_chunk = ""
        current_start = 0
        
        for sentence in sentences:
            if len(current_chunk + sentence) <= max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append((current_start, current_chunk.strip()))
                    current_start += len(current_chunk)
                    current_chunk = sentence + ". "
                else:
                    # Single sentence is too long, split by characters
                    for i in range(0, len(sentence), max_length):
                        chunk = sentence[i:i + max_length]
                        chunks.append((current_start + i, chunk))
        
        if current_chunk:
            chunks.append((current_start, current_chunk.strip()))
        
        return chunks
    
    def _map_entity_label(self, label: str) -> Optional[EntityType]:
        """Map model entity labels to our EntityType enum"""
        # Clean the label (remove B-, I- prefixes from BIO tagging)
        clean_label = label.replace("B-", "").replace("I-", "")
        return self._label_mapping.get(clean_label.upper())
    
    def get_supported_types(self) -> List[EntityType]:
        """Return supported entity types"""
        return list(set(self._label_mapping.values()))

class CustomPIIDetector(BaseDetector):
    """Custom fine-tuned PII detection model"""
    
    def __init__(self, model_path: str = None):
        super().__init__("custom_pii")
        self.model_path = model_path or "dbmdz/bert-large-cased-finetuned-conll03-english"
        self.ner_pipeline = None
        self._load_custom_model()
    
    def _load_custom_model(self):
        """Load custom fine-tuned model"""
        try:
            device = 0 if torch.cuda.is_available() else -1
            
            # Load custom model or fallback to pre-trained
            self.ner_pipeline = pipeline(
                "ner",
                model=self.model_path,
                aggregation_strategy="simple",
                device=device
            )
            
            logger.info(f"Loaded custom PII model from: {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load custom model: {e}")
            self.enabled = False
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Detect PII using custom model"""
        if not self.ner_pipeline or not self.enabled:
            return []
        
        candidates = []
        
        try:
            # Process text
            entities = self.ner_pipeline(text)
            
            for entity in entities:
                # High confidence threshold for custom model
                if entity["score"] >= 0.8:
                    candidate = DetectionCandidate(
                        id=None,
                        type=self._map_custom_label(entity["entity_group"]),
                        text=entity["word"],
                        bbox=None,
                        confidence=entity["score"],
                        start_char=entity["start"],
                        end_char=entity["end"],
                        source=self.name,
                        metadata={
                            "custom_model": True,
                            "model_path": self.model_path,
                            "raw_label": entity["entity_group"],
                            "high_confidence": entity["score"] >= 0.9
                        }
                    )
                    candidates.append(candidate)
                    
        except Exception as e:
            logger.error(f"Error in custom PII detection: {e}")
        
        return candidates
    
    def _map_custom_label(self, label: str) -> EntityType:
        """Map custom model labels to EntityType"""
        # This would be customized based on your fine-tuned model's labels
        label_mapping = {
            "PII": EntityType.CUSTOM,
            "SENSITIVE": EntityType.CUSTOM,
            "PERSONAL": EntityType.PERSON,
            "FINANCIAL": EntityType.CREDIT_CARD,
            "CONTACT": EntityType.EMAIL,
            "IDENTIFIER": EntityType.SSN,
        }
        
        clean_label = label.replace("B-", "").replace("I-", "").upper()
        return label_mapping.get(clean_label, EntityType.CUSTOM)
    
    def get_supported_types(self) -> List[EntityType]:
        """Return supported entity types for custom model"""
        return [EntityType.CUSTOM, EntityType.PERSON, EntityType.EMAIL, 
                EntityType.CREDIT_CARD, EntityType.SSN]

class EnsembleTransformerDetector(BaseDetector):
    """Ensemble of multiple transformer models for robust detection"""
    
    def __init__(self):
        super().__init__("ensemble_transformers")
        self.detectors = []
        self._initialize_ensemble()
    
    def _initialize_ensemble(self):
        """Initialize multiple transformer models"""
        models = [
            "dbmdz/bert-large-cased-finetuned-conll03-english",
            "dslim/bert-base-NER",
            "Jean-Baptiste/roberta-large-ner-english"
        ]
        
        for model_name in models:
            try:
                detector = HuggingFaceDetector(model_name)
                if detector.enabled:
                    self.detectors.append(detector)
            except Exception as e:
                logger.warning(f"Failed to load ensemble model {model_name}: {e}")
        
        if not self.detectors:
            self.enabled = False
            logger.error("No models loaded for ensemble detector")
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Detect using ensemble of models"""
        if not self.enabled:
            return []
        
        all_candidates = []
        
        # Run all models
        for detector in self.detectors:
            candidates = await detector.detect(text, **kwargs)
            all_candidates.extend(candidates)
        
        # Apply ensemble voting/confidence boosting
        ensemble_candidates = self._apply_ensemble_logic(all_candidates)
        
        return ensemble_candidates
    
    def _apply_ensemble_logic(self, candidates: List[DetectionCandidate]) -> List[DetectionCandidate]:
        """Apply ensemble logic to combine predictions"""
        # Group candidates by text position
        position_groups = {}
        
        for candidate in candidates:
            key = (candidate.start_char, candidate.end_char, candidate.type)
            if key not in position_groups:
                position_groups[key] = []
            position_groups[key].append(candidate)
        
        ensemble_candidates = []
        
        for (start, end, entity_type), group in position_groups.items():
            if len(group) == 1:
                # Single detection
                ensemble_candidates.append(group[0])
            else:
                # Multiple detections - create ensemble candidate
                avg_confidence = sum(c.confidence for c in group) / len(group)
                
                # Boost confidence if multiple models agree
                agreement_boost = min(0.2, (len(group) - 1) * 0.1)
                final_confidence = min(avg_confidence + agreement_boost, 1.0)
                
                ensemble_candidate = DetectionCandidate(
                    id=None,
                    type=entity_type,
                    text=group[0].text,  # Use first detection's text
                    bbox=None,
                    confidence=final_confidence,
                    start_char=start,
                    end_char=end,
                    source=f"{self.name}_ensemble",
                    metadata={
                        "ensemble_size": len(group),
                        "model_agreements": len(group),
                        "individual_confidences": [c.confidence for c in group],
                        "contributing_models": [c.source for c in group]
                    }
                )
                ensemble_candidates.append(ensemble_candidate)
        
        return ensemble_candidates
    
    def get_supported_types(self) -> List[EntityType]:
        """Return supported types from all ensemble models"""
        supported_types = set()
        for detector in self.detectors:
            supported_types.update(detector.get_supported_types())
        return list(supported_types)