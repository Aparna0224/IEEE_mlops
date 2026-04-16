#!/usr/bin/env bash
set -e

# Default to paper-model-vX based on timestamp if none provided
VERSION_NAME=${1:-"paper-model-$(date +%s)"}
REGISTRY_FILE="models/model_registry.json"

echo "Building Ollama model version: $VERSION_NAME..."

# Ensure we're in root
cd "$(dirname "$0")/.."

# Build the model using Ollama
ollama create "$VERSION_NAME" -f models/Modelfile

echo "Model $VERSION_NAME created successfully."

# Update registry (very basic JSON update)
python3 -c "
import json
import os

registry_path = 'models/model_registry.json'
if not os.path.exists(registry_path):
    data = {'active_model': '', 'available_models': []}
else:
    with open(registry_path, 'r') as f:
        data = json.load(f)

model_name = '$VERSION_NAME'
if model_name not in data['available_models']:
    data['available_models'].append(model_name)
data['active_model'] = model_name

with open(registry_path, 'w') as f:
    json.dump(data, f, indent=2)
"

echo "Updated $REGISTRY_FILE. Active model is now $VERSION_NAME"
