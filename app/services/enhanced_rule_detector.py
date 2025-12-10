"""
Enhanced rule-based PII detection module.
Supports all PII types defined in the schema and uses configurable regex patterns.
"""

import re
from typing import List, Dict, Pattern, Optional, Any
import logging
from pathlib import Path
import json
import os

from app.services.detection_pipeline import BaseDetector, DetectionCandidate, EntityType
from app.schemas.pii_schemas import PIIType, RiskLevel
from app.schemas.pii_definitions import DEFAULT_PII_TYPE_DEFINITIONS

logger = logging.getLogger(__name__)

class RegexPattern:
    """Holds a regex pattern with metadata"""
    def __init__(self, pattern: str, pii_type: PIIType, confidence: float = 0.9, flags: int = 0, 
                 name: str = None, description: str = None):
        self.pattern = re.compile(pattern, flags)
        self.pii_type = pii_type
        self.confidence = confidence
        self.name = name or f"Pattern for {pii_type}"
        self.description = description or ""
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "pattern": self.pattern.pattern,
            "pii_type": self.pii_type,
            "confidence": self.confidence,
            "flags": self.pattern.flags,
            "name": self.name,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create RegexPattern from dictionary"""
        return cls(
            pattern=data["pattern"],
            pii_type=data["pii_type"],
            confidence=data["confidence"],
            flags=data["flags"],
            name=data.get("name"),
            description=data.get("description")
        )

class EnhancedRuleBasedDetector(BaseDetector):
    """Enhanced rule-based detector using regex patterns for PII types"""
    
    def __init__(self, custom_patterns_file: str = None):
        super().__init__("enhanced_rule_based")
        self.patterns = self._initialize_patterns()
        
        # Load custom patterns if specified
        if custom_patterns_file:
            self._load_custom_patterns(custom_patterns_file)
            
    def get_supported_types(self) -> List[Any]:
        """Return list of entity types this detector can identify"""
        # Get unique PII types from all patterns
        return list(set(pattern.pii_type for pattern in self.patterns))
    
    def _initialize_patterns(self) -> List[RegexPattern]:
        """Initialize regex patterns for all PII types"""
        patterns = []
        
        # Build patterns from the default PII type definitions
        for pii_type, definition in DEFAULT_PII_TYPE_DEFINITIONS.items():
            if definition.regex_patterns:
                for pattern in definition.regex_patterns:
                    patterns.append(RegexPattern(
                        pattern=pattern,
                        pii_type=pii_type,
                        confidence=definition.detection_confidence_threshold,
                        flags=re.IGNORECASE  # Default to case-insensitive
                    ))
        
        # Add additional patterns that aren't in the default definitions
        
        # Credit card patterns with validation
        cc_pattern = r'(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})'
        patterns.append(RegexPattern(cc_pattern, PIIType.CREDIT_CARD, 0.95))
        
        # Credit cards with separators
        cc_sep_pattern = r'(?:4[0-9]{3}|5[1-5][0-9]{2}|6(?:011|5[0-9]{2})|3[47][0-9]{2})[ -]?[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}'
        patterns.append(RegexPattern(cc_sep_pattern, PIIType.CREDIT_CARD, 0.92))
        
        # U.S. Passport
        passport_pattern = r'\b[A-Z][0-9]{8}\b'
        patterns.append(RegexPattern(passport_pattern, PIIType.PASSPORT, 0.9))
        
        # International passport formats
        int_passport_pattern = r'\b[A-Z]{1,2}[0-9]{6,9}\b'
        patterns.append(RegexPattern(int_passport_pattern, PIIType.PASSPORT, 0.85))
        
        # U.S. Driver's License (varies by state)
        dl_pattern = r'\b[A-Z][0-9]{7}\b'
        patterns.append(RegexPattern(dl_pattern, PIIType.DRIVERS_LICENSE, 0.85))
        
        # Dates in various formats
        date_patterns = [
            r'\b(0?[1-9]|1[0-2])[\/\-\.](0?[1-9]|[12][0-9]|3[01])[\/\-\.](19|20)\d{2}\b',  # MM/DD/YYYY
            r'\b(0?[1-9]|[12][0-9]|3[01])[\/\-\.](0?[1-9]|1[0-2])[\/\-\.](19|20)\d{2}\b',  # DD/MM/YYYY
            r'\b(19|20)\d{2}[\/\-\.](0?[1-9]|1[0-2])[\/\-\.](0?[1-9]|[12][0-9]|3[01])\b',  # YYYY/MM/DD
        ]
        for pattern in date_patterns:
            patterns.append(RegexPattern(pattern, PIIType.DATE, 0.85))
        
        # Date of birth specific patterns
        dob_patterns = [
            r'\b(?:DOB|Date\s+of\s+Birth)[:;\s]+(0?[1-9]|1[0-2])[\/\-\.](0?[1-9]|[12][0-9]|3[01])[\/\-\.](19|20)\d{2}\b',
            r'\b(?:DOB|Date\s+of\s+Birth)[:;\s]+(0?[1-9]|[12][0-9]|3[01])[\/\-\.](0?[1-9]|1[0-2])[\/\-\.](19|20)\d{2}\b',
        ]
        for pattern in dob_patterns:
            patterns.append(RegexPattern(pattern, PIIType.DATE_OF_BIRTH, 0.95))
        
        # Bank account numbers
        bank_account_pattern = r'\b[0-9]{8,17}\b'
        patterns.append(RegexPattern(bank_account_pattern, PIIType.BANK_ACCOUNT, 0.7))
        
        # IBAN (International Bank Account Number)
        iban_pattern = r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}\b'
        patterns.append(RegexPattern(iban_pattern, PIIType.IBAN, 0.9))
        
        # IP addresses (IPv4)
        ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        patterns.append(RegexPattern(ipv4_pattern, PIIType.IP_ADDRESS, 0.95))
        
        # IP addresses (IPv6)
        ipv6_pattern = r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
        patterns.append(RegexPattern(ipv6_pattern, PIIType.IP_ADDRESS, 0.95))
        
        # URLs
        url_pattern = r'\bhttps?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*\b'
        patterns.append(RegexPattern(url_pattern, PIIType.URL, 0.95))
        
        # GPS coordinates
        gps_pattern = r'\b[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)\b'
        patterns.append(RegexPattern(gps_pattern, PIIType.GPS_COORDINATES, 0.9))
        
        return patterns
    
    def _load_custom_patterns(self, file_path: str):
        """Load custom patterns from a JSON file"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.warning(f"Custom patterns file not found: {file_path}")
                return
                
            with open(file_path, 'r') as f:
                custom_patterns = json.load(f)
                
            for pattern_data in custom_patterns:
                try:
                    # Convert string PIIType to enum if needed
                    if isinstance(pattern_data["pii_type"], str):
                        pattern_data["pii_type"] = PIIType(pattern_data["pii_type"])
                        
                    pattern = RegexPattern.from_dict(pattern_data)
                    self.patterns.append(pattern)
                except Exception as e:
                    logger.warning(f"Failed to load custom pattern: {e}")
            
            logger.info(f"Loaded {len(custom_patterns)} custom patterns from {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to load custom patterns: {e}")
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """
        Detect PII entities using regex patterns
        
        Args:
            text: Text to analyze
            **kwargs: Additional parameters
                - pii_types: List of PIIType to detect (if empty, detect all)
                
        Returns:
            List of detected PII candidates
        """
        if not text:
            return []
            
        candidates = []
        
        # Filter patterns by requested PII types if specified
        requested_types = kwargs.get("pii_types", [])
        patterns = self.patterns
        if requested_types:
            patterns = [p for p in patterns if p.pii_type in requested_types]
        
        # Apply each pattern
        for pattern in patterns:
            matches = pattern.pattern.finditer(text)
            
            for match in matches:
                start, end = match.span()
                matched_text = text[start:end]
                
                # Skip if empty match or too short
                if not matched_text or len(matched_text) < 2:
                    continue
                
                # Create candidate
                candidate = DetectionCandidate(
                    id=None,  # Will be assigned by the pipeline
                    type=pattern.pii_type,
                    text=matched_text,
                    bbox=None,
                    confidence=pattern.confidence,
                    start_char=start,
                    end_char=end,
                    source=self.name,
                    metadata={
                        "pattern_name": pattern.name,
                        "detection_method": "regex"
                    }
                )
                
                # Validate the candidate if possible
                valid, validation_info = self._validate_candidate(candidate)
                candidate.metadata["validation"] = validation_info
                
                # Adjust confidence based on validation
                if valid is False:  # Only if definitely invalid
                    candidate.confidence *= 0.5
                elif valid is True:  # Only if definitely valid
                    candidate.confidence = min(candidate.confidence * 1.2, 1.0)
                
                candidates.append(candidate)
        
        return candidates
    
    def _validate_candidate(self, candidate: DetectionCandidate) -> tuple:
        """
        Validate a detected PII candidate
        
        Args:
            candidate: The detection candidate
            
        Returns:
            tuple of (is_valid, validation_info)
        """
        pii_type = candidate.type
        text = candidate.text
        
        # Skip validation if text is too short
        if not text or len(text) < 2:
            return None, {"valid": None, "reason": "Text too short"}
        
        # Validate based on PII type
        if pii_type == PIIType.CREDIT_CARD:
            return self._validate_credit_card(text)
        elif pii_type == PIIType.EMAIL:
            return self._validate_email(text)
        elif pii_type == PIIType.SSN:
            return self._validate_ssn(text)
        elif pii_type == PIIType.DATE:
            return self._validate_date(text)
        
        # No specific validation for this type
        return None, {"valid": None, "reason": "No validation available"}
    
    def _validate_credit_card(self, text: str) -> tuple:
        """
        Validate a credit card number using the Luhn algorithm
        
        Args:
            text: Credit card number
            
        Returns:
            tuple of (is_valid, validation_info)
        """
        # Remove spaces, dashes, etc.
        digits = ''.join(c for c in text if c.isdigit())
        
        if len(digits) < 13 or len(digits) > 19:
            return False, {"valid": False, "reason": "Invalid length"}
        
        # Luhn algorithm
        try:
            check = 0
            digits_reversed = digits[::-1]
            
            for i, digit in enumerate(digits_reversed):
                n = int(digit)
                if i % 2 == 1:  # Odd position (0-indexed from right)
                    n *= 2
                    if n > 9:
                        n -= 9
                check += n
                
            if check % 10 == 0:
                return True, {"valid": True, "method": "luhn"}
            else:
                return False, {"valid": False, "reason": "Failed Luhn check"}
                
        except Exception as e:
            return False, {"valid": False, "reason": f"Validation error: {e}"}
    
    def _validate_email(self, text: str) -> tuple:
        """
        Validate an email address
        
        Args:
            text: Email address
            
        Returns:
            tuple of (is_valid, validation_info)
        """
        # Basic format check
        if '@' not in text or '.' not in text.split('@')[1]:
            return False, {"valid": False, "reason": "Invalid format"}
        
        # Check for common fake/test domains
        domain = text.split('@')[1].lower()
        test_domains = ['example.com', 'test.com', 'domain.com']
        if domain in test_domains:
            return False, {"valid": False, "reason": "Test domain"}
        
        return True, {"valid": True, "method": "format"}
    
    def _validate_ssn(self, text: str) -> tuple:
        """
        Validate a Social Security Number
        
        Args:
            text: SSN
            
        Returns:
            tuple of (is_valid, validation_info)
        """
        # Remove spaces, dashes, etc.
        digits = ''.join(c for c in text if c.isdigit())
        
        if len(digits) != 9:
            return False, {"valid": False, "reason": "Invalid length"}
        
        # Check for invalid SSNs
        if digits.startswith('000') or digits.startswith('666'):
            return False, {"valid": False, "reason": "Invalid first group"}
        
        if digits.startswith('9'):
            return False, {"valid": False, "reason": "Invalid first digit"}
        
        if digits[3:5] == '00':
            return False, {"valid": False, "reason": "Invalid second group"}
        
        if digits[5:] == '0000':
            return False, {"valid": False, "reason": "Invalid third group"}
        
        return True, {"valid": True, "method": "format"}
    
    def _validate_date(self, text: str) -> tuple:
        """
        Validate a date
        
        Args:
            text: Date string
            
        Returns:
            tuple of (is_valid, validation_info)
        """
        from datetime import datetime
        
        # Try common date formats
        formats = [
            "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(text, fmt)
                return True, {"valid": True, "method": "format", "parsed_date": dt.isoformat()}
            except ValueError:
                continue
        
        return False, {"valid": False, "reason": "Failed to parse date"}