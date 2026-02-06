#!/bin/bash
set -e

echo "=== Auto-Gamer Setup ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo -e "${YELLOW}Step 1: Installing system dependencies...${NC}"
echo "This requires sudo access."
echo ""

sudo apt-get update
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y \
    python3.10 python3.10-venv python3.10-dev \
    build-essential cmake pkg-config \
    zlib1g-dev libopenmpi-dev ffmpeg \
    libzip-dev liblua5.3-dev \
    libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev \
    git

echo ""
echo -e "${GREEN}System dependencies installed.${NC}"
echo ""

echo -e "${YELLOW}Step 2: Installing pnpm dependencies...${NC}"
pnpm install

echo ""
echo -e "${GREEN}pnpm dependencies installed.${NC}"
echo ""

echo -e "${YELLOW}Step 3: Setting up Python environment...${NC}"
./scripts/setup-python.sh

echo ""
echo -e "${YELLOW}Step 4: Downloading external resources...${NC}"
./scripts/download-resources.sh

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Available commands:"
echo "  pnpm dev        - Start frontend (Vite)"
echo "  pnpm dev:api    - Start backend (FastAPI)"
echo "  pnpm dev:all    - Start both frontend and backend"
echo "  pnpm mgba       - Launch mGBA emulator"
echo "  pnpm mgba:script - Launch mGBA with AI control script"
echo ""
