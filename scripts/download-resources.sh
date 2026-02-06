#!/bin/bash
set -e

# =============================================================================
# Resource Download Script
# Downloads external assets that are not committed to git
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo -e "${CYAN}=== Downloading External Resources ===${NC}"
echo ""

# =============================================================================
# Console Icons (RetroArch XMB Monochrome)
# Source: https://github.com/libretro/retroarch-assets
# =============================================================================

ICONS_DIR="$ROOT_DIR/apps/web/public/resources/console-icons"
RETROARCH_ASSETS_URL="https://raw.githubusercontent.com/libretro/retroarch-assets/master/xmb/monochrome/png"

echo -e "${YELLOW}[1/3] Downloading console icons...${NC}"

mkdir -p "$ICONS_DIR"

# Map stable-retro system names to RetroArch icon names
declare -A SYSTEM_MAP=(
    ["Nes"]="Nintendo - Nintendo Entertainment System"
    ["Snes"]="Nintendo - Super Nintendo Entertainment System"
    ["Genesis"]="Sega - Mega Drive - Genesis"
    ["Gb"]="Nintendo - Game Boy"
    ["Gbc"]="Nintendo - Game Boy Color"
    ["Gba"]="Nintendo - Game Boy Advance"
    ["N64"]="Nintendo - Nintendo 64"
    ["Atari2600"]="Atari - 2600"
    ["GameGear"]="Sega - Game Gear"
    ["Sms"]="Sega - Master System - Mark III"
    ["PCEngine"]="NEC - PC Engine - TurboGrafx 16"
    ["Saturn"]="Sega - Saturn"
    ["32x"]="Sega - 32X"
)

for system in "${!SYSTEM_MAP[@]}"; do
    icon_name="${SYSTEM_MAP[$system]}"
    encoded_name=$(echo "$icon_name" | sed 's/ /%20/g')
    output_file="$ICONS_DIR/${system,,}.png"

    if [ ! -f "$output_file" ]; then
        echo "  Downloading: $system"
        curl -sL "${RETROARCH_ASSETS_URL}/${encoded_name}.png" -o "$output_file" 2>/dev/null || {
            echo -e "  ${RED}Failed: $system${NC}"
            rm -f "$output_file"
        }
    else
        echo "  Skipping (exists): $system"
    fi
done

echo -e "${GREEN}Console icons downloaded to: $ICONS_DIR${NC}"
echo ""

# =============================================================================
# LibRetro Thumbnail Database Index (optional, for offline matching)
# =============================================================================

THUMB_INDEX_DIR="$ROOT_DIR/apps/api/data/libretro_index"

echo -e "${YELLOW}[2/3] LibRetro thumbnail index...${NC}"

if [ ! -d "$THUMB_INDEX_DIR" ]; then
    echo "  Thumbnail index will be built on first sync (fetched on-demand)"
    echo "  To pre-build: run the API and trigger a sync"
else
    echo "  Index already exists"
fi

echo ""

# =============================================================================
# Summary
# =============================================================================

echo -e "${YELLOW}[3/3] Resource summary...${NC}"
echo ""
echo "Downloaded resources:"
echo "  - Console icons: $ICONS_DIR"
echo ""
echo "User-supplied resources (not downloaded):"
echo "  - ROMs: Configure roms_path in Settings"
echo "  - Thumbnails: Fetched from LibRetro/IGDB on sync"
echo ""
echo -e "${GREEN}=== Resource Download Complete ===${NC}"
echo ""
