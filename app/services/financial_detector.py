"""
Financial-specific PII detector.
Detects financial-related PII using specialized patterns and rules.
"""

from typing import List, Dict, Any, Optional
import re
import logging
from app.services.detection_pipeline import BaseDetector, DetectionCandidate, EntityType
from app.schemas.pii_schemas import PIIType, RiskLevel

logger = logging.getLogger(__name__)

class FinancialDetector(BaseDetector):
    """
    Financial-specific PII detector for banking, investment, and financial identifiers
    """
    
    def __init__(self):
        super().__init__("financial")
        self._initialize_patterns()
        
    def get_supported_types(self) -> List[Any]:
        """Return list of entity types this detector can identify"""
        return [
            PIIType.CREDIT_CARD,
            PIIType.BANK_ACCOUNT,
            PIIType.IBAN,
            PIIType.FINANCIAL_ACCOUNT,
            PIIType.CRYPTO_ADDRESS
        ]
    
    def _initialize_patterns(self):
        """Initialize financial-specific patterns"""
        
        # Credit card related patterns
        self.credit_card_patterns = [
            r'\bCVV\s*:?\s*(\d{3,4})\b',
            r'\bCVC\s*:?\s*(\d{3,4})\b',
            r'\bSecurity Code\s*:?\s*(\d{3,4})\b',
            r'\bExpir(?:y|ation)(?:\s+Date)?\s*:?\s*(\d{2}[/\s.-]\d{2,4})\b',
            r'\bExp\s*:?\s*(\d{2}[/\s.-]\d{2,4})\b'
        ]
        
        # Bank account related patterns
        self.bank_account_patterns = [
            r'\bAccount\s*[:#]?\s*(\d{6,17})\b',
            r'\bAcct\s*[:#]?\s*(\d{6,17})\b',
            r'\bRouting\s*[:#]?\s*(\d{9})\b',  # US routing numbers are 9 digits
            r'\bABA\s*[:#]?\s*(\d{9})\b'  # ABA routing number
        ]
        
        # SWIFT/BIC codes for international transfers
        self.swift_patterns = [
            r'\bSWIFT\s*:?\s*([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b',
            r'\bBIC\s*:?\s*([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b'
        ]
        
        # IBAN patterns
        self.iban_patterns = [
            r'\bIBAN\s*:?\s*([A-Z]{2}\d{2}[A-Z0-9]{4}[0-9]{7}(?:[A-Z0-9]{0,16}))\b',
            r'\b([A-Z]{2}\d{2}[A-Z0-9]{4}[0-9]{7}(?:[A-Z0-9]{0,16}))\b'
        ]
        
        # Investment account patterns
        self.investment_patterns = [
            r'\bPortfolio\s*[:#]?\s*([A-Z0-9]{5,12})\b',
            r'\bBrokerage\s*[:#]?\s*([A-Z0-9]{5,12})\b',
            r'\b401[Kk]\s*[:#]?\s*([A-Z0-9]{5,12})\b',
            r'\bIRA\s*[:#]?\s*([A-Z0-9]{5,12})\b'
        ]
        
        # Cryptocurrency wallet addresses
        self.crypto_patterns = {
            "bitcoin": r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b',
            "ethereum": r'\b0x[a-fA-F0-9]{40}\b',
            "ripple": r'\br[a-zA-Z0-9]{24,34}\b',
            "litecoin": r'\b[LM][a-km-zA-HJ-NP-Z1-9]{26,33}\b'
        }
        
        # Tax identification numbers
        self.tax_patterns = [
            r'\bEIN\s*:?\s*(\d{2}-\d{7})\b',  # Employer Identification Number
            r'\bTax ID\s*:?\s*(\d{2}-\d{7})\b',
            r'\bTIN\s*:?\s*(\d{9})\b'  # Taxpayer Identification Number
        ]
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """
        Detect financial-related PII
        
        Args:
            text: Text to analyze
            **kwargs: Additional parameters
                
        Returns:
            List of detected PII candidates
        """
        if not text:
            return []
        
        candidates = []
        
        # Detect CVV/CVC and credit card expiration dates
        for pattern in self.credit_card_patterns:
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
                
                # Determine the specific type based on the pattern
                if "CVV" in matched_text or "CVC" in matched_text or "Security Code" in matched_text:
                    pii_subtype = "cvv"
                    confidence = 0.95
                else:
                    pii_subtype = "expiration_date"
                    confidence = 0.9
                
                candidates.append(DetectionCandidate(
                    id=None,
                    type=PIIType.CREDIT_CARD,
                    text=id_text,
                    bbox=None,
                    confidence=confidence,
                    start_char=id_start,
                    end_char=id_end,
                    source=self.name,
                    metadata={
                        "full_match": matched_text,
                        "detection_method": "financial_regex",
                        "context": self._extract_context(text, start, end),
                        "financial_subtype": pii_subtype
                    }
                ))
        
        # Detect bank account numbers and routing numbers
        for pattern in self.bank_account_patterns:
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
                
                # Determine the specific type based on the pattern
                if "Routing" in matched_text or "ABA" in matched_text:
                    pii_subtype = "routing_number"
                    pii_type = PIIType.CUSTOM
                    confidence = 0.95
                else:
                    pii_subtype = "account_number"
                    pii_type = PIIType.BANK_ACCOUNT
                    confidence = 0.9
                
                candidates.append(DetectionCandidate(
                    id=None,
                    type=pii_type,
                    text=id_text,
                    bbox=None,
                    confidence=confidence,
                    start_char=id_start,
                    end_char=id_end,
                    source=self.name,
                    metadata={
                        "full_match": matched_text,
                        "detection_method": "financial_regex",
                        "context": self._extract_context(text, start, end),
                        "financial_subtype": pii_subtype
                    }
                ))
        
        # Detect SWIFT/BIC codes
        for pattern in self.swift_patterns:
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
                    confidence=0.95,
                    start_char=id_start,
                    end_char=id_end,
                    source=self.name,
                    metadata={
                        "full_match": matched_text,
                        "detection_method": "financial_regex",
                        "context": self._extract_context(text, start, end),
                        "financial_subtype": "swift_code",
                        "custom_type": "swift_code"
                    }
                ))
        
        # Detect IBAN
        for pattern in self.iban_patterns:
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
                    type=PIIType.IBAN,
                    text=id_text,
                    bbox=None,
                    confidence=0.95,
                    start_char=id_start,
                    end_char=id_end,
                    source=self.name,
                    metadata={
                        "full_match": matched_text,
                        "detection_method": "financial_regex",
                        "context": self._extract_context(text, start, end)
                    }
                ))
        
        # Detect cryptocurrency wallet addresses
        for crypto_type, pattern in self.crypto_patterns.items():
            for match in re.finditer(pattern, text):
                start, end = match.span()
                matched_text = text[start:end]
                
                candidates.append(DetectionCandidate(
                    id=None,
                    type=PIIType.CRYPTO_ADDRESS,
                    text=matched_text,
                    bbox=None,
                    confidence=0.9,
                    start_char=start,
                    end_char=end,
                    source=self.name,
                    metadata={
                        "detection_method": "financial_regex",
                        "context": self._extract_context(text, start, end),
                        "crypto_type": crypto_type
                    }
                ))
        
        # Detect tax identification numbers
        for pattern in self.tax_patterns:
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
                    type=PIIType.TAX_ID,
                    text=id_text,
                    bbox=None,
                    confidence=0.9,
                    start_char=id_start,
                    end_char=id_end,
                    source=self.name,
                    metadata={
                        "full_match": matched_text,
                        "detection_method": "financial_regex",
                        "context": self._extract_context(text, start, end),
                        "tax_id_type": "ein" if "EIN" in matched_text else "tax_id"
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