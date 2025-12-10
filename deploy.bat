@echo off

REM Create necessary directories
if not exist temp_uploads mkdir temp_uploads
if not exist redacted_outputs mkdir redacted_outputs
if not exist monitoring\prometheus mkdir monitoring\prometheus
if not exist monitoring\grafana\provisioning\datasources mkdir monitoring\grafana\provisioning\datasources
if not exist monitoring\grafana\provisioning\dashboards mkdir monitoring\grafana\provisioning\dashboards

REM Deploy the application using Docker Compose
docker-compose up -d

REM Print access information
echo.
echo PII Detection ^& Redaction System is now running!
echo =================================================
echo API: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo Monitoring:
echo   - Prometheus: http://localhost:9090
echo   - Grafana: http://localhost:3001 (admin/admin)
echo.
echo You can stop the system with: docker-compose down