#!/bin/bash
set -e

# Default values
PORT=${PORT:-5000}
OUTPUT_DIR=${OUTPUT_DIR:-/app/output}
WORKERS=${WORKERS:-2}
THREADS=${THREADS:-4}

echo "Starting OpenAPI to MCP Generator Web Service..."
echo "  Port: $PORT"
echo "  Output Directory: $OUTPUT_DIR"
echo "  Workers: $WORKERS"
echo "  Threads: $THREADS"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Set environment variables for the app
export OUTPUT_DIR
export PORT

# Run with gunicorn for production
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WORKERS}" \
    --threads "${THREADS}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    "src.openapi_to_mcp.gui.web_app:create_standalone_app()"
