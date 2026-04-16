#!/usr/bin/env bash
set -e

# Start Ollama in the background
echo "Starting Ollama..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be available
echo "Waiting for Ollama to start..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done

# Build model
echo "Building initial Ollama model from Modelfile if needed..."
bash scripts/build_model.sh

echo "Starting FastAPI app..."
# Exec CMD from Dockerfile
exec "$@"
