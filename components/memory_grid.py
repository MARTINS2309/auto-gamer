"""
Memory Grid Component - Visualizes memory reads/writes with recency-based dimming.

Shows a grid of memory addresses with colors indicating:
- Blue: Recently read
- Red: Recently written
- Brightness: How recently accessed (brighter = more recent)
"""

import tkinter as tk
from typing import Optional
from dataclasses import dataclass
from collections import defaultdict
import time


@dataclass
class MemoryAccess:
    """Record of a memory access."""
    address: int
    value: int
    access_type: str  # 'read' or 'write'
    timestamp: float
    label: Optional[str] = None  # Human-readable label like "PLAYER_X"


class MemoryGrid(tk.LabelFrame):
    """Grid visualization of memory access patterns."""

    # Memory regions to display (Pokemon FireRed)
    MEMORY_REGIONS = {
        "Player": {
            "PLAYER_X": 0x02036E38,
            "PLAYER_Y": 0x02036E3A,
            "DIRECTION": 0x02036E3C,
            "MAP_BANK": 0x02036E34,
            "MAP_NUM": 0x02036E36,
            "PLAYER_NAME": 0x02024EA4,
            "TRAINER_ID": 0x02024EAC,
        },
        "Progress": {
            "MONEY": 0x02025000,
            "BADGES": 0x02025028,
            "PLAY_TIME_H": 0x02024EAE,
            "PLAY_TIME_M": 0x02024EB0,
            "SEEN_FLAGS": 0x02025064,
            "CAUGHT_FLAGS": 0x02025094,
        },
        "Party": {
            "PARTY_COUNT": 0x02024029,
            "PARTY_DATA": 0x02024284,
            "PKMN1_SPECIES": 0x02024284,
            "PKMN1_LEVEL": 0x020242C0,
            "PKMN1_HP": 0x020242BC,
            "PKMN1_MAXHP": 0x020242BE,
        },
        "Battle": {
            "BATTLE_FLAG": 0x02022B4C,
            "BATTLE_TYPE": 0x02022B50,
            "PLAYER_HP": 0x02023BE4,
            "PLAYER_MAX_HP": 0x02023BE6,
            "PLAYER_ATK": 0x02023BE8,
            "PLAYER_DEF": 0x02023BEA,
            "ENEMY_HP": 0x02023C08,
            "ENEMY_MAX_HP": 0x02023C0A,
            "ENEMY_SPECIES": 0x02023C00,
        },
        "Items": {
            "POCKET_ITEMS": 0x02025A30,
            "KEY_ITEMS": 0x02025AD0,
            "POKE_BALLS": 0x02025B50,
            "TM_CASE": 0x02025B70,
            "BERRY_POUCH": 0x02025C10,
            "PC_ITEMS": 0x02028510,
        },
        "UI": {
            "TEXT_BOX": 0x020204B4,
            "MENU_STATE": 0x0203ADB8,
            "GAME_STATE": 0x03005008,
            "SCRIPT_PTR": 0x03000EB0,
            "TEXTBOX_ID": 0x02038814,
        },
    }

    # Fade duration in seconds
    FADE_DURATION = 3.0

    def __init__(self, parent, cell_size: int = 20, **kwargs):
        super().__init__(parent, text="MEMORY ACCESS", bg='#1a1a2e', fg='#666',
                        font=('Consolas', 11), **kwargs)

        self.cell_size = cell_size
        self.access_history: dict[int, MemoryAccess] = {}
        self.address_to_label: dict[int, str] = {}

        # Build reverse lookup
        for region, addresses in self.MEMORY_REGIONS.items():
            for label, addr in addresses.items():
                self.address_to_label[addr] = label

        self._build_ui()

    def _build_ui(self):
        """Build the memory grid UI."""
        # Main container with scrolling
        container = tk.Frame(self, bg='#1a1a2e')
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create canvas for grid
        self.canvas = tk.Canvas(container, bg='#0d0d1a', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Draw initial grid
        self._draw_grid()

        # Start fade update loop
        self._update_fade()

    def _draw_grid(self):
        """Draw the memory grid."""
        self.canvas.delete("all")

        x = 5
        y = 10
        row_height = 18
        col_widths = [95, 75, 50, 45]  # Label, Address, Value, Age

        # Header
        headers = ["Label", "Address", "Value", "Age"]
        for i, header in enumerate(headers):
            self.canvas.create_text(x + sum(col_widths[:i]) + col_widths[i]//2, y,
                                   text=header, fill='#666', font=('Consolas', 8, 'bold'))
        y += row_height

        # Draw each memory region
        self.cell_items = {}

        for region, addresses in self.MEMORY_REGIONS.items():
            # Region header
            self.canvas.create_text(x + 5, y, text=region, fill='#888',
                                   font=('Consolas', 9, 'bold'), anchor='w')
            y += row_height - 5

            for label, addr in addresses.items():
                # Get access info
                access = self.access_history.get(addr)

                # Calculate color based on recency
                if access:
                    age = time.time() - access.timestamp
                    brightness = max(0, 1 - (age / self.FADE_DURATION))

                    if access.access_type == 'read':
                        r, g, b = 0, int(100 + 155 * brightness), int(200 + 55 * brightness)
                    else:  # write
                        r, g, b = int(200 + 55 * brightness), int(50 * brightness), int(50 * brightness)

                    color = f'#{r:02x}{g:02x}{b:02x}'
                    value_text = f"{access.value:04X}" if access.value is not None else "----"
                    age_text = f"{age:.1f}s" if age < 10 else ">10s"
                else:
                    color = '#333'
                    value_text = "----"
                    age_text = ""

                # Draw row background
                bg_rect = self.canvas.create_rectangle(x, y - 8, x + sum(col_widths), y + 12,
                                                       fill=color, outline='#222')

                # Label
                label_text = self.canvas.create_text(x + 5, y,
                                                    text=label[:10], fill='#aaa',
                                                    font=('Consolas', 8), anchor='w')

                # Address
                addr_text = self.canvas.create_text(x + col_widths[0] + 5, y,
                                                   text=f"{addr:08X}", fill='#666',
                                                   font=('Consolas', 8), anchor='w')

                # Value
                val_item = self.canvas.create_text(x + col_widths[0] + col_widths[1] + 5, y,
                                                  text=value_text, fill='#fff' if access else '#444',
                                                  font=('Consolas', 8, 'bold'), anchor='w')

                # Age
                age_item = self.canvas.create_text(x + col_widths[0] + col_widths[1] + col_widths[2] + 5, y,
                                                  text=age_text, fill='#666',
                                                  font=('Consolas', 7), anchor='w')

                self.cell_items[addr] = (bg_rect, label_text, addr_text, val_item, age_item)
                y += row_height

            y += 5  # Space between regions

        # Update canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _update_fade(self):
        """Update colors based on access age (fade effect)."""
        self._draw_grid()
        self.after(100, self._update_fade)  # Update 10 times per second

    def record_read(self, address: int, value: int, label: str = None):
        """Record a memory read."""
        if label is None:
            label = self.address_to_label.get(address, f"0x{address:08X}")

        self.access_history[address] = MemoryAccess(
            address=address,
            value=value,
            access_type='read',
            timestamp=time.time(),
            label=label
        )

    def record_write(self, address: int, value: int, label: str = None):
        """Record a memory write."""
        if label is None:
            label = self.address_to_label.get(address, f"0x{address:08X}")

        self.access_history[address] = MemoryAccess(
            address=address,
            value=value,
            access_type='write',
            timestamp=time.time(),
            label=label
        )

    def clear(self):
        """Clear all access history."""
        self.access_history.clear()
        self._draw_grid()

    # Convenience methods for known addresses
    def read_player_x(self, value: int):
        self.record_read(0x02036E38, value, "PLAYER_X")

    def read_player_y(self, value: int):
        self.record_read(0x02036E3A, value, "PLAYER_Y")

    def read_player_hp(self, value: int):
        self.record_read(0x02023BE4, value, "PLAYER_HP")

    def read_enemy_hp(self, value: int):
        self.record_read(0x02023C08, value, "ENEMY_HP")

    def read_battle_flag(self, value: int):
        self.record_read(0x02022B4C, value, "BATTLE_FLAG")

    def read_game_state(self, value: int):
        self.record_read(0x03005008, value, "GAME_STATE")
