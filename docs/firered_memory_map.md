# Pokemon FireRed USA v1.0 - Complete Memory Map

Reference for AI runner's primary perception system. All addresses are for USA v1.0 (1636).

Sources:
- [Data Crystal RAM Map](https://datacrystal.tcrf.net/wiki/Pok%C3%A9mon_3rd_Generation/Pok%C3%A9mon_FireRed_and_LeafGreen/RAM_map)
- [PokeCommunity RAM Offset List](https://www.pokecommunity.com/threads/pokemon-firered-ram-offset-list.342546/)
- [Bulbapedia Gen III Pokemon Structure](https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_structure_(Generation_III))
- [Bulbapedia Gen III Save Structure](https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III))

---

## Quick Reference - Most Used Addresses

| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x02036E38 | 2 | PLAYER_X | Player X coordinate on map |
| 0x02036E3A | 2 | PLAYER_Y | Player Y coordinate on map |
| 0x02036E3C | 1 | PLAYER_DIR | Direction (0=down,1=up,2=left,3=right) |
| 0x02036E34 | 1 | MAP_BANK | Current map bank |
| 0x02036E36 | 1 | MAP_NUM | Current map number |
| 0x02022B4C | 4 | BATTLE_FLAG | Battle active (0=overworld, >0=battle) |
| 0x02024029 | 1 | PARTY_COUNT | Number of Pokemon in party (0-6) |
| 0x02025000 | 4 | MONEY | Player money (XOR encrypted) |
| 0x02025028 | 1 | BADGES | Badge flags (bit 0=Boulder, etc) |
| 0x020204B4 | 1 | TEXT_BOX | Text box active flag |
| 0x0203ADB8 | 1 | MENU_STATE | Menu open state |

---

## 1. Player State

### Position & Movement
| Address | Size | Name | Values |
|---------|------|------|--------|
| 0x02036E38 | 2 | PLAYER_X | X coordinate (0-65535) |
| 0x02036E3A | 2 | PLAYER_Y | Y coordinate (0-65535) |
| 0x02036E3C | 1 | PLAYER_DIR | 0=down, 1=up, 2=left, 3=right |
| 0x02037078 | 1 | PLAYER_SPEED | Movement speed (3 LSBs) |
| 0x02037079 | 1 | BIKE_FLAG | Bike transformation state |
| 0x0203707A | 1 | DPAD_STATE | D-pad button press state |
| 0x0203707B | 1 | MOVE_STATE | Player movement state |
| 0x0203707E | 1 | CTRL_LOCKED | Movement lock (0x01=locked) |
| 0x020370D0 | 1 | SCRIPT_LOCK | Script locking player control |

### Map Data
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x02036E34 | 1 | MAP_BANK | Map bank number |
| 0x02036E36 | 1 | MAP_NUM | Map number within bank |
| 0x02036DFC | ? | MAP_HEADER | Current map header data |
| 0x02031DB4 | 1 | PREV_MAP_BANK | Previous map bank |
| 0x02031DB5 | 1 | PREV_MAP_NUM | Previous map number |
| 0x02031DB6 | 1 | PREV_WARP | Previous warp ID |
| 0x02031DB8 | 2 | PREV_X | Previous X coordinate |
| 0x02031DBA | 2 | PREV_Y | Previous Y coordinate |

### Trainer Info (via 0x0300500C pointer)
| Offset | Size | Name | Description |
|--------|------|------|-------------|
| +0x0000 | 8 | NAME | Player name (FF-terminated) |
| +0x0008 | 1 | GENDER | 0=male, 1=female |
| +0x000A | 2 | TRAINER_ID | Visible trainer ID |
| +0x000C | 2 | SECRET_ID | Secret ID |
| +0x000E | 2 | PLAY_HOURS | Playtime hours |
| +0x0010 | 1 | PLAY_MINS | Playtime minutes |
| +0x0011 | 1 | PLAY_SECS | Playtime seconds |

### Direct Trainer Addresses
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x020245CC | 8 | PLAYER_NAME | Player name string |
| 0x02028F78 | 8 | RIVAL_NAME | Rival name string |
| 0x02024EA4 | 8 | PLAYER_NAME_ALT | Alternative player name addr |
| 0x02024EAC | 4 | TRAINER_ID_FULL | Full trainer ID |
| 0x02024EAE | 2 | PLAY_TIME_H | Play time hours |
| 0x02024EB0 | 1 | PLAY_TIME_M | Play time minutes |
| 0x02024EB2 | 1 | PLAY_TIME_S | Play time seconds |

---

## 2. Party Pokemon

### Party Overview
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x02024029 | 1 | PARTY_COUNT | Pokemon in party (0-6) |
| 0x02024284 | 600 | PARTY_DATA | Full party data (6 x 100 bytes) |

### Party Pokemon Addresses (100 bytes each)
| Slot | Address | Description |
|------|---------|-------------|
| 1 | 0x02024284 | First party Pokemon |
| 2 | 0x020242E8 | Second party Pokemon |
| 3 | 0x0202434C | Third party Pokemon |
| 4 | 0x020243B0 | Fourth party Pokemon |
| 5 | 0x02024414 | Fifth party Pokemon |
| 6 | 0x02024478 | Sixth party Pokemon |

### Pokemon Data Structure (100 bytes)
| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0x00 | 4 | PERSONALITY | Personality value (nature, gender, etc) |
| 0x04 | 4 | OT_ID | Original trainer ID |
| 0x08 | 10 | NICKNAME | Pokemon nickname |
| 0x12 | 1 | LANGUAGE | Language of origin |
| 0x13 | 1 | FLAGS | Bad egg, has species flags |
| 0x14 | 7 | OT_NAME | Original trainer name |
| 0x1B | 1 | MARKINGS | Box markings |
| 0x1C | 2 | CHECKSUM | Data checksum |
| 0x1E | 2 | PADDING | Usually 0 |
| 0x20 | 48 | DATA | Encrypted data block |
| 0x50 | 4 | STATUS | Status condition |
| 0x54 | 1 | LEVEL | Current level |
| 0x55 | 1 | MAIL_ID | Mail ID (0xFF if none) |
| 0x56 | 2 | CURRENT_HP | Current HP |
| 0x58 | 2 | MAX_HP | Maximum HP |
| 0x5A | 2 | ATTACK | Attack stat |
| 0x5C | 2 | DEFENSE | Defense stat |
| 0x5E | 2 | SPEED | Speed stat |
| 0x60 | 2 | SP_ATK | Special Attack stat |
| 0x62 | 2 | SP_DEF | Special Defense stat |

### Quick Party Stat Addresses (Slot 1)
| Address | Size | Name |
|---------|------|------|
| 0x02024284 | 4 | POKE1_PERSONALITY |
| 0x020242D4 | 4 | POKE1_STATUS |
| 0x020242D8 | 1 | POKE1_LEVEL |
| 0x020242DA | 2 | POKE1_HP |
| 0x020242DC | 2 | POKE1_MAX_HP |
| 0x020242DE | 2 | POKE1_ATK |
| 0x020242E0 | 2 | POKE1_DEF |
| 0x020242E2 | 2 | POKE1_SPD |
| 0x020242E4 | 2 | POKE1_SPATK |
| 0x020242E6 | 2 | POKE1_SPDEF |

---

## 3. Battle State

### Battle Flags
| Address | Size | Name | Values |
|---------|------|------|--------|
| 0x02022B4B | 1 | BATTLE_FLAGS1 | Various battle flags |
| 0x02022B4C | 4 | BATTLE_TYPE | 0=no battle, 0x8=trainer, others=wild |
| 0x02022B50 | 4 | BATTLE_FLAGS2 | Extended battle flags |
| 0x02022AB8 | 1 | BATTLE_OUTCOME_A | Battle result A |
| 0x02022AC8 | 1 | BATTLE_OUTCOME_B | Battle result B |

### Active Pokemon in Battle
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x02023BC4 | 1 | ACTIVE_SIDE | Active side in battle |
| 0x02023BCC | 1 | NUM_ACTIVE | Number of active sides |
| 0x02023BCE | 1 | TEAM_BY_SIDE | Pokemon team ID by side |
| 0x02023BD6 | 1 | SIDE_STATUS | Side status flags |
| 0x02023BDE | 1 | TURN_ORDER | Attackers in order |
| 0x02023BE3 | 1 | BATTLE_MODE | Battle system mode |

### Player Battle Pokemon
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x02023BE4 | 2 | PLAYER_HP | Player's active Pokemon HP |
| 0x02023BE6 | 2 | PLAYER_MAX_HP | Player's active Pokemon max HP |
| 0x02023BE8 | 2 | PLAYER_ATK | Attack stat |
| 0x02023BEA | 2 | PLAYER_DEF | Defense stat |
| 0x02023BEC | 2 | PLAYER_SPD | Speed stat |
| 0x02023BEE | 2 | PLAYER_SPATK | Special Attack |
| 0x02023BF0 | 2 | PLAYER_SPDEF | Special Defense |

### Enemy Pokemon
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x02023C00 | 2 | ENEMY_SPECIES | Enemy species ID |
| 0x02023C04 | 1 | ENEMY_LEVEL | Enemy level |
| 0x02023C08 | 2 | ENEMY_HP | Enemy current HP |
| 0x02023C0A | 2 | ENEMY_MAX_HP | Enemy max HP |

### Enemy Party Addresses (in battle)
| Slot | Address | Description |
|------|---------|-------------|
| 1 | 0x0202402C | Enemy Pokemon 1 |
| 2 | 0x02024090 | Enemy Pokemon 2 |
| 3 | 0x020240F4 | Enemy Pokemon 3 |
| 4 | 0x02024158 | Enemy Pokemon 4 |
| 5 | 0x020241BC | Enemy Pokemon 5 |
| 6 | 0x02024220 | Enemy Pokemon 6 |

### Trainer Battle Info
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x020386AC | 2 | TRAINER_BATTLE_TYPE | Battle type ID |
| 0x020386AE | 2 | TRAINER_FLAG | Trainer flag number |
| 0x020386B0 | 2 | TRAINER_ARG3 | Trainerbattle argument 3 |

---

## 4. Progress & Inventory

### Money & Badges
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x02025000 | 4 | MONEY | Money (XOR encrypted) |
| 0x02025028 | 1 | BADGES | Badge bits (see below) |
| 0x02025004 | 2 | COINS | Game Corner coins (XOR encrypted) |

### Badge Bits (0x02025028)
| Bit | Badge | Gym Leader |
|-----|-------|------------|
| 0 | Boulder | Brock |
| 1 | Cascade | Misty |
| 2 | Thunder | Lt. Surge |
| 3 | Rainbow | Erika |
| 4 | Soul | Koga |
| 5 | Marsh | Sabrina |
| 6 | Volcano | Blaine |
| 7 | Earth | Giovanni |

### Security Key (for XOR decryption)
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x02025F20 | 4 | SECURITY_KEY | XOR key for money/items |

To get real money: `MONEY XOR SECURITY_KEY`

### Bag Pockets (via pointers at 0x0203988C)
| Address | Size | Name | Capacity |
|---------|------|------|----------|
| 0x0203988C | 4 | BAG_ITEMS_PTR | Items pocket (42 slots) |
| 0x02039894 | 4 | BAG_KEY_PTR | Key Items pocket (30 slots) |
| 0x0203989C | 4 | BAG_BALLS_PTR | Poke Balls pocket (13 slots) |
| 0x020398A4 | 4 | BAG_TM_PTR | TM Case (58 slots) |
| 0x020398AC | 4 | BAG_BERRY_PTR | Berry pocket (43 slots) |

### Item Entry Structure (4 bytes each)
| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0x00 | 2 | ITEM_ID | Item index |
| 0x02 | 2 | QUANTITY | Quantity (XOR with key lower 16 bits) |

### Pokedex
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x02025048 | 49 | DEX_OWNED | Owned Pokemon flags |
| 0x0202507C | 49 | DEX_SEEN_A | Seen Pokemon flags (copy A) |
| 0x020250B0 | 49 | DEX_SEEN_B | Seen Pokemon flags (copy B) |
| 0x020251E4 | 1 | NATIONAL_DEX | National dex enabled (0xDA) |

---

## 5. UI & Scene State

### Text & Dialog
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x020204B4 | 12 | DIALOG_BOX_1 | First dialog box state |
| 0x020204C0 | 12 | DIALOG_BOX_2 | Second dialog box |
| 0x02020010 | 4 | DIALOG_MAIN | Main dialog pointer |
| 0x02021D18 | ? | MSG_STRING | Message box display string |
| 0x02002D40 | ? | BOX_COLORS | UI box pixel colors |

### Menu State
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x0203ADB8 | 1 | MENU_STATE | Menu open/closed state |
| 0x0203ADE6 | 1 | CURSOR_POS | Menu cursor position |
| 0x0203ADFA | 1 | GAME_STATE | Game state flag |

### Scene Detection
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x03005008 | 4 | CALLBACK1_PTR | Main callback 1 pointer |
| 0x0300500C | 4 | CALLBACK2_PTR | Main callback 2 pointer |
| 0x03005D8C | 4 | SUPER_STATE | Super state (0=intro/title) |
| 0x02037721 | 1 | IN_INTRO | Has game started (0=intro) |
| 0x0203A11C | 1 | NAME_SCREEN | Name entry screen active |
| 0x03000F9C | 1 | FADE_STATE | Screen fade state |

### Script Engine
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x03000EB0 | 74 | SCRIPT_RAM | Script engine RAM |
| 0x020386C4 | 4 | SCRIPT_NEXT | Next script command offset |

---

## 6. System State

### Random Number Generator
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x03005000 | 4 | RNG_SEED | Current PRNG seed |

### Music & Audio
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x03000FC0 | 4 | MAP_MUSIC | Current map music ID |

### Save Block Pointers (DMA Protected)
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x03005008 | 4 | SAVE_MAPDATA | Pointer to map save block |
| 0x0300500C | 4 | SAVE_TRAINER | Pointer to trainer save block |
| 0x03005010 | 4 | SAVE_BOXDATA | Pointer to PC box save block |

### Hardware
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x04000130 | 2 | KEYINPUT | Hardware key input register |

---

## 7. Overworld Objects (NPCs/Events)

### Object Sprites (36 bytes each, 16 slots)
Base: 0x02036E38 (first is player)

| Slot | Address | Description |
|------|---------|-------------|
| 0 | 0x02036E38 | Player sprite |
| 1 | 0x02036E5C | Object 1 |
| 2 | 0x02036E80 | Object 2 |
| ... | +0x24 each | ... |
| 15 | 0x02037054 | Object 15 |

### Object Structure (36 bytes)
| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0x00 | 2 | X_POS | X position |
| 0x02 | 2 | Y_POS | Y position |
| 0x04 | 1 | DIRECTION | Facing direction |
| 0x05 | 1 | MOVEMENT | Movement type |
| ... | ... | ... | Other sprite data |

---

## 8. Event Flags & Variables

### Script Variables (0x8000-0x800F)
| Address | Size | Name |
|---------|------|------|
| 0x020370B8 | 2 | VAR_8000 |
| 0x020370BA | 2 | VAR_8001 |
| 0x020370BC | 2 | VAR_8002 |
| ... | 2 | ... |
| 0x020370D4 | 2 | VAR_800F |

### Special Addresses
| Address | Size | Name | Description |
|---------|------|------|-------------|
| 0x0203AAA8 | 4 | SETBYTE_TARGET | "setbyte" command target |
| 0x0203B01E | 2 | ASM_DATA | ASM routine data |

---

## 9. Recommended Watchpoints for Runner

These addresses change frequently during gameplay and are most useful for decision-making:

### High Priority (Always Watch)
```lua
{addr = 0x02036E38, size = 2, label = "PLAYER_X"},
{addr = 0x02036E3A, size = 2, label = "PLAYER_Y"},
{addr = 0x02036E3C, size = 1, label = "DIRECTION"},
{addr = 0x02036E36, size = 1, label = "MAP_NUM"},
{addr = 0x02022B4C, size = 1, label = "BATTLE_FLAG"},
{addr = 0x020204B4, size = 1, label = "TEXT_BOX"},
{addr = 0x0203ADB8, size = 1, label = "MENU_STATE"},
```

### Battle (Watch during battles)
```lua
{addr = 0x02023BE4, size = 2, label = "PLAYER_HP"},
{addr = 0x02023BE6, size = 2, label = "PLAYER_MAX_HP"},
{addr = 0x02023C08, size = 2, label = "ENEMY_HP"},
{addr = 0x02023C0A, size = 2, label = "ENEMY_MAX_HP"},
{addr = 0x02023C00, size = 2, label = "ENEMY_SPECIES"},
{addr = 0x02023C04, size = 1, label = "ENEMY_LEVEL"},
```

### Progress (Periodic check)
```lua
{addr = 0x02024029, size = 1, label = "PARTY_COUNT"},
{addr = 0x02025028, size = 1, label = "BADGES"},
{addr = 0x020242DA, size = 2, label = "POKE1_HP"},
{addr = 0x020242D8, size = 1, label = "POKE1_LEVEL"},
```

---

## 10. Scene Type Detection

Use these combinations to determine game state:

| Condition | Scene Type |
|-----------|------------|
| BATTLE_FLAG > 0 | In Battle |
| TEXT_BOX > 0 && BATTLE_FLAG == 0 | Dialog/Text |
| MENU_STATE > 0 | Menu Open |
| IN_INTRO == 0 | Title/Intro |
| NAME_SCREEN > 0 | Name Entry |
| FADE_STATE > 0 | Transitioning |
| All zero | Free Roam |

---

## Notes

1. **Encryption**: Money and item quantities are XOR'd with the security key at 0x02025F20
2. **Little Endian**: All multi-byte values are stored little-endian
3. **DMA Protection**: Save blocks may move; use pointers at 0x03005008/0C/10
4. **ROM Version**: These addresses are for USA v1.0 (1636) - other versions differ!
