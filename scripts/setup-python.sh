#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
API_DIR="$ROOT_DIR/apps/api"
RETRO_DIR="$ROOT_DIR/packages/stable-retro"

cd "$API_DIR"

echo -e "${YELLOW}Creating Python 3.10 virtual environment...${NC}"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    python3.10 -m venv .venv
    echo "Virtual environment created at apps/api/.venv (Python 3.10)"
else
    echo "Virtual environment already exists"
fi

# Activate venv
source .venv/bin/activate

echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

echo -e "${YELLOW}Detecting GPU and installing PyTorch...${NC}"
"$SCRIPT_DIR/setup-gpu.sh"

echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt

echo -e "${YELLOW}Installing stable-retro from source (this may take a while)...${NC}"
cd "$RETRO_DIR"
pip install -e .

echo ""
echo -e "${GREEN}Python environment setup complete.${NC}"
echo ""
echo "To activate the environment manually:"
echo "  source apps/api/.venv/bin/activate"
echo ""
