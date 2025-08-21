#!/bin/bash
set -e

echo "Starting desktop environment..."
./start_all.sh
./novnc_startup.sh

sleep 2

echo "✨ Computer Use Demo Backend is starting!"

# Ensure Python environment is set up correctly
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Set PYTHONPATH to include current directory
export PYTHONPATH=$HOME

# Debug: Check if uvicorn is available
echo "Python version: $(python --version)"
echo "Python path: $(which python)"
echo "Checking uvicorn installation..."
python -c "import uvicorn; print(f'uvicorn version: {uvicorn.__version__}')" || echo "uvicorn not found in Python"

# Gunicorn args (input from Dockerfile)
GUNICORN_WORKERS=${GUNICORN_WORKERS:-1}

# Starting FastAPI server with gunicorn using uvicorn workers
echo "Starting FastAPI server with gunicorn + uvicorn workers..."
exec python -m gunicorn backend.main:app \
    --bind 0.0.0.0:8000 \
    --workers $GUNICORN_WORKERS \
    --worker-class uvicorn.workers.UvicornWorker
