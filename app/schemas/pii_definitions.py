"""
Default PII type definitions and compliance requirements.
This module provides standard definitions for PII types and compliance frameworks
that can be used throughout the application.
"""

from typing import Dict, List
from app.schemas.pii_schemas import (
    PIITypeDefinition, ComplianceRequirement, PIIType,
    PIICategory, RiskLevel, RedactionStrategy, ComplianceFramework
)

# Default PII type definitions
DEFAULT_PII_TYPE_DEFINITIONS: Dict[PIIType, PIITypeDefinition] = {
    # Personal identifiers
    PIIType.PERSON_NAME: PIITypeDefinition(
        pii_type=PIIType.PERSON_NAME,
        name="Person Name",
        description="Full name of an individual",
        category=PIICategory.PERSONAL_IDENTIFIERS,
        default_risk_level=RiskLevel.MEDIUM,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.GDPR, 
            ComplianceFramework.CCPA
        ],
        regex_patterns=[
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Simple first last pattern
            r'\b[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+\b',  # First middle-initial last
        ],
        context_keywords=["name", "full name", "employee name", "customer name"],
        examples=["John Smith", "Jane A. Doe"]
    ),
    
    # Contact information
    PIIType.EMAIL: PIITypeDefinition(
        pii_type=PIIType.EMAIL,
        name="Email Address",
        description="Electronic mail address",
        category=PIICategory.CONTACT_INFORMATION,
        default_risk_level=RiskLevel.MEDIUM,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.GDPR,
            ComplianceFramework.CCPA
        ],
        regex_patterns=[
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ],
        context_keywords=["email", "e-mail", "email address", "contact"],
        examples=["user@example.com", "john.doe@company.org"]
    ),
    
    PIIType.PHONE: PIITypeDefinition(
        pii_type=PIIType.PHONE,
        name="Phone Number",
        description="Telephone or mobile phone number",
        category=PIICategory.CONTACT_INFORMATION,
        default_risk_level=RiskLevel.MEDIUM,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.GDPR,
            ComplianceFramework.CCPA
        ],
        regex_patterns=[
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # North American format
            r'\b\+\d{1,3}[-.\s]?\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b',  # International format
        ],
        context_keywords=["phone", "telephone", "mobile", "cell", "contact number"],
        examples=["555-123-4567", "+1 555 123 4567"]
    ),
    
    PIIType.ADDRESS: PIITypeDefinition(
        pii_type=PIIType.ADDRESS,
        name="Physical Address",
        description="Street address or mailing address",
        category=PIICategory.CONTACT_INFORMATION,
        default_risk_level=RiskLevel.MEDIUM,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.GDPR,
            ComplianceFramework.CCPA
        ],
        # Regex patterns for addresses are complex, better to use NER
        context_keywords=["address", "street", "avenue", "boulevard", "road", "apartment", "suite"],
        examples=["123 Main St, Anytown, CA 12345", "Apt 4B, 567 Oak Road"]
    ),
    
    # Financial information
    PIIType.CREDIT_CARD: PIITypeDefinition(
        pii_type=PIIType.CREDIT_CARD,
        name="Credit Card Number",
        description="Payment card number",
        category=PIICategory.FINANCIAL,
        default_risk_level=RiskLevel.HIGH,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.PCI_DSS,
            ComplianceFramework.GDPR,
            ComplianceFramework.CCPA
        ],
        regex_patterns=[
            # Visa
            r'\b4[0-9]{12}(?:[0-9]{3})?\b',
            # Mastercard
            r'\b5[1-5][0-9]{14}\b',
            # American Express
            r'\b3[47][0-9]{13}\b',
            # Discover
            r'\b6(?:011|5[0-9]{2})[0-9]{12}\b',
            # With common separators
            r'\b(?:4[0-9]{3}|5[1-5][0-9]{2}|6(?:011|5[0-9]{2})|3[47][0-9]{2})[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}\b'
        ],
        context_keywords=["credit card", "card number", "payment card", "visa", "mastercard", "amex"],
        examples=["4111-1111-1111-1111", "5500 0000 0000 0004"]
    ),
    
    PIIType.BANK_ACCOUNT: PIITypeDefinition(
        pii_type=PIIType.BANK_ACCOUNT,
        name="Bank Account Number",
        description="Bank account number",
        category=PIICategory.FINANCIAL,
        default_risk_level=RiskLevel.HIGH,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.GLBA,
            ComplianceFramework.GDPR
        ],
        regex_patterns=[
            r'\b[0-9]{8,17}\b'  # Common bank account number lengths
        ],
        context_keywords=["bank account", "account number", "checking account", "savings account"],
        examples=["12345678", "987654321012345"]
    ),
    
    # Government identifiers
    PIIType.SSN: PIITypeDefinition(
        pii_type=PIIType.SSN,
        name="Social Security Number",
        description="US Social Security Number",
        category=PIICategory.GOVERNMENT_IDENTIFIERS,
        default_risk_level=RiskLevel.CRITICAL,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.HIPAA,
            ComplianceFramework.GDPR,
            ComplianceFramework.CCPA,
        ],
        regex_patterns=[
            r'\b\d{3}-\d{2}-\d{4}\b',  # XXX-XX-XXXX
            r'\b\d{3}\s\d{2}\s\d{4}\b',  # XXX XX XXXX
            r'\bSSN:?\s*\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'  # SSN: XXX-XX-XXXX
        ],
        context_keywords=["ssn", "social security", "social security number"],
        examples=["123-45-6789", "SSN: 123-45-6789"]
    ),
    
    PIIType.PASSPORT: PIITypeDefinition(
        pii_type=PIIType.PASSPORT,
        name="Passport Number",
        description="Government issued passport number",
        category=PIICategory.GOVERNMENT_IDENTIFIERS,
        default_risk_level=RiskLevel.HIGH,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.GDPR
        ],
        regex_patterns=[
            r'\b[A-Z]{1,2}[0-9]{6,9}\b'  # Common passport formats
        ],
        context_keywords=["passport", "passport number", "travel document"],
        examples=["A12345678", "AB1234567"]
    ),
    
    PIIType.DRIVERS_LICENSE: PIITypeDefinition(
        pii_type=PIIType.DRIVERS_LICENSE,
        name="Driver's License Number",
        description="Government issued driver's license number",
        category=PIICategory.GOVERNMENT_IDENTIFIERS,
        default_risk_level=RiskLevel.HIGH,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.GDPR,
            ComplianceFramework.CCPA
        ],
        regex_patterns=[
            # Varies widely by region
            r'\b[A-Z][0-9]{7}\b',  # Common US format
            r'\b[A-Z]{1,2}[0-9]{4,7}\b'  # Other common formats
        ],
        context_keywords=["driver's license", "drivers license", "driving license", "dl number"],
        examples=["D1234567", "AB123456"]
    ),
    
    # Health information
    PIIType.HEALTH_INSURANCE_ID: PIITypeDefinition(
        pii_type=PIIType.HEALTH_INSURANCE_ID,
        name="Health Insurance ID",
        description="Health insurance identifier or policy number",
        category=PIICategory.HEALTH,
        default_risk_level=RiskLevel.HIGH,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.HIPAA
        ],
        regex_patterns=[
            r'\b[A-Z0-9]{6,12}\b'  # General pattern, varies by provider
        ],
        context_keywords=["health insurance", "insurance ID", "insurance policy", "policy number"],
        examples=["ABC123456789", "XYZ98765432"]
    ),
    
    # Professional information
    PIIType.ORGANIZATION: PIITypeDefinition(
        pii_type=PIIType.ORGANIZATION,
        name="Organization Name",
        description="Name of company, business, or organization",
        category=PIICategory.PROFESSIONAL,
        default_risk_level=RiskLevel.LOW,
        default_redaction_strategy=RedactionStrategy.NONE,
        compliance_frameworks=[],
        context_keywords=["company", "organization", "business", "corporation", "employer"],
        examples=["Acme Corporation", "Global Enterprises Ltd."]
    ),
    
    # Location information
    PIIType.IP_ADDRESS: PIITypeDefinition(
        pii_type=PIIType.IP_ADDRESS,
        name="IP Address",
        description="Internet Protocol address",
        category=PIICategory.LOCATION,
        default_risk_level=RiskLevel.MEDIUM,
        default_redaction_strategy=RedactionStrategy.FULL_MASK,
        compliance_frameworks=[
            ComplianceFramework.GDPR
        ],
        regex_patterns=[
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IPv4
            r'\b([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}\b'  # Simple IPv6 pattern
        ],
        context_keywords=["IP", "IP address", "IPv4", "IPv6"],
        examples=["192.168.1.1", "2001:0db8:85a3:0000:0000:8a2e:0370:7334"]
    ),
    
    # Date and time
    PIIType.DATE_OF_BIRTH: PIITypeDefinition(
        pii_type=PIIType.DATE_OF_BIRTH,
        name="Date of Birth",
        description="Person's birth date",
        category=PIICategory.DEMOGRAPHIC,
        default_risk_level=RiskLevel.HIGH,
        default_redaction_strategy=RedactionStrategy.PARTIAL_MASK,
        compliance_frameworks=[
            ComplianceFramework.HIPAA,
            ComplianceFramework.GDPR
        ],
        regex_patterns=[
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'  # Month DD, YYYY
        ],
        context_keywords=["birth date", "birthdate", "date of birth", "born on", "DOB"],
        examples=["01/15/1990", "January 15, 1990", "15/01/1990"]
    ),
    
    # URL and web data
    PIIType.URL: PIITypeDefinition(
        pii_type=PIIType.URL,
        name="URL",
        description="Uniform Resource Locator (web address)",
        category=PIICategory.CUSTOM,
        default_risk_level=RiskLevel.LOW,
        default_redaction_strategy=RedactionStrategy.NONE,
        compliance_frameworks=[],
        regex_patterns=[
            r'\bhttps?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*\b'
        ],
        context_keywords=["website", "URL", "web address", "link"],
        examples=["https://example.com", "http://subdomain.example.org/path"]
    ),
}

# Default compliance framework requirements
DEFAULT_COMPLIANCE_REQUIREMENTS: Dict[ComplianceFramework, ComplianceRequirement] = {
    ComplianceFramework.GDPR: ComplianceRequirement(
        framework=ComplianceFramework.GDPR,
        name="General Data Protection Regulation",
        description="EU regulation on data protection and privacy",
        pii_types=[
            PIIType.PERSON_NAME, PIIType.EMAIL, PIIType.PHONE, PIIType.ADDRESS,
            PIIType.IP_ADDRESS, PIIType.DATE_OF_BIRTH, PIIType.PASSPORT,
            PIIType.DRIVERS_LICENSE
        ],
        required_redaction_strategies={
            PIIType.PERSON_NAME: [RedactionStrategy.PARTIAL_MASK, RedactionStrategy.PSEUDONYMIZATION],
            PIIType.EMAIL: [RedactionStrategy.PARTIAL_MASK],
            PIIType.PHONE: [RedactionStrategy.PARTIAL_MASK],
            PIIType.PASSPORT: [RedactionStrategy.PARTIAL_MASK, RedactionStrategy.FULL_MASK]
        },
        required_validation=True,
        required_audit_logging=True
    ),
    
    ComplianceFramework.HIPAA: ComplianceRequirement(
        framework=ComplianceFramework.HIPAA,
        name="Health Insurance Portability and Accountability Act",
        description="US regulation for medical information privacy",
        pii_types=[
            PIIType.PERSON_NAME, PIIType.PHONE, PIIType.EMAIL, PIIType.ADDRESS,
            PIIType.SSN, PIIType.HEALTH_INSURANCE_ID, PIIType.MEDICAL_RECORD_NUMBER,
            PIIType.PATIENT_ID, PIIType.DATE_OF_BIRTH
        ],
        required_redaction_strategies={
            PIIType.HEALTH_INSURANCE_ID: [RedactionStrategy.FULL_MASK, RedactionStrategy.TOKENIZATION],
            PIIType.PATIENT_ID: [RedactionStrategy.FULL_MASK, RedactionStrategy.TOKENIZATION],
            PIIType.MEDICAL_RECORD_NUMBER: [RedactionStrategy.FULL_MASK]
        },
        required_validation=True,
        required_audit_logging=True
    ),
    
    ComplianceFramework.PCI_DSS: ComplianceRequirement(
        framework=ComplianceFramework.PCI_DSS,
        name="Payment Card Industry Data Security Standard",
        description="Information security standard for payment card processing",
        pii_types=[
            PIIType.CREDIT_CARD, PIIType.BANK_ACCOUNT, PIIType.PERSON_NAME
        ],
        required_redaction_strategies={
            PIIType.CREDIT_CARD: [RedactionStrategy.PARTIAL_MASK],
            PIIType.BANK_ACCOUNT: [RedactionStrategy.PARTIAL_MASK, RedactionStrategy.TOKENIZATION]
        },
        required_validation=True,
        required_audit_logging=True
    ),
    
    ComplianceFramework.CCPA: ComplianceRequirement(
        framework=ComplianceFramework.CCPA,
        name="California Consumer Privacy Act",
        description="California regulation for consumer privacy rights",
        pii_types=[
            PIIType.PERSON_NAME, PIIType.EMAIL, PIIType.PHONE, PIIType.ADDRESS,
            PIIType.SSN, PIIType.DRIVERS_LICENSE
        ],
        required_redaction_strategies={},
        required_validation=True,
        required_audit_logging=True
    ),
}