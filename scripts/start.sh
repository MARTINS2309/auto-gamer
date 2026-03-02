#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"
DIST_DIR="$WEB_DIR/dist"
HASH_FILE="$DIST_DIR/.build-hash"

# Generate a hash of web source files to detect changes
build_hash() {
    find "$WEB_DIR/src" "$WEB_DIR/index.html" "$WEB_DIR/vite.config.ts" "$WEB_DIR/tsconfig.json" "$WEB_DIR/tsconfig.app.json" \
        -type f 2>/dev/null | sort | xargs cat 2>/dev/null | sha256sum | cut -d' ' -f1
}

# Check if build is needed
needs_build() {
    if [ ! -d "$DIST_DIR" ] || [ ! -f "$HASH_FILE" ]; then
        return 0
    fi
    local current_hash
    current_hash=$(build_hash)
    local stored_hash
    stored_hash=$(cat "$HASH_FILE" 2>/dev/null || echo "")
    [ "$current_hash" != "$stored_hash" ]
}

# Build frontend if needed
if needs_build; then
    echo -e "${YELLOW}Building frontend...${NC}"
    cd "$ROOT_DIR"
    pnpm build
    build_hash > "$HASH_FILE"
    echo -e "${GREEN}Build complete.${NC}"
else
    echo -e "${GREEN}Frontend is up to date, skipping build.${NC}"
fi

# Cleanup on exit
cleanup() {
    echo -e "\n${CYAN}Shutting down...${NC}"
    kill $API_PID 2>/dev/null || true
    kill $WEB_PID 2>/dev/null || true
    wait $API_PID 2>/dev/null || true
    wait $WEB_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start API
echo -e "${CYAN}Starting API server...${NC}"
PORT=8000
EXISTING_PID=$(lsof -ti :$PORT || true)
if [ -n "$EXISTING_PID" ]; then
    echo "Killing existing process on port $PORT"
    kill -9 $EXISTING_PID
fi

cd "$API_DIR"
if [ -f ".gpu-env" ]; then
    source .gpu-env
fi
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Start frontend preview
echo -e "${CYAN}Starting frontend preview server...${NC}"
cd "$ROOT_DIR"
pnpm preview &
WEB_PID=$!

echo -e "${GREEN}Auto-Gamer is running:${NC}"
echo -e "  Frontend: ${CYAN}http://localhost:4173${NC}"
echo -e "  API:      ${CYAN}http://localhost:8000${NC}"
echo ""
echo -e "Press ${YELLOW}Ctrl+C${NC} to stop."

wait
