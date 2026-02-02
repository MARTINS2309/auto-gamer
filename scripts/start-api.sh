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

cd "$API_DIR"
source .venv/bin/activate

uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
