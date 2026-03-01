#!/bin/bash
# Start the Planeter server

cd "$(dirname "$0")/backend"

# Activate virtual environment
source venv/bin/activate

# Start server
echo "Starting Planeter application..."
echo "Application will be available at http://localhost:8000"
echo "API docs at http://localhost:8000/docs"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
