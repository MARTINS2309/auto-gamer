/**
 * Console icon utilities
 * Icons are downloaded from RetroArch assets via scripts/download-resources.sh
 */

// Map stable-retro system names to icon file names
const SYSTEM_ICONS: Record<string, string> = {
  Nes: "nes",
  Snes: "snes",
  Genesis: "genesis",
  Gb: "gb",
  Gbc: "gbc",
  Gba: "gba",
  N64: "n64",
  Atari2600: "atari2600",
  GameGear: "gamegear",
  Sms: "sms",
  PCEngine: "pcengine",
  Saturn: "saturn",
  "32x": "32x",
}

// Friendly display names for systems
export const SYSTEM_NAMES: Record<string, string> = {
  Nes: "NES",
  Snes: "SNES",
  Genesis: "Genesis",
  Gb: "Game Boy",
  Gbc: "Game Boy Color",
  Gba: "Game Boy Advance",
  N64: "Nintendo 64",
  Atari2600: "Atari 2600",
  GameGear: "Game Gear",
  Sms: "Master System",
  PCEngine: "PC Engine",
  Saturn: "Saturn",
  "32x": "32X",
}

/**
 * Get the icon URL for a console system
 * Returns undefined if no icon is available
 */
export function getConsoleIconUrl(system: string): string | undefined {
  const iconName = SYSTEM_ICONS[system]
  if (!iconName) return undefined
  return `/resources/console-icons/${iconName}.png`
}

/**
 * Get the display name for a system
 */
export function getSystemDisplayName(system: string): string {
  return SYSTEM_NAMES[system] ?? system
}
