from typing import List, Dict, Any, Optional
import asyncio
import logging
from app.services.detection_pipeline import DetectionPipeline, DetectionCandidate, EntityType
from app.services.rule_based_detector import RuleBasedDetector, CustomRuleDetector
from app.services.enhanced_rule_detector import EnhancedRuleBasedDetector
from app.services.healthcare_detector import HealthcareDetector
from app.services.financial_detector import FinancialDetector
from app.services.spacy_detector import SpacyNERDetector, EnhancedSpacyDetector
from app.services.huggingface_detector import HuggingFaceDetector, EnsembleTransformerDetector
from app.services.rag_detector import RAGDetector
from app.utils.serialization import convert_numpy_types
from app.services.text_preprocessing import TextPreprocessor, ProcessedDocument
import json

logger = logging.getLogger(__name__)

class DetectionOrchestrator:
    """Main orchestrator for PII detection pipeline"""
    
    def __init__(self):
        self.pipeline = DetectionPipeline()
        self._initialized = False
        self.text_preprocessor = TextPreprocessor()
        self.detection_stats = {
            "total_detections": 0,
            "by_detector": {},
            "by_entity_type": {},
            "confidence_distribution": {}
        }
    
    async def initialize(self):
        """Initialize all detectors in the pipeline"""
        if self._initialized:
            return
        
        try:
            # Initialize detectors in order of reliability
            
            # 1. Enhanced rule-based detector (with expanded PII types)
            enhanced_rule_detector = EnhancedRuleBasedDetector()
            self.pipeline.add_detector(enhanced_rule_detector)
            logger.info("Added enhanced rule-based detector")
            
            # 2. Domain-specific detectors
            healthcare_detector = HealthcareDetector()
            self.pipeline.add_detector(healthcare_detector)
            logger.info("Added healthcare detector")
            
            financial_detector = FinancialDetector()
            self.pipeline.add_detector(financial_detector)
            logger.info("Added financial detector")
            
            # 3. Legacy rule-based detector (for backward compatibility)
            rule_detector = RuleBasedDetector()
            self.pipeline.add_detector(rule_detector)
            logger.info("Added legacy rule-based detector")
            
            # 4. Custom rules detector
            custom_detector = CustomRuleDetector()
            self.pipeline.add_detector(custom_detector)
            logger.info("Added custom rules detector")
            
            # 3. spaCy NER detector
            try:
                spacy_detector = EnhancedSpacyDetector()
                if spacy_detector.enabled:
                    self.pipeline.add_detector(spacy_detector)
                    logger.info("Added enhanced spaCy detector")
                else:
                    # Fallback to basic spaCy
                    basic_spacy = SpacyNERDetector()
                    if basic_spacy.enabled:
                        self.pipeline.add_detector(basic_spacy)
                        logger.info("Added basic spaCy detector")
            except Exception as e:
                logger.warning(f"Failed to initialize spaCy detector: {e}")
            
            # 4. Hugging Face transformer detector
            try:
                hf_detector = HuggingFaceDetector()
                if hf_detector.enabled:
                    self.pipeline.add_detector(hf_detector)
                    logger.info("Added Hugging Face detector")
                
                # Optionally add ensemble detector
                ensemble_detector = EnsembleTransformerDetector()
                if ensemble_detector.enabled:
                    self.pipeline.add_detector(ensemble_detector)
                    logger.info("Added ensemble transformer detector")
                    
            except Exception as e:
                logger.warning(f"Failed to initialize Hugging Face detectors: {e}")
            
            # 5. RAG-enhanced detector (most sophisticated)
            try:
                rag_detector = RAGDetector()
                await rag_detector.initialize()
                self.pipeline.add_detector(rag_detector)
                logger.info("Added RAG detector")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG detector: {e}")
            
            # Configure pipeline settings
            self.pipeline.confidence_threshold = 0.5
            self.pipeline.merge_overlap_threshold = 0.7
            
            self._initialized = True
            logger.info(f"Detection pipeline initialized with {len(self.pipeline.detectors)} detectors")
            
        except Exception as e:
            logger.error(f"Failed to initialize detection pipeline: {e}")
            raise
    
    async def detect_pii(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Main entry point for PII detection
        
        Args:
            text: Text to analyze
            **kwargs: Additional parameters (file_path, user_context, etc.)
                - preprocess: bool = True, whether to preprocess the text
                - preprocessing_steps: List[str], specific preprocessing steps to apply
                - pii_types: List[PIIType], specific PII types to detect
                - compliance_frameworks: List[ComplianceFramework], frameworks to check compliance against
        
        Returns:
            Dictionary containing detected candidates and metadata
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get preprocessing options
            preprocess = kwargs.get("preprocess", True)
            preprocessing_steps = kwargs.get("preprocessing_steps")
            
            # Original text for reference
            original_text = text
            processed_doc = None
            
            # Apply preprocessing if enabled
            if preprocess:
                metadata = {
                    "source": kwargs.get("source", "unknown"),
                    "file_path": kwargs.get("file_path"),
                    "file_id": kwargs.get("file_id"),
                }
                
                processed_doc = await self.text_preprocessor.preprocess(text, steps=preprocessing_steps, metadata=metadata)
                text = processed_doc.processed_text
                
                # Add preprocessing metadata to kwargs
                kwargs["preprocessing_metadata"] = processed_doc.metadata
                kwargs["processed_document"] = processed_doc
            
            # Run detection pipeline
            candidates = await self.pipeline.process(text, **kwargs)
            
            # Map positions back to original text if preprocessing was applied
            if processed_doc:
                for candidate in candidates:
                    orig_start, orig_end = processed_doc.map_range(candidate.start_char, candidate.end_char)
                    if orig_start >= 0 and orig_end >= 0:
                        candidate.metadata["processed_position"] = {
                            "start": candidate.start_char,
                            "end": candidate.end_char
                        }
                        candidate.start_char = orig_start
                        candidate.end_char = orig_end
                        # Update the text to the original text
                        candidate.text = original_text[orig_start:orig_end]
            
            # Post-process and enhance candidates
            enhanced_candidates = await self._enhance_candidates(candidates, original_text, **kwargs)
            
            # Update statistics
            self._update_stats(enhanced_candidates)
            
            # Generate detection report
            report = self._generate_report(enhanced_candidates, original_text, **kwargs)
            
            # Add preprocessing info if available
            if processed_doc:
                report["preprocessing"] = processed_doc.metadata
            
            return report
            
        except Exception as e:
            logger.error(f"Error during PII detection: {e}")
            return {
                "success": False,
                "error": str(e),
                "candidates": [],
                "summary": {}
            }
    
    async def _enhance_candidates(self, candidates: List[DetectionCandidate], 
                                text: str, **kwargs) -> List[DetectionCandidate]:
        """Enhance candidates with additional metadata and validation"""
        enhanced = []
        
        for candidate in candidates:
            # Add contextual information
            candidate.metadata["context"] = self._extract_context(candidate, text)
            
            # Add risk assessment
            candidate.metadata["risk_level"] = self._assess_risk(candidate)
            
            # Add validation flags
            candidate.metadata["validation"] = await self._validate_candidate(candidate, text)
            
            # Adjust confidence based on enhancements
            candidate.confidence = self._adjust_confidence(candidate)
            
            enhanced.append(candidate)
        
        return enhanced
    
    def _extract_context(self, candidate: DetectionCandidate, text: str, window: int = 50) -> Dict[str, str]:
        """Extract context around detected entity"""
        start = max(0, candidate.start_char - window)
        end = min(len(text), candidate.end_char + window)
        
        return {
            "before": text[start:candidate.start_char],
            "entity": text[candidate.start_char:candidate.end_char],
            "after": text[candidate.end_char:end],
            "full_context": text[start:end]
        }
    
    def _assess_risk(self, candidate: DetectionCandidate) -> str:
        """Assess risk level of detected PII"""
        risk_levels = {
            EntityType.SSN: "critical",
            EntityType.CREDIT_CARD: "critical",
            EntityType.PAN: "critical",
            EntityType.PHONE: "high",
            EntityType.EMAIL: "high",
            EntityType.PERSON: "high",
            EntityType.ADDRESS: "medium",
            EntityType.ORGANIZATION: "low",
            EntityType.DATE: "medium",
            EntityType.LOCATION: "low",
            EntityType.IP_ADDRESS: "medium",
            EntityType.URL: "low",
            EntityType.IBAN: "critical",
            EntityType.CUSTOM: "medium"
        }
        
        base_risk = risk_levels.get(candidate.type, "medium")
        
        # Adjust based on confidence
        if candidate.confidence >= 0.9:
            return base_risk
        elif candidate.confidence >= 0.7:
            # Lower risk for lower confidence
            risk_map = {"critical": "high", "high": "medium", "medium": "low", "low": "low"}
            return risk_map.get(base_risk, "medium")
        else:
            return "low"
    
    async def _validate_candidate(self, candidate: DetectionCandidate, text: str) -> Dict[str, Any]:
        """Validate detected candidate using multiple checks"""
        validation = {
            "format_valid": True,
            "context_appropriate": True,
            "not_common_word": True,
            "length_appropriate": True,
            "checksum_valid": None
        }
        
        # Format validation
        if candidate.type == EntityType.EMAIL:
            validation["format_valid"] = "@" in candidate.text and "." in candidate.text
        elif candidate.type == EntityType.PHONE:
            digits = ''.join(filter(str.isdigit, candidate.text))
            validation["format_valid"] = 7 <= len(digits) <= 15
        elif candidate.type == EntityType.SSN:
            digits = ''.join(filter(str.isdigit, candidate.text))
            validation["format_valid"] = len(digits) == 9
        
        # Context validation
        context = candidate.metadata.get("context", {})
        if context:
            full_context = context.get("full_context", "").lower()
            
            # Check for negation words
            negation_words = ["not", "fake", "example", "test", "dummy", "sample"]
            validation["context_appropriate"] = not any(word in full_context for word in negation_words)
        
        # Common word check for names
        if candidate.type == EntityType.PERSON:
            common_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for"}
            validation["not_common_word"] = candidate.text.lower() not in common_words
        
        # Length validation
        validation["length_appropriate"] = 1 <= len(candidate.text) <= 100
        
        return validation
    
    def _adjust_confidence(self, candidate: DetectionCandidate) -> float:
        """Adjust confidence based on validation results"""
        base_confidence = candidate.confidence
        validation = candidate.metadata.get("validation", {})
        
        # Apply penalties for validation failures
        if not validation.get("format_valid", True):
            base_confidence *= 0.7
        
        if not validation.get("context_appropriate", True):
            base_confidence *= 0.5
        
        if not validation.get("not_common_word", True):
            base_confidence *= 0.6
        
        if not validation.get("length_appropriate", True):
            base_confidence *= 0.8
        
        # Apply bonus for high-confidence detectors
        if candidate.source == "rule_based" and candidate.confidence >= 0.9:
            base_confidence = min(base_confidence * 1.1, 1.0)
        
        return round(base_confidence, 3)
    
    def _generate_report(self, candidates: List[DetectionCandidate], 
                        text: str, **kwargs) -> Dict[str, Any]:
        """Generate comprehensive detection report"""
        # Group candidates by type
        by_type = {}
        for candidate in candidates:
            type_name = candidate.type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(candidate)
        
        # Calculate summary statistics
        total_entities = len(candidates)
        high_confidence_count = sum(1 for c in candidates if c.confidence >= 0.8)
        risk_distribution = {}
        
        for candidate in candidates:
            risk = candidate.metadata.get("risk_level", "medium")
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
        
        # Convert candidates to serializable format
        serializable_candidates = []
        for candidate in candidates:
            serializable_candidates.append({
                "id": candidate.id,
                "type": candidate.type.value,
                "text": candidate.text,
                "confidence": candidate.confidence,
                "start_char": candidate.start_char,
                "end_char": candidate.end_char,
                "source": candidate.source,
                "bbox": candidate.bbox.__dict__ if candidate.bbox else None,
                "metadata": candidate.metadata
            })
        
        # Create the report with all data
        report = {
            "success": True,
            "candidates": serializable_candidates,
            "summary": {
                "total_entities": total_entities,
                "high_confidence_entities": high_confidence_count,
                "entity_types": list(by_type.keys()),
                "entities_by_type": {k: len(v) for k, v in by_type.items()},
                "risk_distribution": risk_distribution,
                "text_length": len(text),
                "detection_coverage": round((total_entities / max(len(text.split()), 1)) * 100, 2)
            },
            "metadata": {
                "detectors_used": [d.name for d in self.pipeline.detectors if d.enabled],
                "pipeline_settings": {
                    "confidence_threshold": self.pipeline.confidence_threshold,
                    "merge_threshold": self.pipeline.merge_overlap_threshold
                },
                "processing_info": kwargs
            }
        }
        
        # Add file_id to metadata if provided
        if "file_id" in kwargs:
            report["metadata"]["file_id"] = kwargs["file_id"]
        
        # Convert any NumPy types to Python native types before returning
        return convert_numpy_types(report)
    
    def _update_stats(self, candidates: List[DetectionCandidate]):
        """Update detection statistics"""
        self.detection_stats["total_detections"] += len(candidates)
        
        for candidate in candidates:
            # By detector
            source = candidate.source
            self.detection_stats["by_detector"][source] = \
                self.detection_stats["by_detector"].get(source, 0) + 1
            
            # By entity type
            entity_type = candidate.type.value
            self.detection_stats["by_entity_type"][entity_type] = \
                self.detection_stats["by_entity_type"].get(entity_type, 0) + 1
            
            # Confidence distribution
            conf_bucket = f"{int(candidate.confidence * 10) * 10}%-{int(candidate.confidence * 10) * 10 + 9}%"
            self.detection_stats["confidence_distribution"][conf_bucket] = \
                self.detection_stats["confidence_distribution"].get(conf_bucket, 0) + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics"""
        return self.detection_stats.copy()
    
    def reset_stats(self):
        """Reset detection statistics"""
        self.detection_stats = {
            "total_detections": 0,
            "by_detector": {},
            "by_entity_type": {},
            "confidence_distribution": {}
        }
    
    async def add_custom_rule(self, pattern: str, entity_type: str, confidence: float = 0.8) -> bool:
        """Add custom detection rule"""
        for detector in self.pipeline.detectors:
            if isinstance(detector, CustomRuleDetector):
                try:
                    entity_enum = EntityType(entity_type)
                    return detector.add_pattern(pattern, entity_enum, confidence)
                except ValueError:
                    logger.error(f"Invalid entity type: {entity_type}")
                    return False
        return False
    
    def get_supported_types(self) -> List[str]:
        """Get all supported entity types"""
        return [entity_type.value for entity_type in EntityType]

# Global instance
detection_orchestrator = DetectionOrchestrator()