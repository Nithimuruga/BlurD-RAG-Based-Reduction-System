from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

class EntityType(Enum):
    """Enumeration of supported entity types"""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    PAN = "pan"
    CREDIT_CARD = "credit_card"
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    ADDRESS = "address"
    IBAN = "iban"
    IP_ADDRESS = "ip_address"
    URL = "url"
    CUSTOM = "custom"

@dataclass
class BoundingBox:
    """Bounding box coordinates for detected entities"""
    x: float
    y: float
    width: float
    height: float
    page: int = 0

@dataclass
class DetectionCandidate:
    """Represents a detected PII candidate"""
    id: str
    type: EntityType
    text: str
    bbox: Optional[BoundingBox]
    confidence: float
    start_char: int
    end_char: int
    source: str  # Which detector found this
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.metadata is None:
            self.metadata = {}

class BaseDetector(ABC):
    """Abstract base class for all detectors"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    @abstractmethod
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Detect PII entities in the given text"""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[EntityType]:
        """Return list of entity types this detector can identify"""
        pass

class DetectionPipeline:
    """Main detection pipeline that orchestrates multiple detectors"""
    
    def __init__(self):
        self.detectors: List[BaseDetector] = []
        self.confidence_threshold = 0.5
        self.merge_overlap_threshold = 0.8
    
    def add_detector(self, detector: BaseDetector):
        """Add a detector to the pipeline"""
        self.detectors.append(detector)
    
    def remove_detector(self, detector_name: str):
        """Remove a detector by name"""
        self.detectors = [d for d in self.detectors if d.name != detector_name]
    
    async def process(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Process text through all detectors and merge results"""
        all_candidates = []
        
        # Run all detectors
        for detector in self.detectors:
            if detector.enabled:
                try:
                    candidates = await detector.detect(text, **kwargs)
                    all_candidates.extend(candidates)
                except Exception as e:
                    print(f"Error in detector {detector.name}: {e}")
        
        # Merge overlapping candidates
        merged_candidates = self._merge_candidates(all_candidates)
        
        # Filter by confidence threshold
        filtered_candidates = [
            c for c in merged_candidates 
            if c.confidence >= self.confidence_threshold
        ]
        
        # Sort by confidence (highest first)
        filtered_candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        return filtered_candidates
    
    def _merge_candidates(self, candidates: List[DetectionCandidate]) -> List[DetectionCandidate]:
        """Merge overlapping candidates from different detectors"""
        if not candidates:
            return []
        
        # Group by text position
        sorted_candidates = sorted(candidates, key=lambda x: x.start_char)
        merged = []
        
        for candidate in sorted_candidates:
            merged_with_existing = False
            
            for i, existing in enumerate(merged):
                overlap = self._calculate_overlap(candidate, existing)
                
                if overlap >= self.merge_overlap_threshold:
                    # Merge with existing candidate
                    merged_candidate = self._merge_two_candidates(existing, candidate)
                    merged[i] = merged_candidate
                    merged_with_existing = True
                    break
            
            if not merged_with_existing:
                merged.append(candidate)
        
        return merged
    
    def _calculate_overlap(self, c1: DetectionCandidate, c2: DetectionCandidate) -> float:
        """Calculate overlap ratio between two candidates"""
        start1, end1 = c1.start_char, c1.end_char
        start2, end2 = c2.start_char, c2.end_char
        
        # Calculate intersection
        intersection_start = max(start1, start2)
        intersection_end = min(end1, end2)
        
        if intersection_start >= intersection_end:
            return 0.0
        
        intersection_length = intersection_end - intersection_start
        
        # Calculate union
        union_start = min(start1, start2)
        union_end = max(end1, end2)
        union_length = union_end - union_start
        
        return intersection_length / union_length if union_length > 0 else 0.0
    
    def _merge_two_candidates(self, c1: DetectionCandidate, c2: DetectionCandidate) -> DetectionCandidate:
        """Merge two overlapping candidates"""
        # Use the candidate with higher confidence as base
        base = c1 if c1.confidence >= c2.confidence else c2
        other = c2 if c1.confidence >= c2.confidence else c1
        
        # Merge text spans
        start_char = min(c1.start_char, c2.start_char)
        end_char = max(c1.end_char, c2.end_char)
        
        # Combine confidence scores (weighted average)
        total_length = (c1.end_char - c1.start_char) + (c2.end_char - c2.start_char)
        c1_weight = (c1.end_char - c1.start_char) / total_length
        c2_weight = (c2.end_char - c2.start_char) / total_length
        
        merged_confidence = (c1.confidence * c1_weight) + (c2.confidence * c2_weight)
        
        # Create merged candidate
        merged = DetectionCandidate(
            id=str(uuid.uuid4()),
            type=base.type,
            text=base.text,  # Use base candidate's text
            bbox=base.bbox or other.bbox,
            confidence=min(merged_confidence, 1.0),
            start_char=start_char,
            end_char=end_char,
            source=f"{base.source}+{other.source}",
            metadata={
                "merged_from": [base.id, other.id],
                "sources": [base.source, other.source],
                "original_confidences": [base.confidence, other.confidence]
            }
        )
        
        return merged