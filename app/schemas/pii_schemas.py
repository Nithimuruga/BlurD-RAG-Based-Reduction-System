"""
Schema definitions for PII types, detection configurations, and compliance frameworks.
"""

from enum import Enum, auto
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
import uuid

class PIICategory(str, Enum):
    """Categories of PII for classification and filtering"""
    PERSONAL_IDENTIFIERS = "personal_identifiers"
    CONTACT_INFORMATION = "contact_information"
    FINANCIAL = "financial"
    GOVERNMENT_IDENTIFIERS = "government_identifiers"
    HEALTH = "health"
    PROFESSIONAL = "professional"
    DEMOGRAPHIC = "demographic"
    LOCATION = "location"
    BIOMETRIC = "biometric"
    EDUCATION = "education"
    CUSTOM = "custom"

class PIIType(str, Enum):
    """Expanded list of PII entity types"""
    # Personal identifiers
    PERSON_NAME = "person_name"
    USERNAME = "username"
    PASSWORD = "password"
    
    # Contact information
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    
    # Financial information
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    IBAN = "iban"
    CRYPTO_ADDRESS = "crypto_address"
    FINANCIAL_ACCOUNT = "financial_account"
    
    # Government identifiers
    SSN = "ssn"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    TAX_ID = "tax_id"
    NATIONAL_ID = "national_id"
    
    # Health information
    HEALTH_INSURANCE_ID = "health_insurance_id"
    MEDICAL_RECORD_NUMBER = "medical_record_number"
    PATIENT_ID = "patient_id"
    
    # Professional information
    ORGANIZATION = "organization"
    JOB_TITLE = "job_title"
    EMPLOYEE_ID = "employee_id"
    
    # Demographic information
    DATE_OF_BIRTH = "date_of_birth"
    AGE = "age"
    GENDER = "gender"
    NATIONALITY = "nationality"
    ETHNICITY = "ethnicity"
    
    # Location information
    GPS_COORDINATES = "gps_coordinates"
    IP_ADDRESS = "ip_address"
    LOCATION = "location"
    
    # Biometric data
    BIOMETRIC_DATA = "biometric_data"
    
    # Education information
    EDUCATION = "education"
    STUDENT_ID = "student_id"
    
    # Date and time
    DATE = "date"
    
    # URLs and web data
    URL = "url"
    
    # Custom types
    CUSTOM = "custom"
    
    # Legacy types (for backwards compatibility)
    PAN = "pan"  # Personal Account Number

class ComplianceFramework(str, Enum):
    """Regulatory frameworks for compliance"""
    GDPR = "gdpr"             # General Data Protection Regulation (EU)
    HIPAA = "hipaa"           # Health Insurance Portability and Accountability Act (US)
    CCPA = "ccpa"             # California Consumer Privacy Act
    GLBA = "glba"             # Gramm-Leach-Bliley Act (US)
    FERPA = "ferpa"           # Family Educational Rights and Privacy Act (US)
    PIPEDA = "pipeda"         # Personal Information Protection and Electronic Documents Act (Canada)
    LGPD = "lgpd"             # Lei Geral de Proteção de Dados (Brazil)
    SOC2 = "soc2"             # Service Organization Control 2
    NIST_800_53 = "nist_800_53"  # NIST Special Publication 800-53
    PCI_DSS = "pci_dss"       # Payment Card Industry Data Security Standard
    CUSTOM = "custom"         # Custom compliance framework

class RiskLevel(str, Enum):
    """Risk levels for PII entities"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RedactionStrategy(str, Enum):
    """Available redaction strategies"""
    FULL_REMOVAL = "full_removal"          # Complete removal of PII
    PARTIAL_MASK = "partial_mask"          # Mask part of the value (e.g., XXX-XX-1234)
    FULL_MASK = "full_mask"                # Complete masking (e.g., XXXXXXXXXX)
    TOKENIZATION = "tokenization"          # Replace with token that can be reversed
    PSEUDONYMIZATION = "pseudonymization"  # Replace with consistent but fake value
    GENERALIZATION = "generalization"      # Replace with more general category 
    NONE = "none"                          # No redaction (for testing or review)

class PIITypeDefinition(BaseModel):
    """Detailed definition of a PII type"""
    pii_type: PIIType
    name: str
    description: str
    category: PIICategory
    default_risk_level: RiskLevel = RiskLevel.MEDIUM
    default_redaction_strategy: RedactionStrategy = RedactionStrategy.PARTIAL_MASK
    compliance_frameworks: List[ComplianceFramework] = Field(default_factory=list)
    detection_confidence_threshold: float = 0.7
    regex_patterns: Optional[List[str]] = None
    context_keywords: Optional[List[str]] = None
    validation_function: Optional[str] = None
    examples: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ComplianceRequirement(BaseModel):
    """Definition of a compliance requirement"""
    framework: ComplianceFramework
    name: str
    description: str
    pii_types: List[PIIType]
    required_redaction_strategies: Dict[PIIType, List[RedactionStrategy]] = Field(default_factory=dict)
    required_validation: bool = False
    required_audit_logging: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DetectionOptions(BaseModel):
    """Options for PII detection process"""
    pii_types: List[PIIType] = Field(default_factory=list)
    compliance_frameworks: List[ComplianceFramework] = Field(default_factory=list)
    min_confidence_threshold: float = 0.7
    include_context: bool = True
    max_context_chars: int = 50
    redaction_strategy: RedactionStrategy = RedactionStrategy.PARTIAL_MASK
    skip_validation: bool = False
    custom_settings: Dict[str, Any] = Field(default_factory=dict)

class RedactionOptions(BaseModel):
    """Options for PII redaction process"""
    default_strategy: RedactionStrategy = RedactionStrategy.PARTIAL_MASK
    per_type_strategy: Dict[PIIType, RedactionStrategy] = Field(default_factory=dict)
    mask_char: str = "X"
    preserve_format: bool = True
    preserve_length: bool = True
    tokenization_key: Optional[str] = None
    custom_replacements: Dict[PIIType, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DetectedPII(BaseModel):
    """Representation of detected PII entity with metadata"""
    id: str
    pii_type: PIIType
    text: str
    start_position: int
    end_position: int
    confidence: float
    source_detector: str
    risk_level: RiskLevel
    redaction_strategy: RedactionStrategy
    redacted_text: Optional[str] = None
    validation_status: Optional[bool] = None
    context: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RedactionResult(BaseModel):
    """Result of a redaction operation"""
    original_text: str
    redacted_text: str
    redaction_count: Dict[PIIType, int] = Field(default_factory=dict)
    detected_entities: List[DetectedPII] = Field(default_factory=list)
    processing_time: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PIIDetectionResult(BaseModel):
    """Detailed detection result including statistics and metadata"""
    success: bool
    document_id: Optional[str] = None
    text_length: int
    detected_entities: List[DetectedPII]
    detection_summary: Dict[PIIType, int]
    risk_assessment: Dict[str, Any]
    processing_time: float
    compliance_status: Dict[ComplianceFramework, bool] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AuditLogEntry(BaseModel):
    """Audit log entry for tracking PII operations"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    operation: str
    user_id: Optional[str] = None
    document_id: Optional[str] = None
    pii_types_processed: List[PIIType] = Field(default_factory=list)
    entity_count: int = 0
    success: bool
    compliance_frameworks: List[ComplianceFramework] = Field(default_factory=list)
    source_ip: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class PIITypeSelection(BaseModel):
    """User selection of PII types to detect or redact"""
    pii_types: List[PIIType] = Field(default_factory=list)
    include_all: bool = False
    exclude_types: List[PIIType] = Field(default_factory=list)
    custom_types: List[Dict[str, Any]] = Field(default_factory=list)
    
class PIIDetectionRequest(BaseModel):
    """Request for PII detection"""
    text: Optional[str] = None
    file_path: Optional[str] = None
    file_url: Optional[HttpUrl] = None
    pii_types: Optional[List[str]] = None
    compliance_frameworks: Optional[List[str]] = None
    min_confidence: Optional[float] = 0.7
    include_context: bool = True
    document_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class RedactionRequest(BaseModel):
    """Request for PII redaction"""
    text: Optional[str] = None
    file_path: Optional[str] = None
    file_url: Optional[HttpUrl] = None
    pii_types: Optional[List[str]] = None
    compliance_frameworks: Optional[List[str]] = None
    redaction_strategy: Optional[str] = "mask"
    output_format: Optional[str] = None
    include_detection_details: bool = False
    document_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = Field(default_factory=dict)