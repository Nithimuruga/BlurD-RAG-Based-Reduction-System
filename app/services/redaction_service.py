"""
PII redaction service with multiple redaction strategies.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import re
import logging
import uuid
import hashlib
import base64
import json
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

from app.schemas.pii_schemas import (
    PIIType, RedactionStrategy, DetectedPII, RedactionResult, RedactionOptions,
    PIIDetectionResult
)

logger = logging.getLogger(__name__)

class RedactionService:
    """Service for redacting PII using various strategies"""
    
    def __init__(self, encryption_key: str = None):
        """
        Initialize the redaction service
        
        Args:
            encryption_key: Optional key for reversible redaction
                If not provided, a random key will be generated
        """
        self.encryption_key = encryption_key or secrets.token_urlsafe(32)
        self._setup_encryption()
        self.default_options = RedactionOptions()
    
    def _setup_encryption(self):
        """Set up encryption for tokenization"""
        # Generate a key from the encryption key
        salt = b'pii_redaction_salt'  # Salt should be stored securely in production
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
        self.cipher = Fernet(key)
    
    async def redact_text(self, 
                         text: str, 
                         detected_pii: List[DetectedPII], 
                         options: RedactionOptions = None) -> RedactionResult:
        """
        Redact PII in text based on detected entities
        
        Args:
            text: Original text to redact
            detected_pii: List of detected PII entities
            options: Redaction options
            
        Returns:
            RedactionResult with redacted text and metadata
        """
        if not text or not detected_pii:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                redaction_count={},
                detected_entities=[],
                processing_time=0
            )
        
        # Use default options if not provided
        options = options or self.default_options
        
        # Sort entities by position (end to start to avoid offset issues)
        sorted_entities = sorted(detected_pii, key=lambda x: x.start_position, reverse=True)
        
        # Make a copy of the original text
        redacted_text = text
        
        # Track redaction counts by type
        redaction_count = {}
        
        # Process each entity
        for entity in sorted_entities:
            # Determine redaction strategy for this entity
            strategy = self._get_redaction_strategy(entity, options)
            
            # Apply redaction
            redacted_value, redaction_info = await self._apply_redaction_strategy(
                text=entity.text, 
                strategy=strategy,
                pii_type=entity.pii_type, 
                options=options
            )
            
            # Replace in the text
            start = entity.start_position
            end = entity.end_position
            redacted_text = redacted_text[:start] + redacted_value + redacted_text[end:]
            
            # Update entity with redaction info
            entity.redacted_text = redacted_value
            entity.metadata.update(redaction_info)
            
            # Track counts
            redaction_count[entity.pii_type] = redaction_count.get(entity.pii_type, 0) + 1
        
        return RedactionResult(
            original_text=text,
            redacted_text=redacted_text,
            redaction_count=redaction_count,
            detected_entities=sorted_entities,
            processing_time=0  # Will be updated by the caller
        )
    
    def _get_redaction_strategy(self, entity: DetectedPII, options: RedactionOptions) -> RedactionStrategy:
        """Determine the redaction strategy for a specific entity"""
        # Check if there's a per-type strategy defined
        if entity.pii_type in options.per_type_strategy:
            return options.per_type_strategy[entity.pii_type]
        
        # Otherwise use the default strategy
        return options.default_strategy
    
    async def _apply_redaction_strategy(self, 
                                       text: str, 
                                       strategy: RedactionStrategy,
                                       pii_type: PIIType, 
                                       options: RedactionOptions) -> Tuple[str, Dict[str, Any]]:
        """
        Apply a redaction strategy to text
        
        Args:
            text: Text to redact
            strategy: Redaction strategy to apply
            pii_type: Type of PII
            options: Redaction options
            
        Returns:
            Tuple of (redacted_text, metadata)
        """
        metadata = {"strategy": strategy}
        
        # Check for custom replacement
        if pii_type in options.custom_replacements:
            return options.custom_replacements[pii_type], {
                "strategy": strategy, 
                "method": "custom_replacement"
            }
        
        # Apply the specified strategy
        if strategy == RedactionStrategy.FULL_REMOVAL:
            return "", {"strategy": strategy, "method": "full_removal"}
            
        elif strategy == RedactionStrategy.FULL_MASK:
            mask_char = options.mask_char or "X"
            if options.preserve_length:
                return mask_char * len(text), {
                    "strategy": strategy, 
                    "method": "full_mask",
                    "mask_char": mask_char
                }
            else:
                return mask_char * 5, {
                    "strategy": strategy, 
                    "method": "fixed_mask",
                    "mask_char": mask_char
                }
            
        elif strategy == RedactionStrategy.PARTIAL_MASK:
            return self._partial_mask(text, pii_type, options), {
                "strategy": strategy, 
                "method": "partial_mask",
                "mask_char": options.mask_char
            }
            
        elif strategy == RedactionStrategy.TOKENIZATION:
            token, is_reversible = self._tokenize(text, options)
            return token, {
                "strategy": strategy, 
                "method": "tokenization",
                "reversible": is_reversible
            }
            
        elif strategy == RedactionStrategy.PSEUDONYMIZATION:
            pseudonym = await self._pseudonymize(text, pii_type)
            return pseudonym, {
                "strategy": strategy, 
                "method": "pseudonymization"
            }
            
        elif strategy == RedactionStrategy.GENERALIZATION:
            generalized = self._generalize(text, pii_type)
            return generalized, {
                "strategy": strategy, 
                "method": "generalization"
            }
            
        else:  # NONE or unknown strategy
            return text, {"strategy": RedactionStrategy.NONE, "method": "none"}
    
    def _partial_mask(self, text: str, pii_type: PIIType, options: RedactionOptions) -> str:
        """Apply partial masking based on PII type"""
        mask_char = options.mask_char or "X"
        
        # Special handling for different PII types
        if pii_type == PIIType.CREDIT_CARD:
            # Mask all but last 4 digits (e.g., XXXX-XXXX-XXXX-1234)
            digits = ''.join(c for c in text if c.isdigit())
            if len(digits) >= 4:
                visible = digits[-4:]
                mask_length = len(digits) - 4
                masked_part = mask_char * mask_length
                
                if options.preserve_format and any(c in text for c in ['-', ' ']):
                    # Try to preserve format (e.g., XXXX-XXXX-XXXX-1234)
                    result = ''
                    digit_index = 0
                    for char in text:
                        if char.isdigit():
                            if digit_index < mask_length:
                                result += mask_char
                            else:
                                result += char
                            digit_index += 1
                        else:
                            result += char
                    return result
                else:
                    return masked_part + visible
            
        elif pii_type == PIIType.SSN:
            # Mask SSN as XXX-XX-1234
            digits = ''.join(c for c in text if c.isdigit())
            if len(digits) == 9:
                if options.preserve_format and '-' in text:
                    return f"{mask_char * 3}-{mask_char * 2}-{digits[-4:]}"
                else:
                    return f"{mask_char * 5}{digits[-4:]}"
        
        elif pii_type == PIIType.PHONE:
            # Mask phone as (XXX) XXX-1234 or similar
            digits = ''.join(c for c in text if c.isdigit())
            if len(digits) >= 4:
                visible = digits[-4:]
                mask_length = len(digits) - 4
                
                if options.preserve_format:
                    result = ''
                    digit_index = 0
                    for char in text:
                        if char.isdigit():
                            if digit_index < mask_length:
                                result += mask_char
                            else:
                                result += char
                            digit_index += 1
                        else:
                            result += char
                    return result
                else:
                    return f"{mask_char * mask_length}{visible}"
        
        elif pii_type == PIIType.EMAIL:
            # Mask as x***@domain.com
            if '@' in text:
                username, domain = text.split('@', 1)
                if len(username) > 1:
                    masked_username = username[0] + mask_char * (len(username) - 1)
                    return f"{masked_username}@{domain}"
        
        elif pii_type == PIIType.PERSON_NAME:
            # Mask as J*** D**
            name_parts = text.split()
            if len(name_parts) >= 2:
                first = name_parts[0]
                last = name_parts[-1]
                middle = name_parts[1:-1] if len(name_parts) > 2 else []
                
                masked_first = first[0] + mask_char * (len(first) - 1)
                masked_last = last[0] + mask_char * (len(last) - 1)
                
                masked_middle = []
                for part in middle:
                    if len(part) > 1:
                        masked_middle.append(part[0] + mask_char * (len(part) - 1))
                    else:
                        masked_middle.append(part)
                
                return " ".join([masked_first] + masked_middle + [masked_last])
        
        # Default: mask all but first and last character
        if len(text) > 2:
            return text[0] + mask_char * (len(text) - 2) + text[-1]
        elif len(text) == 2:
            return text[0] + mask_char
        else:
            return mask_char * len(text)
    
    def _tokenize(self, text: str, options: RedactionOptions) -> Tuple[str, bool]:
        """Tokenize text using reversible encryption"""
        try:
            # Generate a deterministic token based on the text
            if options.tokenization_key:
                # Use provided key for encryption (reversible)
                encrypted = self.cipher.encrypt(text.encode())
                token = f"TOK_{base64.urlsafe_b64encode(encrypted).decode()[:15]}"
                return token, True
            else:
                # No key, use one-way hash (non-reversible)
                hash_obj = hashlib.sha256(text.encode())
                return f"TOK_{hash_obj.hexdigest()[:15]}", False
        except Exception as e:
            logger.error(f"Tokenization error: {e}")
            return f"TOK_ERROR_{uuid.uuid4().hex[:8]}", False
    
    async def _pseudonymize(self, text: str, pii_type: PIIType) -> str:
        """Replace with realistic but fake data based on type"""
        # In a real implementation, this could use a service or database of fake data
        # Here, we'll use simple replacements for demonstration
        
        if pii_type == PIIType.PERSON_NAME:
            name_parts = text.split()
            if len(name_parts) == 1:
                return self._get_fake_name(first_only=True)
            else:
                return self._get_fake_name()
                
        elif pii_type == PIIType.EMAIL:
            return f"user{uuid.uuid4().hex[:8]}@example.com"
            
        elif pii_type == PIIType.PHONE:
            return f"(555) 000-{secrets.randbelow(10000):04d}"
            
        elif pii_type == PIIType.ADDRESS:
            return f"{secrets.randbelow(1000)} Main Street, Anytown, USA"
        
        # For other types, return a placeholder
        return f"PSEUDONYM_{pii_type.value}_{uuid.uuid4().hex[:8]}"
    
    def _generalize(self, text: str, pii_type: PIIType) -> str:
        """Replace with more general category"""
        if pii_type == PIIType.PERSON_NAME:
            return "[PERSON]"
        elif pii_type == PIIType.EMAIL:
            return "[EMAIL]"
        elif pii_type == PIIType.PHONE:
            return "[PHONE NUMBER]"
        elif pii_type == PIIType.ADDRESS:
            return "[ADDRESS]"
        elif pii_type == PIIType.CREDIT_CARD:
            return "[PAYMENT CARD]"
        elif pii_type == PIIType.SSN:
            return "[SSN]"
        elif pii_type == PIIType.PASSPORT:
            return "[PASSPORT]"
        elif pii_type == PIIType.DRIVERS_LICENSE:
            return "[DRIVER'S LICENSE]"
        elif pii_type == PIIType.DATE_OF_BIRTH:
            return "[DOB]"
        elif pii_type == PIIType.BANK_ACCOUNT:
            return "[BANK ACCOUNT]"
        else:
            return f"[{pii_type.value.upper()}]"
    
    def _get_fake_name(self, first_only=False) -> str:
        """Generate a fake name"""
        first_names = ["John", "Jane", "Alex", "Sam", "Taylor", "Morgan", "Jordan", "Casey"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis"]
        
        first = secrets.choice(first_names)
        if first_only:
            return first
        else:
            return f"{first} {secrets.choice(last_names)}"
    
    async def process_detection_result(self, 
                                     result: PIIDetectionResult, 
                                     options: RedactionOptions = None) -> Dict[str, Any]:
        """
        Process a detection result and apply redaction
        
        Args:
            result: Detection result from PII detection
            options: Redaction options
            
        Returns:
            Dictionary with redacted content and statistics
        """
        if not result or not result.success:
            return {
                "success": False,
                "error": "Invalid detection result",
                "redacted_text": ""
            }
            
        text = result.metadata.get("original_text", "")
        if not text:
            return {
                "success": False,
                "error": "No text to redact",
                "redacted_text": ""
            }
            
        redaction_result = await self.redact_text(
            text=text,
            detected_pii=result.detected_entities,
            options=options
        )
        
        return {
            "success": True,
            "redacted_text": redaction_result.redacted_text,
            "redaction_count": redaction_result.redaction_count,
            "detected_entities": [e.dict() for e in redaction_result.detected_entities],
            "processing_time": redaction_result.processing_time
        }