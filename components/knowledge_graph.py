"""
Knowledge Graph Component - Visualizes the bot's internal knowledge state.

Shows:
- Current beliefs about game state
- Recent observations and their confidence
- Decision-making factors
- Connections between knowledge nodes
"""

import tkinter as tk
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict
import time
import math


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    category: str  # 'state', 'observation', 'decision', 'action', 'goal'
    label: str
    value: str
    confidence: float = 1.0  # 0.0 to 1.0
    timestamp: float = 0.0
    connections: list = field(default_factory=list)  # List of connected node IDs


class KnowledgeGraph(tk.LabelFrame):
    """Visual representation of the bot's knowledge."""

    # Category colors
    CATEGORY_COLORS = {
        'state': '#00aaff',      # Blue - current game state
        'observation': '#aa00ff', # Purple - what was seen
        'decision': '#ffaa00',   # Orange - reasoning
        'action': '#00ff88',     # Green - what was done
        'goal': '#ff4444',       # Red - objectives
        'memory': '#ff00ff',     # Magenta - remembered facts
        'rule': '#44ffff',       # Cyan - condition->action rules
    }

    # Fade duration for recency visualization
    FADE_DURATION = 5.0

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="KNOWLEDGE GRAPH", bg='#1a1a2e', fg='#666',
                        font=('Consolas', 11), **kwargs)

        self.nodes: dict[str, KnowledgeNode] = {}
        self.node_positions: dict[str, tuple] = {}
        self._layout_done = False  # Only layout once
        self._last_canvas_size = (0, 0)

        self._build_ui()
        self._init_default_nodes()

    def _build_ui(self):
        """Build the knowledge graph UI."""
        # Main canvas
        self.canvas = tk.Canvas(self, bg='#0d0d1a', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Pan/zoom state
        self.pan_offset = [0, 0]
        self.zoom_level = 1.0
        self.drag_start = None

        # Mouse bindings for pan/zoom
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<MouseWheel>", self._on_scroll)  # Windows
        self.canvas.bind("<Button-4>", lambda e: self._on_scroll_unix(e, 1))  # Linux up
        self.canvas.bind("<Button-5>", lambda e: self._on_scroll_unix(e, -1))  # Linux down
        self.canvas.bind("<Double-Button-1>", self._reset_view)

        # Legend
        legend_frame = tk.Frame(self, bg='#1a1a2e')
        legend_frame.pack(fill=tk.X, padx=5, pady=2)

        for category, color in self.CATEGORY_COLORS.items():
            tk.Label(legend_frame, text=f"● {category}", fg=color, bg='#1a1a2e',
                    font=('Consolas', 7)).pack(side=tk.LEFT, padx=5)

        # Start update loop
        self._update_display()

    def _on_drag_start(self, event):
        """Start panning."""
        self.drag_start = (event.x, event.y)

    def _on_drag(self, event):
        """Pan the view."""
        if self.drag_start:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.pan_offset[0] += dx
            self.pan_offset[1] += dy
            self.drag_start = (event.x, event.y)

    def _on_scroll(self, event):
        """Zoom with mouse wheel (Windows)."""
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom_level = max(0.3, min(3.0, self.zoom_level * factor))

    def _on_scroll_unix(self, event, direction):
        """Zoom with mouse wheel (Linux/Mac)."""
        factor = 1.1 if direction > 0 else 0.9
        self.zoom_level = max(0.3, min(3.0, self.zoom_level * factor))

    def _reset_view(self, event=None):
        """Reset pan/zoom to default."""
        self.pan_offset = [0, 0]
        self.zoom_level = 1.0
        self._layout_done = False  # Force relayout

    def _init_default_nodes(self):
        """Initialize with default knowledge structure."""
        # Core state nodes
        self.add_node("scene", "state", "Scene", "unknown")
        self.add_node("in_battle", "state", "In Battle", "No")
        self.add_node("player_hp", "state", "Player HP", "100%")
        self.add_node("enemy_hp", "state", "Enemy HP", "100%")
        self.add_node("position", "state", "Position", "(?,?)")

        # Observation nodes
        self.add_node("last_vision", "observation", "Vision", "pending")
        self.add_node("dialogue", "observation", "Dialogue", "none")

        # Decision nodes
        self.add_node("strategy", "decision", "Strategy", "explore")
        self.add_node("weights", "decision", "Weights", "default")

        # Action nodes
        self.add_node("last_action", "action", "Last Action", "none")
        self.add_node("action_count", "action", "Actions", "0")

        # Goal nodes
        self.add_node("current_goal", "goal", "Goal", "explore")

        # Memory/Genome nodes (evolutionary lineage)
        self.add_node("genome_id", "memory", "Genome", "gen-0")
        self.add_node("generation", "memory", "Generation", "0")
        self.add_node("fitness", "memory", "Fitness", "0")
        self.add_node("lineage", "memory", "Lineage", "root")
        self.add_node("battles", "memory", "Battles", "0W/0L")
        self.add_node("caught", "memory", "Caught", "0")
        self.add_node("badges", "memory", "Badges", "0")

        # Rule nodes (condition -> action)
        self.add_node("rule_battle", "rule", "IF battle", "-> A (attack)")
        self.add_node("rule_dialogue", "rule", "IF dialogue", "-> A (confirm)")
        self.add_node("rule_overworld", "rule", "IF overworld", "-> move")
        self.add_node("rule_lowHP", "rule", "IF HP < 25%", "-> heal/run")

        # Connect nodes
        self.connect("last_vision", "scene")
        self.connect("scene", "strategy")
        self.connect("strategy", "last_action")
        self.connect("in_battle", "strategy")
        self.connect("player_hp", "strategy")
        self.connect("enemy_hp", "strategy")
        self.connect("current_goal", "strategy")

        # Memory connections
        self.connect("genome_id", "weights")
        self.connect("lineage", "genome_id")
        self.connect("fitness", "genome_id")
        self.connect("battles", "fitness")
        self.connect("caught", "fitness")
        self.connect("badges", "fitness")

        # Rule connections (rules influence strategy)
        self.connect("rule_battle", "strategy")
        self.connect("rule_dialogue", "strategy")
        self.connect("rule_overworld", "strategy")
        self.connect("rule_lowHP", "strategy")

        # Layout nodes
        self._layout_nodes()

    def _layout_nodes(self):
        """Arrange nodes in a logical layout with proper spacing."""
        # Get canvas dimensions
        self.update_idletasks()
        width = self.canvas.winfo_width() or 600
        height = self.canvas.winfo_height() or 400

        # Minimum spacing between nodes
        MIN_NODE_SPACING = 60
        MIN_LAYER_SPACING = 100

        # Group nodes by category
        categories = defaultdict(list)
        for node_id, node in self.nodes.items():
            categories[node.category].append(node_id)

        # Arrange in layers (left to right)
        layer_order = ['observation', 'state', 'rule', 'decision', 'action', 'goal', 'memory']
        layer_x = {}

        visible_layers = [l for l in layer_order if l in categories]
        if not visible_layers:
            return

        # Calculate layer spacing - ensure minimum spacing
        layer_width = max(MIN_LAYER_SPACING, width / (len(visible_layers) + 1))

        for i, layer in enumerate(visible_layers):
            layer_x[layer] = (i + 1) * layer_width

        # Position nodes within each layer with proper vertical spacing
        for category, node_ids in categories.items():
            if category not in layer_x:
                continue

            x = layer_x[category]
            n = len(node_ids)

            # Calculate vertical spacing - ensure minimum
            total_height_needed = n * MIN_NODE_SPACING
            if total_height_needed > height:
                # Nodes won't fit, use minimum spacing anyway
                layer_height = MIN_NODE_SPACING
                start_y = MIN_NODE_SPACING / 2
            else:
                # Center the nodes vertically with proper spacing
                layer_height = max(MIN_NODE_SPACING, height / (n + 1))
                start_y = layer_height

            for i, node_id in enumerate(node_ids):
                y = start_y + i * layer_height
                self.node_positions[node_id] = (x, y)

    def _transform(self, x, y):
        """Apply pan and zoom transform to coordinates."""
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        # Zoom around center, then apply pan
        tx = cx + (x - cx) * self.zoom_level + self.pan_offset[0]
        ty = cy + (y - cy) * self.zoom_level + self.pan_offset[1]
        return tx, ty

    def _update_display(self):
        """Redraw the knowledge graph."""
        self.canvas.delete("all")

        # Only recalculate layout once, or if canvas size changed significantly
        current_size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        size_changed = (abs(current_size[0] - self._last_canvas_size[0]) > 50 or
                       abs(current_size[1] - self._last_canvas_size[1]) > 50)

        if not self._layout_done or (size_changed and current_size[0] > 100):
            self._layout_nodes()
            self._layout_done = True
            self._last_canvas_size = current_size

        z = self.zoom_level  # Shorthand for zoom

        # Draw connections first (behind nodes)
        for node_id, node in self.nodes.items():
            if node_id not in self.node_positions:
                continue
            x1, y1 = self._transform(*self.node_positions[node_id])

            for connected_id in node.connections:
                if connected_id not in self.node_positions:
                    continue
                x2, y2 = self._transform(*self.node_positions[connected_id])

                # Calculate connection age for fading
                connected_node = self.nodes.get(connected_id)
                if connected_node:
                    age = time.time() - max(node.timestamp, connected_node.timestamp)
                    brightness = max(0.2, min(1.0, 1 - age / self.FADE_DURATION))
                else:
                    brightness = 0.3

                gray = int(50 + 100 * brightness)
                color = f'#{gray:02x}{gray:02x}{gray:02x}'

                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=max(1, int(z)),
                                        dash=(4, 2) if brightness < 0.5 else None)

        # Draw nodes
        for node_id, node in self.nodes.items():
            if node_id not in self.node_positions:
                continue

            x, y = self._transform(*self.node_positions[node_id])

            # Calculate node brightness based on recency
            age = time.time() - node.timestamp
            brightness = max(0.3, min(1.0, 1 - age / self.FADE_DURATION))

            # Get base color
            base_color = self.CATEGORY_COLORS.get(node.category, '#888888')
            r = int(int(base_color[1:3], 16) * brightness)
            g = int(int(base_color[3:5], 16) * brightness)
            b = int(int(base_color[5:7], 16) * brightness)
            color = f'#{r:02x}{g:02x}{b:02x}'

            # Node size based on confidence and zoom (reduced for better fit)
            node_width = (20 + int(10 * node.confidence)) * z
            node_height = (12 + int(6 * node.confidence)) * z

            # Glow effect for recently updated nodes
            if age < 0.5:
                glow_w = node_width + 6 * z
                glow_h = node_height + 4 * z
                self.canvas.create_oval(x - glow_w, y - glow_h,
                                        x + glow_w, y + glow_h,
                                        fill='', outline=color, width=2)

            # Draw node (ellipse shape)
            self.canvas.create_oval(x - node_width, y - node_height,
                                   x + node_width, y + node_height,
                                   fill=color, outline='#333')

            # Label (scale font with zoom)
            font_size = max(6, int(7 * z))
            self.canvas.create_text(x, y - 2 * z, text=node.label,
                                   fill='white' if brightness > 0.5 else '#aaa',
                                   font=('Consolas', font_size, 'bold'))

            # Value (truncate to fit)
            value_text = str(node.value)[:12]
            font_size_small = max(5, int(6 * z))
            self.canvas.create_text(x, y + 8 * z, text=value_text,
                                   fill='#ddd' if brightness > 0.5 else '#666',
                                   font=('Consolas', font_size_small))

        # Draw zoom indicator
        self.canvas.create_text(10, 10, text=f"Zoom: {self.zoom_level:.1f}x", anchor='nw',
                               fill='#555', font=('Consolas', 8))

        # Schedule next update
        self.after(100, self._update_display)

    def add_node(self, node_id: str, category: str, label: str, value: str,
                 confidence: float = 1.0):
        """Add or update a node."""
        self.nodes[node_id] = KnowledgeNode(
            id=node_id,
            category=category,
            label=label,
            value=value,
            confidence=confidence,
            timestamp=time.time(),
            connections=self.nodes.get(node_id, KnowledgeNode(node_id, '', '', '')).connections
        )

    def update_node(self, node_id: str, value: str, confidence: float = None):
        """Update an existing node's value."""
        if node_id in self.nodes:
            self.nodes[node_id].value = value
            self.nodes[node_id].timestamp = time.time()
            if confidence is not None:
                self.nodes[node_id].confidence = confidence

    def connect(self, from_id: str, to_id: str):
        """Connect two nodes."""
        if from_id in self.nodes:
            if to_id not in self.nodes[from_id].connections:
                self.nodes[from_id].connections.append(to_id)

    def disconnect(self, from_id: str, to_id: str):
        """Disconnect two nodes."""
        if from_id in self.nodes:
            if to_id in self.nodes[from_id].connections:
                self.nodes[from_id].connections.remove(to_id)

    def remove_node(self, node_id: str):
        """Remove a node."""
        if node_id in self.nodes:
            del self.nodes[node_id]
        if node_id in self.node_positions:
            del self.node_positions[node_id]

        # Remove connections to this node
        for node in self.nodes.values():
            if node_id in node.connections:
                node.connections.remove(node_id)

    def clear(self):
        """Clear all nodes and reinitialize."""
        self.nodes.clear()
        self.node_positions.clear()
        self._layout_done = False  # Force relayout on next update
        self._init_default_nodes()

    # Convenience methods for common updates
    def set_scene(self, scene_type: str, confidence: float = 1.0):
        """Update scene observation."""
        self.update_node("scene", scene_type, confidence)
        self.update_node("last_vision", f"saw {scene_type}")

    def set_battle_state(self, in_battle: bool, player_hp: int = None, enemy_hp: int = None):
        """Update battle-related knowledge."""
        self.update_node("in_battle", "Yes" if in_battle else "No")
        if player_hp is not None:
            self.update_node("player_hp", f"{player_hp}%")
        if enemy_hp is not None:
            self.update_node("enemy_hp", f"{enemy_hp}%")

    def set_position(self, x: int, y: int, map_id: int = None):
        """Update position knowledge."""
        pos_str = f"({x},{y})"
        if map_id is not None:
            pos_str += f" M{map_id}"
        self.update_node("position", pos_str)

    def set_strategy(self, strategy: str, reason: str = None):
        """Update current strategy."""
        self.update_node("strategy", strategy)
        if reason:
            self.update_node("weights", reason[:20])

    def set_action(self, action: str, count: int = None):
        """Update last action."""
        self.update_node("last_action", action)
        if count is not None:
            self.update_node("action_count", str(count))

    def set_goal(self, goal: str):
        """Update current goal."""
        self.update_node("current_goal", goal)

    def set_dialogue(self, has_dialogue: bool, text: str = None):
        """Update dialogue observation."""
        if has_dialogue:
            self.update_node("dialogue", text[:20] if text else "detected")
        else:
            self.update_node("dialogue", "none")

    # Genome/Evolutionary methods
    def set_genome(self, genome_id: str, generation: int, fitness: float, parent_ids: list = None):
        """Set genome lineage info."""
        self.update_node("genome_id", genome_id[:8])
        self.update_node("generation", f"Gen {generation}")
        self.update_node("fitness", f"{fitness:.1f}")

        if parent_ids:
            lineage = " → ".join([p[:4] for p in parent_ids[:3]])
            self.update_node("lineage", lineage or "root")
        else:
            self.update_node("lineage", "root")

    def set_fitness(self, fitness: float, ai_score: float = None):
        """Update fitness score (can include AI feedback)."""
        if ai_score is not None:
            self.update_node("fitness", f"{fitness:.1f} (AI:{ai_score:+.1f})")
        else:
            self.update_node("fitness", f"{fitness:.1f}")

    def set_run_stats(self, battles_won: int = 0, battles_lost: int = 0,
                      pokemon_caught: int = 0, badges_earned: int = 0):
        """Update run statistics nodes."""
        self.update_node("battles", f"{battles_won}W/{battles_lost}L")
        self.update_node("caught", str(pokemon_caught))
        self.update_node("badges", str(badges_earned))

    def set_rules_from_genome(self, genome):
        """Update rule nodes based on genome weights."""
        if not genome or not hasattr(genome, 'weights'):
            return

        weights = genome.weights

        # Battle rules - find top action
        if 'battle' in weights:
            top_action = max(weights['battle'].items(), key=lambda x: x[1])
            self.update_node("rule_battle", f"-> {top_action[0]} ({top_action[1]:.1f})")

        # Dialogue rules
        if 'dialogue' in weights:
            top_action = max(weights['dialogue'].items(), key=lambda x: x[1])
            self.update_node("rule_dialogue", f"-> {top_action[0]} ({top_action[1]:.1f})")

        # Overworld rules
        if 'overworld' in weights:
            top_action = max(weights['overworld'].items(), key=lambda x: x[1])
            self.update_node("rule_overworld", f"-> {top_action[0]} ({top_action[1]:.1f})")

        # Menu rules (reuse lowHP slot for now)
        if 'menu' in weights:
            top_action = max(weights['menu'].items(), key=lambda x: x[1])
            self.update_node("rule_lowHP", f"menu-> {top_action[0]}")

    def set_active_rule(self, scene: str, action: str, weight: float):
        """Highlight which rule is currently active."""
        # Map scene to rule node
        rule_map = {
            'battle': 'rule_battle',
            'dialogue': 'rule_dialogue',
            'overworld': 'rule_overworld',
            'menu': 'rule_lowHP',
            'title': 'rule_lowHP',
        }
        rule_id = rule_map.get(scene)
        if rule_id:
            self.update_node(rule_id, f"-> {action} ({weight:.2f})", confidence=1.0)
