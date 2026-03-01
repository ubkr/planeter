#!/bin/bash
# For isolated frontend development only.
# In production, FastAPI serves the frontend as static files.

cd "$(dirname "$0")/frontend"

echo "Starting frontend dev server at http://localhost:3000"
echo ""

python3 -m http.server 3000
