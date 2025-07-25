#!/bin/bash
set -e

echo "Starting desktop environment..."
./start_all.sh
./novnc_startup.sh

sleep 2

echo "✨ Computer Use Demo Backend is starting!"

# Start FastAPI on port 8000 (replacing the original HTTP server)
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info