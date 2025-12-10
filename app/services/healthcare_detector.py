"""
Healthcare-specific PII detector.
Detects healthcare-related PII using specialized patterns and rules.
"""

from typing import List, Dict, Any, Optional
import re
import logging
from app.services.detection_pipeline import BaseDetector, DetectionCandidate, EntityType
from app.schemas.pii_schemas import PIIType, RiskLevel

logger = logging.getLogger(__name__)

class HealthcareDetector(BaseDetector):
    """
    Healthcare-specific PII detector for medical identifiers and information
    """
    
    def __init__(self):
        super().__init__("healthcare")
        self._initialize_patterns()
        
    def get_supported_types(self) -> List[Any]:
        """Return list of entity types this detector can identify"""
        return [
            PIIType.HEALTH_INSURANCE_ID,
            PIIType.MEDICAL_RECORD_NUMBER,
            PIIType.PATIENT_ID
        ]
    
    def _initialize_patterns(self):
        """Initialize healthcare-specific patterns"""
        # Medical record number patterns
        self.mrn_patterns = [
            r'\bMRN\s*[:#]?\s*(\d{5,10})\b',
            r'\bMedical Record\s*[:#]?\s*(\d{5,10})\b',
            r'\bRecord\s*[:#]?\s*(\d{5,10})\b'
        ]
        
        # Health insurance ID patterns
        self.insurance_patterns = [
            r'\bInsurance ID\s*[:#]?\s*([A-Z0-9]{6,15})\b',
            r'\bPolicy\s*[:#]?\s*([A-Z0-9]{6,15})\b',
            r'\bGroup\s*[:#]?\s*([A-Z0-9]{5,10})\b',
            r'\bMember ID\s*[:#]?\s*([A-Z0-9]{6,15})\b',
            r'\bBCBS\s*[:#]?\s*([A-Z0-9]{6,15})\b',
            r'\bMedicare\s*[:#]?\s*([0-9]{6,12})\b',
            r'\bMedicaid\s*[:#]?\s*([0-9]{6,12})\b'
        ]
        
        # Patient ID patterns
        self.patient_patterns = [
            r'\bPatient ID\s*[:#]?\s*([A-Z0-9]{5,15})\b',
            r'\bPatient\s*[:#]?\s*([A-Z0-9]{5,10})\b',
            r'\bPT\s*[:#]?\s*([A-Z0-9]{5,10})\b'
        ]
        
        # Medication-related patterns (for context)
        self.medication_patterns = [
            r'\b\d+\s*mg\b',
            r'\b\d+\s*ml\b',
            r'\b\d+\s*mcg\b'
        ]
        
        # Common medical test results
        self.test_patterns = [
            r'\bHbA1c[:=\s]+(\d+\.?\d*)\s*%?\b',
            r'\bHemoglobin[:=\s]+(\d+\.?\d*)\s*g/dL\b',
            r'\bWhite Blood Cell[:=\s]+(\d+\.?\d*)\s*K/uL\b',
            r'\bCholesterol[:=\s]+(\d+\.?\d*)\s*mg/dL\b',
            r'\bBP[:=\s]+(\d{2,3})/(\d{2,3})\b',  # Blood pressure
            r'\bBlood Pressure[:=\s]+(\d{2,3})/(\d{2,3})\b'
        ]
        
        # Diagnosis codes (ICD-10, etc.)
        self.diagnosis_patterns = [
            r'\b[A-Z]\d{2}\.\d{1,2}\b',  # ICD-10 format
            r'\bICD-10\s*:?\s*([A-Z]\d{2}\.\d{1,2})\b',
            r'\bDiagnosis\s*:?\s*([A-Z]\d{2}\.\d{1,2})\b',
            r'\bDX\s*:?\s*([A-Z]\d{2}\.\d{1,2})\b'
        ]
        
        # CPT codes (medical procedure codes)
        self.cpt_patterns = [
            r'\bCPT\s*:?\s*(\d{5})\b',
            r'\bProcedure\s*:?\s*(\d{5})\b'
        ]
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """
        Detect healthcare-related PII
        
        Args:
            text: Text to analyze
            **kwargs: Additional parameters
                
        Returns:
            List of detected PII candidates
        """
        if not text:
            return []
        
        candidates = []
        
        # Detect medical record numbers
        for pattern in self.mrn_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start, end = match.span()
                matched_text = text[start:end]
                
                # Extract just the identifier part if we can
                if match.groups():
                    id_text = match.group(1)
                    # Adjust start position to point to the actual ID
                    id_start = text.find(id_text, start)
                    id_end = id_start + len(id_text)
                else:
                    id_text = matched_text
                    id_start, id_end = start, end
                
                candidates.append(DetectionCandidate(
                    id=None,
                    type=PIIType.MEDICAL_RECORD_NUMBER,
                    text=id_text,
                    bbox=None,
                    confidence=0.9,
                    start_char=id_start,
                    end_char=id_end,
                    source=self.name,
                    metadata={
                        "full_match": matched_text,
                        "detection_method": "healthcare_regex",
                        "context": self._extract_context(text, start, end)
                    }
                ))
        
        # Detect health insurance IDs
        for pattern in self.insurance_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start, end = match.span()
                matched_text = text[start:end]
                
                # Extract just the identifier part if we can
                if match.groups():
                    id_text = match.group(1)
                    # Adjust start position to point to the actual ID
                    id_start = text.find(id_text, start)
                    id_end = id_start + len(id_text)
                else:
                    id_text = matched_text
                    id_start, id_end = start, end
                
                candidates.append(DetectionCandidate(
                    id=None,
                    type=PIIType.HEALTH_INSURANCE_ID,
                    text=id_text,
                    bbox=None,
                    confidence=0.85,
                    start_char=id_start,
                    end_char=id_end,
                    source=self.name,
                    metadata={
                        "full_match": matched_text,
                        "detection_method": "healthcare_regex",
                        "context": self._extract_context(text, start, end)
                    }
                ))
        
        # Detect patient IDs
        for pattern in self.patient_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start, end = match.span()
                matched_text = text[start:end]
                
                # Extract just the identifier part if we can
                if match.groups():
                    id_text = match.group(1)
                    # Adjust start position to point to the actual ID
                    id_start = text.find(id_text, start)
                    id_end = id_start + len(id_text)
                else:
                    id_text = matched_text
                    id_start, id_end = start, end
                
                candidates.append(DetectionCandidate(
                    id=None,
                    type=PIIType.PATIENT_ID,
                    text=id_text,
                    bbox=None,
                    confidence=0.9,
                    start_char=id_start,
                    end_char=id_end,
                    source=self.name,
                    metadata={
                        "full_match": matched_text,
                        "detection_method": "healthcare_regex",
                        "context": self._extract_context(text, start, end)
                    }
                ))
        
        # Detect diagnosis codes
        for pattern in self.diagnosis_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start, end = match.span()
                matched_text = text[start:end]
                
                # Extract just the identifier part if we can
                if match.groups():
                    id_text = match.group(1)
                    # Adjust start position to point to the actual ID
                    id_start = text.find(id_text, start)
                    id_end = id_start + len(id_text)
                else:
                    id_text = matched_text
                    id_start, id_end = start, end
                
                candidates.append(DetectionCandidate(
                    id=None,
                    type=PIIType.CUSTOM,
                    text=id_text,
                    bbox=None,
                    confidence=0.85,
                    start_char=id_start,
                    end_char=id_end,
                    source=self.name,
                    metadata={
                        "full_match": matched_text,
                        "detection_method": "healthcare_regex",
                        "context": self._extract_context(text, start, end),
                        "custom_type": "diagnosis_code"
                    }
                ))
        
        return candidates
    
    def _extract_context(self, text: str, start: int, end: int, context_chars: int = 30) -> str:
        """Extract context around a match"""
        text_len = len(text)
        context_start = max(0, start - context_chars)
        context_end = min(text_len, end + context_chars)
        
        prefix = "..." if context_start > 0 else ""
        suffix = "..." if context_end < text_len else ""
        
        context = prefix + text[context_start:start] + "**" + text[start:end] + "**" + text[context_end:context_end] + suffix
        return context