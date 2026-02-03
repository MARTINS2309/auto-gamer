#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
API_DIR="$ROOT_DIR/apps/api"

echo -e "${GREEN}Starting Retro Runner API...${NC}"

# Kill any existing process on port 8000
PORT=8000
EXISTING_PID=$(lsof -ti :$PORT || true)
if [ ! -z "$EXISTING_PID" ]; then
    echo "Killing process $EXISTING_PID on port $PORT"
    kill -9 $EXISTING_PID
fi

cd "$API_DIR"
source .venv/bin/activate

uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
