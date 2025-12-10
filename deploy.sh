#!/bin/sh

# Create necessary directories
mkdir -p temp_uploads redacted_outputs monitoring/prometheus monitoring/grafana/provisioning/datasources monitoring/grafana/provisioning/dashboards

# Deploy the application using Docker Compose
docker-compose up -d

# Print access information
echo ""
echo "PII Detection & Redaction System is now running!"
echo "================================================="
echo "API: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
echo "Monitoring:"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3001 (admin/admin)"
echo ""
echo "You can stop the system with: docker-compose down"