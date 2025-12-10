# PII Detection and Redaction System

A comprehensive system for detecting and redacting Personally Identifiable Information (PII) in various document formats, with support for compliance frameworks like GDPR, HIPAA, PCI-DSS, and CCPA.

## Features

- **Multiple PII Types**: Detect and redact various PII types including names, emails, phone numbers, financial data, healthcare information, and more
- **Multi-Format Support**: Process text, PDFs, images (with OCR), databases, and live streams
- **Compliance Frameworks**: Built-in support for GDPR, HIPAA, PCI-DSS, and CCPA compliance requirements
- **Redaction Strategies**: Multiple redaction techniques including masking, tokenization, and pseudonymization
- **Domain-Specific Detection**: Specialized detectors for healthcare and financial data
- **Multi-Output Format**: Generate redacted files in PDF, DOCX, JSON, CSV, and plain text formats
- **API-First Design**: RESTful APIs for integration with other systems
- **Monitoring**: Built-in monitoring with Prometheus and Grafana
- **Docker Support**: Easy deployment with Docker and Docker Compose

## Tech Stack

- **Backend**: FastAPI with Python 3.11
- **Database**: MongoDB
- **ML/NLP**: spaCy and Hugging Face Transformers
- **OCR**: Tesseract
- **Document Processing**: PyPDF2, python-docx, Pandas
- **Monitoring**: Prometheus and Grafana
- **Deployment**: Docker and Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)

### Quick Start

1. Clone the repository
2. Run the deployment script:

   ```bash
   # On Linux/Mac
   ./deploy.sh
   
   # On Windows
   deploy.bat
   ```

3. Access the services:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Frontend: http://localhost:3000
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3001 (admin/admin)

### Manual Setup for Development

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Start MongoDB (or use Docker):

   ```bash
   docker run -d -p 27017:27017 --name mongodb mongo:6
   ```

3. Run the FastAPI server:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Install frontend dependencies and start the development server:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## API Endpoints

### PII Detection and Redaction

- `POST /pii/detect` - Detect PII in text or uploaded files
- `POST /pii/redact` - Detect and redact PII
- `POST /pii/redact/download` - Redact PII and download the result
- `GET /pii/compliance/check` - Check compliance with specified frameworks
- `POST /pii/audit/log` - Create an audit log entry
- `GET /pii/audit/logs` - Get audit logs with filtering

## Project Structure

```
├── app/
│   ├── main.py           # FastAPI application
│   ├── routers/          # API routes
│   ├── schemas/          # Pydantic models
│   ├── services/         # Business logic
│   └── utils/            # Utilities
├── frontend/             # React frontend
├── monitoring/           # Prometheus & Grafana configuration
├── redacted_outputs/     # Output directory for redacted files
├── temp_uploads/         # Temporary file uploads
├── docker-compose.yml    # Docker Compose configuration
└── Dockerfile            # Docker configuration
```

## Compliance Frameworks

- **GDPR**: General Data Protection Regulation
- **HIPAA**: Health Insurance Portability and Accountability Act
- **PCI-DSS**: Payment Card Industry Data Security Standard
- **CCPA**: California Consumer Privacy Act

## PII Types Supported

- Names (personal and business)
- Addresses (physical, email)
- Phone numbers
- Financial data (credit cards, bank accounts)
- Government IDs (SSN, passport, driver's license)
- Healthcare information (MRN, health insurance IDs)
- IP addresses
- Dates of birth
- And many more...
````
