from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from app.utils.db import get_database
from app.services.detection_pipeline import BaseDetector, DetectionCandidate, EntityType
import re

logger = logging.getLogger(__name__)

class EntityDefinition:
    """Represents an entity definition in the knowledge base"""
    
    def __init__(self, entity_type: str, name: str, description: str, 
                 patterns: List[str] = None, context_keywords: List[str] = None,
                 sensitivity_level: str = "medium", examples: List[str] = None):
        self.entity_type = entity_type
        self.name = name
        self.description = description
        self.patterns = patterns or []
        self.context_keywords = context_keywords or []
        self.sensitivity_level = sensitivity_level  # low, medium, high, critical
        self.examples = examples or []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "name": self.name,
            "description": self.description,
            "patterns": self.patterns,
            "context_keywords": self.context_keywords,
            "sensitivity_level": self.sensitivity_level,
            "examples": self.examples,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityDefinition':
        obj = cls(
            entity_type=data["entity_type"],
            name=data["name"],
            description=data["description"],
            patterns=data.get("patterns", []),
            context_keywords=data.get("context_keywords", []),
            sensitivity_level=data.get("sensitivity_level", "medium"),
            examples=data.get("examples", [])
        )
        obj.created_at = data.get("created_at", datetime.utcnow())
        obj.updated_at = data.get("updated_at", datetime.utcnow())
        return obj

class KnowledgeBase:
    """MongoDB-based knowledge base for entity definitions"""
    
    def __init__(self):
        self.collection_name = "entity_definitions"
        self._initialized = False
    
    async def initialize(self):
        """Initialize knowledge base with default entity definitions"""
        if self._initialized:
            return
        
        db = get_database()
        if db is None:
            logger.error("Database connection not available")
            return
        
        collection = db[self.collection_name]
        
        # Check if already initialized
        count = await collection.count_documents({})
        if count > 0:
            self._initialized = True
            return
        
        # Insert default entity definitions
        default_definitions = self._get_default_definitions()
        
        for definition in default_definitions:
            await collection.insert_one(definition.to_dict())
        
        # Create text index for semantic search
        await collection.create_index([
            ("name", "text"),
            ("description", "text"),
            ("context_keywords", "text")
        ])
        
        self._initialized = True
        logger.info(f"Initialized knowledge base with {len(default_definitions)} entity definitions")
    
    def _get_default_definitions(self) -> List[EntityDefinition]:
        """Get default entity definitions"""
        return [
            EntityDefinition(
                entity_type="person",
                name="Person Name",
                description="Names of individuals, including first names, last names, and full names",
                patterns=[r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"],
                context_keywords=["name", "person", "individual", "mr", "mrs", "ms", "dr", "prof"],
                sensitivity_level="high",
                examples=["John Smith", "Dr. Sarah Johnson", "Mr. Robert Brown"]
            ),
            EntityDefinition(
                entity_type="email",
                name="Email Address",
                description="Electronic mail addresses including personal and business emails",
                patterns=[r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"],
                context_keywords=["email", "e-mail", "contact", "address"],
                sensitivity_level="high",
                examples=["john@example.com", "sarah.johnson@company.org"]
            ),
            EntityDefinition(
                entity_type="phone",
                name="Phone Number",
                description="Telephone numbers including mobile, landline, and international numbers",
                patterns=[
                    r"\b\d{3}-\d{3}-\d{4}\b",
                    r"\b\(\d{3}\)\s?\d{3}-\d{4}\b",
                    r"\b\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"
                ],
                context_keywords=["phone", "telephone", "mobile", "cell", "contact", "number"],
                sensitivity_level="medium",
                examples=["555-123-4567", "(555) 123-4567", "+1 555 123 4567"]
            ),
            EntityDefinition(
                entity_type="ssn",
                name="Social Security Number",
                description="US Social Security Numbers used for identification and benefits",
                patterns=[r"\b\d{3}-\d{2}-\d{4}\b", r"\b\d{3}\s\d{2}\s\d{4}\b"],
                context_keywords=["ssn", "social security", "social security number"],
                sensitivity_level="critical",
                examples=["123-45-6789", "123 45 6789"]
            ),
            EntityDefinition(
                entity_type="credit_card",
                name="Credit Card Number",
                description="Credit and debit card numbers from various issuers",
                patterns=[
                    r"\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Visa
                    r"\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # MasterCard
                    r"\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b"  # Amex
                ],
                context_keywords=["credit card", "debit card", "card number", "payment"],
                sensitivity_level="critical",
                examples=["4532 1234 5678 9012", "5555 5555 5555 4444"]
            ),
            EntityDefinition(
                entity_type="organization",
                name="Organization Name",
                description="Names of companies, institutions, and other organizations",
                patterns=[r"\b[A-Z][a-zA-Z\s&,.-]+(?:Inc|LLC|Corp|Company|Ltd|University|College)\b"],
                context_keywords=["company", "organization", "corporation", "institute", "university"],
                sensitivity_level="low",
                examples=["Acme Corporation", "State University", "ABC Company Inc."]
            ),
            EntityDefinition(
                entity_type="address",
                name="Physical Address",
                description="Street addresses, postal addresses, and location information",
                patterns=[r"\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b"],
                context_keywords=["address", "street", "avenue", "road", "location"],
                sensitivity_level="medium",
                examples=["123 Main Street", "456 Oak Avenue"]
            ),
            EntityDefinition(
                entity_type="date",
                name="Date Information",
                description="Dates that might reveal sensitive timing information",
                patterns=[
                    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                    r"\b\d{4}-\d{2}-\d{2}\b",
                    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"
                ],
                context_keywords=["date", "birth", "birthday", "born", "created", "expires"],
                sensitivity_level="medium",
                examples=["01/15/1990", "2023-12-25", "January 1, 2023"]
            ),
            EntityDefinition(
                entity_type="ip_address",
                name="IP Address",
                description="Internet Protocol addresses that may reveal location or system information",
                patterns=[r"\b(?:\d{1,3}\.){3}\d{1,3}\b"],
                context_keywords=["ip", "address", "server", "network"],
                sensitivity_level="medium",
                examples=["192.168.1.1", "10.0.0.1"]
            ),
            EntityDefinition(
                entity_type="url",
                name="URL/Website",
                description="Website URLs and links that may contain sensitive information",
                patterns=[r"https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*)?"],
                context_keywords=["url", "website", "link", "http", "https"],
                sensitivity_level="low",
                examples=["https://example.com", "http://internal.company.com"]
            )
        ]
    
    async def search_definitions(self, query: str, entity_types: List[str] = None) -> List[EntityDefinition]:
        """Search entity definitions using text search"""
        db = get_database()
        if db is None:
            return []
        
        collection = db[self.collection_name]
        
        # Build search filter
        search_filter = {}
        
        if entity_types:
            search_filter["entity_type"] = {"$in": entity_types}
        
        # Add text search
        if query.strip():
            search_filter["$text"] = {"$search": query}
        
        # Execute search
        cursor = collection.find(search_filter)
        if query.strip():
            cursor = cursor.sort([("score", {"$meta": "textScore"})])
        
        results = []
        async for doc in cursor:
            results.append(EntityDefinition.from_dict(doc))
        
        return results
    
    async def get_definition(self, entity_type: str, name: str = None) -> Optional[EntityDefinition]:
        """Get specific entity definition"""
        db = get_database()
        if db is None:
            return None
        
        collection = db[self.collection_name]
        
        filter_dict = {"entity_type": entity_type}
        if name:
            filter_dict["name"] = name
        
        doc = await collection.find_one(filter_dict)
        return EntityDefinition.from_dict(doc) if doc else None
    
    async def add_definition(self, definition: EntityDefinition) -> bool:
        """Add new entity definition"""
        db = get_database()
        if db is None:
            return False
        
        collection = db[self.collection_name]
        
        try:
            await collection.insert_one(definition.to_dict())
            return True
        except Exception as e:
            logger.error(f"Error adding entity definition: {e}")
            return False
    
    async def update_definition(self, entity_type: str, name: str, updates: Dict[str, Any]) -> bool:
        """Update existing entity definition"""
        db = get_database()
        if db is None:
            return False
        
        collection = db[self.collection_name]
        
        try:
            updates["updated_at"] = datetime.utcnow()
            result = await collection.update_one(
                {"entity_type": entity_type, "name": name},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating entity definition: {e}")
            return False

class RAGDetector(BaseDetector):
    """RAG-enhanced detector using knowledge base for improved classification"""
    
    def __init__(self):
        super().__init__("rag_enhanced")
        self.knowledge_base = KnowledgeBase()
        self.context_window = 50  # Characters around potential entity
    
    async def initialize(self):
        """Initialize the RAG detector"""
        await self.knowledge_base.initialize()
    
    async def detect(self, text: str, **kwargs) -> List[DetectionCandidate]:
        """Detect entities using RAG-enhanced approach"""
        candidates = []
        
        # Get relevant entity definitions based on text content
        relevant_definitions = await self._get_relevant_definitions(text)
        
        for definition in relevant_definitions:
            # Apply patterns from knowledge base
            pattern_candidates = await self._apply_definition_patterns(text, definition)
            candidates.extend(pattern_candidates)
            
            # Apply context-based detection
            context_candidates = await self._apply_context_detection(text, definition)
            candidates.extend(context_candidates)
        
        return candidates
    
    async def _get_relevant_definitions(self, text: str) -> List[EntityDefinition]:
        """Get entity definitions relevant to the text"""
        # Extract keywords from text for search
        words = re.findall(r'\b\w+\b', text.lower())
        query_keywords = [word for word in words if len(word) > 3][:10]  # Top 10 keywords
        
        query = " ".join(query_keywords)
        
        # Search knowledge base
        relevant_definitions = await self.knowledge_base.search_definitions(query)
        
        # Also get definitions based on detected patterns
        for definition in await self.knowledge_base.search_definitions(""):
            for pattern in definition.patterns:
                try:
                    if re.search(pattern, text, re.IGNORECASE):
                        if definition not in relevant_definitions:
                            relevant_definitions.append(definition)
                except re.error:
                    continue
        
        return relevant_definitions
    
    async def _apply_definition_patterns(self, text: str, definition: EntityDefinition) -> List[DetectionCandidate]:
        """Apply patterns from entity definition"""
        candidates = []
        
        for pattern in definition.patterns:
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    # Calculate confidence based on pattern quality and context
                    confidence = self._calculate_rag_confidence(match, text, definition)
                    
                    candidate = DetectionCandidate(
                        id=None,
                        type=self._map_entity_type(definition.entity_type),
                        text=match.group(),
                        bbox=None,
                        confidence=confidence,
                        start_char=match.start(),
                        end_char=match.end(),
                        source=self.name,
                        metadata={
                            "rag_definition": definition.name,
                            "pattern_used": pattern,
                            "sensitivity_level": definition.sensitivity_level,
                            "context_match": self._check_context_match(match, text, definition)
                        }
                    )
                    candidates.append(candidate)
                    
            except re.error as e:
                logger.warning(f"Invalid pattern in definition {definition.name}: {e}")
        
        return candidates
    
    async def _apply_context_detection(self, text: str, definition: EntityDefinition) -> List[DetectionCandidate]:
        """Apply context-based detection using keywords"""
        candidates = []
        
        for keyword in definition.context_keywords:
            # Find keyword occurrences
            keyword_pattern = rf'\b{re.escape(keyword)}\b'
            keyword_matches = list(re.finditer(keyword_pattern, text, re.IGNORECASE))
            
            for keyword_match in keyword_matches:
                # Look for potential entities near the keyword
                context_start = max(0, keyword_match.start() - self.context_window)
                context_end = min(len(text), keyword_match.end() + self.context_window)
                context_text = text[context_start:context_end]
                
                # Apply simple heuristics to find potential entities
                potential_entities = self._find_potential_entities_in_context(
                    context_text, definition, context_start
                )
                
                candidates.extend(potential_entities)
        
        return candidates
    
    def _calculate_rag_confidence(self, match, text: str, definition: EntityDefinition) -> float:
        """Calculate confidence score using RAG information"""
        base_confidence = 0.7
        
        # Boost based on sensitivity level
        sensitivity_boost = {
            "low": 0.0,
            "medium": 0.1,
            "high": 0.15,
            "critical": 0.2
        }
        base_confidence += sensitivity_boost.get(definition.sensitivity_level, 0.0)
        
        # Boost for context keyword matches
        if self._check_context_match(match, text, definition):
            base_confidence += 0.15
        
        # Boost for exact example matches
        if match.group().lower() in [ex.lower() for ex in definition.examples]:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _check_context_match(self, match, text: str, definition: EntityDefinition) -> bool:
        """Check if context keywords are present near the match"""
        context_start = max(0, match.start() - self.context_window)
        context_end = min(len(text), match.end() + self.context_window)
        context = text[context_start:context_end].lower()
        
        return any(keyword.lower() in context for keyword in definition.context_keywords)
    
    def _find_potential_entities_in_context(self, context: str, definition: EntityDefinition, offset: int) -> List[DetectionCandidate]:
        """Find potential entities in context using heuristics"""
        candidates = []
        
        # Simple heuristics based on entity type
        if definition.entity_type == "person":
            # Look for capitalized words
            name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        elif definition.entity_type == "organization":
            # Look for title case phrases
            name_pattern = r'\b[A-Z][a-zA-Z\s&,.-]+\b'
        elif definition.entity_type == "location":
            # Look for capitalized location words
            name_pattern = r'\b[A-Z][a-zA-Z\s,-]+\b'
        else:
            return candidates
        
        matches = re.finditer(name_pattern, context)
        
        for match in matches:
            # Skip if it's just the context keyword
            if match.group().lower() in [kw.lower() for kw in definition.context_keywords]:
                continue
            
            candidate = DetectionCandidate(
                id=None,
                type=self._map_entity_type(definition.entity_type),
                text=match.group(),
                bbox=None,
                confidence=0.6,  # Lower confidence for context-based detection
                start_char=offset + match.start(),
                end_char=offset + match.end(),
                source=f"{self.name}_context",
                metadata={
                    "rag_definition": definition.name,
                    "context_based": True,
                    "detection_method": "context_heuristic"
                }
            )
            candidates.append(candidate)
        
        return candidates
    
    def _map_entity_type(self, entity_type_str: str) -> EntityType:
        """Map string entity type to EntityType enum"""
        type_mapping = {
            "person": EntityType.PERSON,
            "email": EntityType.EMAIL,
            "phone": EntityType.PHONE,
            "ssn": EntityType.SSN,
            "credit_card": EntityType.CREDIT_CARD,
            "organization": EntityType.ORGANIZATION,
            "address": EntityType.ADDRESS,
            "date": EntityType.DATE,
            "ip_address": EntityType.IP_ADDRESS,
            "url": EntityType.URL,
            "pan": EntityType.PAN,
            "iban": EntityType.IBAN
        }
        return type_mapping.get(entity_type_str.lower(), EntityType.CUSTOM)
    
    def get_supported_types(self) -> List[EntityType]:
        """Return all possible entity types"""
        return list(EntityType)