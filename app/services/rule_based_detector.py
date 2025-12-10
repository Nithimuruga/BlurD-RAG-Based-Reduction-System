import re
from typing import List, Dict, Pattern
from app.services.detection_pipeline import BaseDetector, DetectionCandidate, EntityType

class RegexPattern:
    """Holds a regex pattern with metadata"""
    def __init__(self, pattern: str, entity_type: EntityType, confidence: float = 0.9, flags: int = 0):
        self.pattern = re.compile(pattern, flags)
        self.entity_type = entity_type
        self.confidence = confidence

class RuleBasedDetector(BaseDetector):
    """Rule-based detector using regex patterns for common PII types"""
    
    def __init__(self):
        super().__init__("rule_based")
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> List[RegexPattern]:
        """Initialize regex patterns for various PII types"""
        patterns = []
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        patterns.append(RegexPattern(email_pattern, EntityType.EMAIL, 0.95))
        
        # Phone number patterns (various formats)
        phone_patterns = [
            r'\b\d{3}-\d{3}-\d{4}\b',  # XXX-XXX-XXXX
            r'\b\(\d{3}\)\s?\d{3}-\d{4}\b',  # (XXX) XXX-XXXX
            r'\b\d{3}\.\d{3}\.\d{4}\b',  # XXX.XXX.XXXX
            r'\b\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # +1 XXX XXX XXXX
            r'\b\d{10}\b'  # XXXXXXXXXX
        ]
        for pattern in phone_patterns:
            patterns.append(RegexPattern(pattern, EntityType.PHONE, 0.85))
        
        # Social Security Number (SSN) patterns
        ssn_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # XXX-XX-XXXX
            r'\b\d{3}\s\d{2}\s\d{4}\b',  # XXX XX XXXX
            r'\bSSN:?\s*\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'  # SSN: XXX-XX-XXXX
        ]
        for pattern in ssn_patterns:
            patterns.append(RegexPattern(pattern, EntityType.SSN, 0.95))
        
        # PAN (Permanent Account Number) - Indian tax identifier
        pan_pattern = r'\b[A-Z]{5}\d{4}[A-Z]\b'
        patterns.append(RegexPattern(pan_pattern, EntityType.PAN, 0.90))
        
        # Credit Card patterns
        credit_card_patterns = [
            r'\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Visa
            r'\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # MasterCard
            r'\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b',  # American Express
            r'\b6011[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'  # Discover
        ]
        for pattern in credit_card_patterns:
            patterns.append(RegexPattern(pattern, EntityType.CREDIT_CARD, 0.85))
        
        # IBAN patterns
        iban_pattern = r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b'
        patterns.append(RegexPattern(iban_pattern, EntityType.IBAN, 0.80))
        
        # IP Address patterns
        ip_patterns = [
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IPv4
            r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'  # IPv6 (simplified)
        ]
        for pattern in ip_patterns:
            patterns.append(RegexPattern(pattern, EntityType.IP_ADDRESS, 0.90))
        
        # URL patterns
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
        patterns.append(RegexPattern(url_pattern, EntityType.URL, 0.85))
        
        # Address patterns (basic)
        address_patterns = [
            r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b',
            r'\b\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}(-\d{4})?\b'  # Street, City, State ZIP
        ]
        for pattern in address_patterns:
            patterns.append(RegexPattern(pattern, EntityType.ADDRESS, 0.70))
        
        return patterns
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Detect PII using regex patterns"""
        candidates = []
        
        for regex_pattern in self.patterns:
            matches = regex_pattern.pattern.finditer(text)
            
            for match in matches:
                # Additional validation for some types
                if self._validate_match(match.group(), regex_pattern.entity_type):
                    candidate = DetectionCandidate(
                        id=None,  # Will be auto-generated
                        type=regex_pattern.entity_type,
                        text=match.group(),
                        bbox=None,  # Will be set later with OCR data
                        confidence=regex_pattern.confidence,
                        start_char=match.start(),
                        end_char=match.end(),
                        source=self.name,
                        metadata={
                            "pattern": regex_pattern.pattern.pattern,
                            "validation_passed": True
                        }
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _validate_match(self, text: str, entity_type: EntityType) -> bool:
        """Additional validation for certain entity types"""
        
        if entity_type == EntityType.CREDIT_CARD:
            return self._validate_credit_card(text)
        elif entity_type == EntityType.SSN:
            return self._validate_ssn(text)
        elif entity_type == EntityType.IP_ADDRESS:
            return self._validate_ip_address(text)
        
        return True
    
    def _validate_credit_card(self, card_number: str) -> bool:
        """Validate credit card using Luhn algorithm"""
        # Remove spaces and hyphens
        digits = re.sub(r'[-\s]', '', card_number)
        
        if not digits.isdigit():
            return False
        
        # Luhn algorithm
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10
        
        return luhn_checksum(digits) == 0
    
    def _validate_ssn(self, ssn: str) -> bool:
        """Basic SSN validation"""
        # Remove formatting
        digits = re.sub(r'[-\s]', '', ssn)
        digits = re.sub(r'SSN:?\s*', '', digits, flags=re.IGNORECASE)
        
        if len(digits) != 9 or not digits.isdigit():
            return False
        
        # Check for invalid SSNs
        if digits == '000000000' or digits[:3] == '000' or digits[3:5] == '00' or digits[5:] == '0000':
            return False
        
        # Check for sequential digits
        if digits == '123456789' or digits == '987654321':
            return False
        
        return True
    
    def _validate_ip_address(self, ip: str) -> bool:
        """Validate IPv4 address"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        try:
            for part in parts:
                num = int(part)
                if not (0 <= num <= 255):
                    return False
            return True
        except ValueError:
            return False
    
    def get_supported_types(self) -> List[EntityType]:
        """Return supported entity types"""
        return list(set(pattern.entity_type for pattern in self.patterns))

class CustomRuleDetector(BaseDetector):
    """Detector for custom regex patterns defined by users"""
    
    def __init__(self):
        super().__init__("custom_rules")
        self.custom_patterns: List[RegexPattern] = []
    
    def add_pattern(self, pattern: str, entity_type: EntityType, confidence: float = 0.8):
        """Add a custom regex pattern"""
        try:
            regex_pattern = RegexPattern(pattern, entity_type, confidence)
            self.custom_patterns.append(regex_pattern)
            return True
        except re.error as e:
            print(f"Invalid regex pattern: {e}")
            return False
    
    def remove_pattern(self, pattern: str):
        """Remove a custom pattern"""
        self.custom_patterns = [
            p for p in self.custom_patterns 
            if p.pattern.pattern != pattern
        ]
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Detect using custom patterns"""
        candidates = []
        
        for regex_pattern in self.custom_patterns:
            matches = regex_pattern.pattern.finditer(text)
            
            for match in matches:
                candidate = DetectionCandidate(
                    id=None,
                    type=regex_pattern.entity_type,
                    text=match.group(),
                    bbox=None,
                    confidence=regex_pattern.confidence,
                    start_char=match.start(),
                    end_char=match.end(),
                    source=self.name,
                    metadata={
                        "pattern": regex_pattern.pattern.pattern,
                        "custom_rule": True
                    }
                )
                candidates.append(candidate)
        
        return candidates
    
    def get_supported_types(self) -> List[EntityType]:
        """Return supported entity types from custom patterns"""
        return list(set(pattern.entity_type for pattern in self.custom_patterns))