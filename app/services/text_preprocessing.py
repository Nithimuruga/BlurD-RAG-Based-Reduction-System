"""
Text preprocessing pipeline for PII detection.
This module provides functionality for text normalization, language detection,
OCR cleanup, and other preprocessing steps before PII detection.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import re
import logging
import unicodedata
from dataclasses import dataclass, field
import json

# Try to import optional dependencies
try:
    from langdetect import detect as detect_language
    from langdetect import DetectorFactory
    # Make language detection deterministic
    DetectorFactory.seed = 0
    LANGUAGE_DETECTION_AVAILABLE = True
except ImportError:
    LANGUAGE_DETECTION_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class TextSegment:
    """Represents a segment of text with metadata"""
    text: str
    start: int
    end: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __len__(self):
        return len(self.text)

@dataclass
class ProcessedDocument:
    """Represents a document after preprocessing"""
    original_text: str
    processed_text: str
    segments: List[TextSegment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    character_map: Dict[int, int] = field(default_factory=dict)
    
    def map_position(self, processed_pos: int) -> int:
        """Map a position in the processed text to a position in the original text"""
        return self.character_map.get(processed_pos, -1)
    
    def map_range(self, processed_start: int, processed_end: int) -> Tuple[int, int]:
        """Map a range in the processed text to a range in the original text"""
        orig_start = self.map_position(processed_start)
        orig_end = self.map_position(processed_end)
        
        # Handle edge cases where mapping is not exact
        if orig_start == -1 or orig_end == -1:
            return (-1, -1)
            
        return (orig_start, orig_end)

class TextPreprocessor:
    """Text preprocessing pipeline for PII detection"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.default_steps = [
            "remove_control_chars",
            "normalize_whitespace",
            "normalize_unicode",
            "detect_language",
            "segment_text"
        ]
        
    async def preprocess(self, 
                        text: str, 
                        steps: List[str] = None, 
                        metadata: Dict[str, Any] = None) -> ProcessedDocument:
        """
        Preprocess text through the pipeline
        
        Args:
            text: Input text to process
            steps: List of preprocessing steps to apply (default: all steps)
            metadata: Additional metadata to include
            
        Returns:
            ProcessedDocument containing the processed text and metadata
        """
        if not text:
            return ProcessedDocument(
                original_text="",
                processed_text="",
                metadata=metadata or {}
            )
            
        # Use default steps if none specified
        steps = steps or self.default_steps
        metadata = metadata or {}
        
        # Initialize processed document
        processed = text
        doc = ProcessedDocument(
            original_text=text,
            processed_text=processed,
            metadata=metadata
        )
        
        # Build initial character map (1:1 mapping)
        doc.character_map = {i: i for i in range(len(text))}
        
        # Apply each preprocessing step
        for step in steps:
            step_func = getattr(self, f"_step_{step}", None)
            if step_func:
                try:
                    doc = await step_func(doc)
                except Exception as e:
                    logger.warning(f"Error in preprocessing step '{step}': {e}")
            else:
                logger.warning(f"Unknown preprocessing step: {step}")
        
        return doc
    
    async def _step_remove_control_chars(self, doc: ProcessedDocument) -> ProcessedDocument:
        """Remove control characters from text"""
        text = doc.processed_text
        result = ""
        new_map = {}
        
        # Index in the processed text
        p_idx = 0
        # Index in the result text
        r_idx = 0
        
        for char in text:
            # Skip control characters except whitespace
            if unicodedata.category(char)[0] == "C" and char not in (" ", "\t", "\n", "\r"):
                p_idx += 1
                continue
                
            result += char
            # Map the position in the result to the original text
            orig_pos = doc.character_map.get(p_idx, -1)
            if orig_pos != -1:
                new_map[r_idx] = orig_pos
                
            p_idx += 1
            r_idx += 1
        
        doc.processed_text = result
        doc.character_map = new_map
        doc.metadata["removed_control_chars"] = p_idx - r_idx
        
        return doc
    
    async def _step_normalize_whitespace(self, doc: ProcessedDocument) -> ProcessedDocument:
        """Normalize whitespace in text"""
        text = doc.processed_text
        
        # Replace multiple whitespace characters with a single space
        # Preserve paragraph breaks (double newlines)
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Preserve paragraph breaks
        text = re.sub(r'[ \t]+', ' ', text)      # Compress horizontal whitespace
        text = re.sub(r' *\n *', '\n', text)     # Clean around newlines
        
        # Build new character map (this is complex with whitespace normalization)
        # We'll need to track how the positions change
        result = ""
        new_map = {}
        
        p_idx = 0  # Position in the processed text
        r_idx = 0  # Position in the result text
        
        # Process the text
        i = 0
        while i < len(doc.processed_text):
            char = doc.processed_text[i]
            
            # Handle whitespace sequences
            if char in (' ', '\t'):
                # Check for whitespace sequence
                ws_len = 1
                j = i + 1
                while j < len(doc.processed_text) and doc.processed_text[j] in (' ', '\t'):
                    ws_len += 1
                    j += 1
                
                # Add single space to result
                result += ' '
                # Map this position
                orig_pos = doc.character_map.get(i, -1)
                if orig_pos != -1:
                    new_map[r_idx] = orig_pos
                
                # Skip the rest of the whitespace
                i += ws_len
                r_idx += 1
            else:
                # Normal character
                result += char
                orig_pos = doc.character_map.get(i, -1)
                if orig_pos != -1:
                    new_map[r_idx] = orig_pos
                
                i += 1
                r_idx += 1
        
        doc.processed_text = result
        doc.character_map = new_map
        
        return doc
    
    async def _step_normalize_unicode(self, doc: ProcessedDocument) -> ProcessedDocument:
        """Normalize Unicode characters"""
        text = doc.processed_text
        
        # Normalize to NFKC form (compatible equivalence)
        normalized = unicodedata.normalize('NFKC', text)
        
        # If the text didn't change, just return the document
        if normalized == text:
            return doc
        
        # Since normalization can change the length of the text,
        # we need to rebuild the character map
        result = normalized
        new_map = {}
        
        # This is a simplification - full Unicode normalization mapping is complex
        # For accurate mapping, we would need to track the exact normalization changes
        if len(normalized) == len(text):
            # If lengths are the same, mapping is straightforward
            new_map = doc.character_map
        else:
            # Otherwise, we need to approximate the mapping
            # This is a simplified approximation that doesn't handle all cases
            ratio = len(doc.original_text) / len(normalized)
            for i in range(len(normalized)):
                approx_pos = int(i * ratio)
                if approx_pos < len(doc.original_text):
                    new_map[i] = approx_pos
        
        doc.processed_text = result
        doc.character_map = new_map
        doc.metadata["unicode_normalized"] = True
        
        return doc
    
    async def _step_detect_language(self, doc: ProcessedDocument) -> ProcessedDocument:
        """Detect the language of the text"""
        if not LANGUAGE_DETECTION_AVAILABLE:
            doc.metadata["language_detection"] = "unavailable"
            return doc
            
        try:
            # Only detect if we have enough text
            if len(doc.processed_text) >= 10:
                lang = detect_language(doc.processed_text[:4000])  # Use first 4000 chars
                doc.metadata["detected_language"] = lang
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            doc.metadata["language_detection_error"] = str(e)
            
        return doc
    
    async def _step_segment_text(self, doc: ProcessedDocument) -> ProcessedDocument:
        """Segment text into paragraphs or sections"""
        text = doc.processed_text
        
        # Simple paragraph-based segmentation
        paragraphs = re.split(r'\n\s*\n', text)
        segments = []
        
        pos = 0
        for para in paragraphs:
            if not para.strip():
                pos += len(para) + 2  # +2 for the removed paragraph separator
                continue
                
            # Create text segment
            seg = TextSegment(
                text=para,
                start=pos,
                end=pos + len(para),
                metadata={"type": "paragraph"}
            )
            segments.append(seg)
            pos += len(para) + 2  # +2 for the removed paragraph separator
        
        doc.segments = segments
        doc.metadata["segment_count"] = len(segments)
        
        return doc
    
    async def _step_normalize_ocr_text(self, doc: ProcessedDocument) -> ProcessedDocument:
        """Apply OCR-specific text cleanup"""
        text = doc.processed_text
        
        # Common OCR error patterns and corrections
        ocr_fixes = [
            # Format: (pattern, replacement)
            (r'l\b', '1'),              # Lowercase l at end of word -> 1
            (r'\b0\b', 'O'),            # Single 0 -> O
            (r'rn', 'm'),               # 'rn' -> 'm'
            (r'S\$', '$'),              # S$ -> $
            (r'，', ','),               # Full-width comma -> regular comma
        ]
        
        # Apply fixes and track changes
        result = text
        change_count = 0
        
        for pattern, replacement in ocr_fixes:
            new_text = re.sub(pattern, replacement, result)
            if new_text != result:
                change_count += len(re.findall(pattern, result))
                result = new_text
        
        # If no changes were made, return the original document
        if change_count == 0:
            return doc
        
        # Create a new character map (simplified - assumes 1:1 replacements)
        # For complex OCR fixes, more sophisticated mapping would be needed
        
        doc.processed_text = result
        doc.metadata["ocr_fixes"] = change_count
        
        return doc
    
    async def _step_clean_boilerplate(self, doc: ProcessedDocument) -> ProcessedDocument:
        """Remove common boilerplate text"""
        text = doc.processed_text
        
        # Common boilerplate patterns to remove
        boilerplate_patterns = [
            r'Page \d+ of \d+',
            r'CONFIDENTIAL',
            r'©\s*\d{4}.*\bAll rights reserved\b',
            r'www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'Powered by.*'
        ]
        
        # Apply pattern removal
        result = text
        removed_count = 0
        
        for pattern in boilerplate_patterns:
            matches = list(re.finditer(pattern, result, re.IGNORECASE))
            removed_count += len(matches)
            
            # Remove in reverse order to preserve positions
            for match in reversed(matches):
                start, end = match.span()
                result = result[:start] + ' ' * (end - start) + result[end:]
        
        # If no changes were made, return the original document
        if removed_count == 0:
            return doc
        
        doc.processed_text = result
        doc.metadata["boilerplate_removed"] = removed_count
        
        return doc