import spacy
from spacy.tokens import Doc, Span
from typing import List, Optional
import logging
from app.services.detection_pipeline import BaseDetector, DetectionCandidate, EntityType

logger = logging.getLogger(__name__)

class SpacyNERDetector(BaseDetector):
    """spaCy-based Named Entity Recognition detector"""
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        super().__init__("spacy_ner")
        self.model_name = model_name
        self.nlp = None
        self._entity_mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORGANIZATION,
            "GPE": EntityType.LOCATION,  # Geopolitical entity
            "LOC": EntityType.LOCATION,
            "DATE": EntityType.DATE,
            "TIME": EntityType.DATE,
            "MONEY": EntityType.CUSTOM,
            "PERCENT": EntityType.CUSTOM,
        }
        self._load_model()
    
    def _load_model(self):
        """Load spaCy model"""
        try:
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Successfully loaded spaCy model: {self.model_name}")
        except OSError:
            logger.error(f"Failed to load spaCy model: {self.model_name}")
            logger.info("Please install the model using: python -m spacy download en_core_web_sm")
            self.enabled = False
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Detect named entities using spaCy"""
        if not self.nlp or not self.enabled:
            return []
        
        candidates = []
        
        try:
            # Process text with spaCy
            doc = self.nlp(text)
            
            # Extract named entities
            for ent in doc.ents:
                entity_type = self._map_spacy_label(ent.label_)
                
                if entity_type:
                    # Calculate confidence based on spaCy's internal confidence
                    # spaCy doesn't provide confidence scores directly, so we estimate
                    confidence = self._calculate_confidence(ent, doc)
                    
                    candidate = DetectionCandidate(
                        id=None,
                        type=entity_type,
                        text=ent.text,
                        bbox=None,
                        confidence=confidence,
                        start_char=ent.start_char,
                        end_char=ent.end_char,
                        source=self.name,
                        metadata={
                            "spacy_label": ent.label_,
                            "spacy_explanation": spacy.explain(ent.label_),
                            "lemma": ent.lemma_,
                            "pos_tags": [token.pos_ for token in ent],
                            "is_alpha": ent.text.isalpha(),
                            "is_title": ent.text.istitle()
                        }
                    )
                    candidates.append(candidate)
            
            # Additional processing for custom entities
            candidates.extend(await self._detect_custom_patterns(doc))
            
        except Exception as e:
            logger.error(f"Error in spaCy NER detection: {e}")
        
        return candidates
    
    def _map_spacy_label(self, spacy_label: str) -> Optional[EntityType]:
        """Map spaCy entity labels to our EntityType enum"""
        return self._entity_mapping.get(spacy_label)
    
    def _calculate_confidence(self, ent: Span, doc: Doc) -> float:
        """Calculate confidence score for spaCy entities"""
        # Base confidence for spaCy entities
        base_confidence = 0.75
        
        # Boost confidence based on various factors
        confidence_boost = 0.0
        
        # Length factor (longer entities are often more reliable)
        if len(ent.text) > 2:
            confidence_boost += 0.05
        
        # Title case boost for PERSON and ORG
        if ent.label_ in ["PERSON", "ORG"] and ent.text.istitle():
            confidence_boost += 0.10
        
        # Context-based boost
        if self._has_strong_context(ent, doc):
            confidence_boost += 0.10
        
        # All caps penalty (might be acronym or noise)
        if ent.text.isupper() and len(ent.text) > 1:
            confidence_boost -= 0.05
        
        return min(base_confidence + confidence_boost, 1.0)
    
    def _has_strong_context(self, ent: Span, doc: Doc) -> bool:
        """Check if entity has strong contextual indicators"""
        # Look for common prefixes/suffixes
        context_window = 3
        start_idx = max(0, ent.start - context_window)
        end_idx = min(len(doc), ent.end + context_window)
        
        context_tokens = [token.text.lower() for token in doc[start_idx:end_idx]]
        
        person_indicators = ["mr", "mrs", "ms", "dr", "prof", "ceo", "manager", "director"]
        org_indicators = ["inc", "llc", "corp", "company", "ltd", "university", "college"]
        location_indicators = ["in", "at", "from", "to", "near", "city", "state", "country"]
        
        if ent.label_ == "PERSON":
            return any(indicator in context_tokens for indicator in person_indicators)
        elif ent.label_ == "ORG":
            return any(indicator in context_tokens for indicator in org_indicators)
        elif ent.label_ in ["GPE", "LOC"]:
            return any(indicator in context_tokens for indicator in location_indicators)
        
        return False
    
    async def _detect_custom_patterns(self, doc: Doc) -> List[DetectionCandidate]:
        """Detect additional patterns using spaCy's linguistic features"""
        candidates = []
        
        # Detect potential names using POS tags and dependency parsing
        for sent in doc.sents:
            for token in sent:
                # Potential person names (proper nouns with specific patterns)
                if (token.pos_ == "PROPN" and 
                    token.ent_type_ == "" and  # Not already tagged by NER
                    self._looks_like_name(token)):
                    
                    candidate = DetectionCandidate(
                        id=None,
                        type=EntityType.PERSON,
                        text=token.text,
                        bbox=None,
                        confidence=0.6,  # Lower confidence for pattern-based detection
                        start_char=token.idx,
                        end_char=token.idx + len(token.text),
                        source=f"{self.name}_patterns",
                        metadata={
                            "detection_method": "pos_pattern",
                            "pos": token.pos_,
                            "dep": token.dep_,
                            "is_title": token.text.istitle()
                        }
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _looks_like_name(self, token) -> bool:
        """Heuristic to identify potential names"""
        text = token.text
        
        # Basic checks
        if len(text) < 2 or not text.istitle():
            return False
        
        # Common name patterns
        if text.isalpha() and len(text) >= 2:
            # Check if it's not a common word
            common_words = {"The", "This", "That", "When", "Where", "What", "How"}
            return text not in common_words
        
        return False
    
    def get_supported_types(self) -> List[EntityType]:
        """Return supported entity types"""
        return list(self._entity_mapping.values())
    
    def add_custom_entity_ruler(self, patterns: List[dict]):
        """Add custom entity patterns to spaCy pipeline"""
        if not self.nlp:
            return False
        
        try:
            # Add entity ruler if not already present
            if "entity_ruler" not in self.nlp.pipe_names:
                ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            else:
                ruler = self.nlp.get_pipe("entity_ruler")
            
            ruler.add_patterns(patterns)
            return True
        except Exception as e:
            logger.error(f"Error adding custom entity patterns: {e}")
            return False

class EnhancedSpacyDetector(SpacyNERDetector):
    """Enhanced spaCy detector with additional linguistic analysis"""
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        super().__init__(model_name)
        self.name = "enhanced_spacy"
        self._setup_custom_components()
    
    def _setup_custom_components(self):
        """Setup custom spaCy pipeline components"""
        if not self.nlp:
            return
        
        # Add custom patterns for PII detection
        patterns = [
            {"label": "PERSON", "pattern": [{"LOWER": "mr"}, {"IS_TITLE": True}]},
            {"label": "PERSON", "pattern": [{"LOWER": "mrs"}, {"IS_TITLE": True}]},
            {"label": "PERSON", "pattern": [{"LOWER": "dr"}, {"IS_TITLE": True}]},
            {"label": "ORGANIZATION", "pattern": [{"IS_TITLE": True}, {"LOWER": "university"}]},
            {"label": "ORGANIZATION", "pattern": [{"IS_TITLE": True}, {"LOWER": "college"}]},
            {"label": "ORGANIZATION", "pattern": [{"IS_TITLE": True}, {"LOWER": "inc"}]},
        ]
        
        self.add_custom_entity_ruler(patterns)
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Enhanced detection with additional analysis"""
        candidates = await super().detect(text, **kwargs)
        
        if not self.nlp:
            return candidates
        
        # Additional analysis
        doc = self.nlp(text)
        
        # Detect potential sensitive information using dependency parsing
        sensitive_candidates = await self._analyze_dependencies(doc)
        candidates.extend(sensitive_candidates)
        
        # Detect potential addresses using compound detection
        address_candidates = await self._detect_addresses(doc)
        candidates.extend(address_candidates)
        
        return candidates
    
    async def _analyze_dependencies(self, doc: Doc) -> List[DetectionCandidate]:
        """Analyze dependency trees for sensitive information"""
        candidates = []
        
        for sent in doc.sents:
            for token in sent:
                # Look for patterns like "My name is John" or "Contact: john@email.com"
                if token.lemma_.lower() in ["name", "email", "phone", "address", "contact"]:
                    # Find the associated entity
                    for child in token.children:
                        if child.pos_ in ["PROPN", "NOUN"] or "@" in child.text:
                            entity_type = self._infer_type_from_context(token.lemma_.lower())
                            if entity_type:
                                candidate = DetectionCandidate(
                                    id=None,
                                    type=entity_type,
                                    text=child.text,
                                    bbox=None,
                                    confidence=0.7,
                                    start_char=child.idx,
                                    end_char=child.idx + len(child.text),
                                    source=f"{self.name}_dependency",
                                    metadata={
                                        "detection_method": "dependency_parsing",
                                        "context_word": token.text,
                                        "dependency": child.dep_
                                    }
                                )
                                candidates.append(candidate)
        
        return candidates
    
    def _infer_type_from_context(self, context: str) -> Optional[EntityType]:
        """Infer entity type from context words"""
        context_mapping = {
            "name": EntityType.PERSON,
            "email": EntityType.EMAIL,
            "phone": EntityType.PHONE,
            "address": EntityType.ADDRESS,
            "contact": EntityType.PERSON
        }
        return context_mapping.get(context.lower())
    
    async def _detect_addresses(self, doc: Doc) -> List[DetectionCandidate]:
        """Detect addresses using compound noun phrases"""
        candidates = []
        
        for chunk in doc.noun_chunks:
            # Look for address-like patterns
            if self._looks_like_address(chunk):
                candidate = DetectionCandidate(
                    id=None,
                    type=EntityType.ADDRESS,
                    text=chunk.text,
                    bbox=None,
                    confidence=0.65,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    source=f"{self.name}_address",
                    metadata={
                        "detection_method": "noun_chunk_analysis",
                        "chunk_label": chunk.label_,
                        "root": chunk.root.text
                    }
                )
                candidates.append(candidate)
        
        return candidates
    
    def _looks_like_address(self, chunk: Span) -> bool:
        """Heuristic to identify potential addresses"""
        text = chunk.text.lower()
        address_indicators = ["street", "st", "avenue", "ave", "road", "rd", "boulevard", 
                            "blvd", "lane", "ln", "drive", "dr", "suite", "apt", "floor"]
        
        # Check if chunk contains address indicators
        return any(indicator in text for indicator in address_indicators)