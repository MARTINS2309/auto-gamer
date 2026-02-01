"""
Pokemon AI - Visual Dashboard

Static layout with grid-based component positioning.
All logic lives in dedicated modules.
"""

from queue import Queue

import tkinter as tk
from tkinter import ttk

from components import (
    ToolMap, InputPad, GameView, StateDisplay,
    ControlBar, ActivityLog, MemoryGrid, KnowledgeGraph,
)

from logic.runner import AgentRunner
from logic.act import GameLauncher


class Dashboard:
    """
    Main dashboard window.

    Layout:
    - Row 1: Control bar (full width)
    - Main area:
      - Left sidebar: Activity Log
      - Center (3 rows):
        - Row 1: Game View | State Display
        - Row 2: Input Pad | Tool Map
        - Row 3: Knowledge Graph (full width)
      - Right sidebar: Memory Grid
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Pokemon AI")
        self.root.configure(bg='#0a0a1a')

        # Window size
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        if w >= 3840:
            self.root.geometry(f"{w-100}x{h-100}+50+25")
        else:
            self.root.geometry("1600x900")

        # Event queue for runner -> UI communication
        self.events: Queue = Queue()

        # Agent runner - handles all game logic
        self.runner = AgentRunner(self.events)

        # Component references
        self.widgets = {}

        self._build_ui()
        self._try_connect()
        self._poll_events()

    def _build_ui(self):
        """Build the static dashboard layout."""
        # Main container
        main = tk.Frame(self.root, bg='#0a0a1a')
        main.pack(fill=tk.BOTH, expand=True)

        # === Row 1: Control Bar (full width) ===
        self.control_bar = ControlBar(
            main,
            on_start=self._start,
            on_stop=self._stop,
            on_pause=self._pause,
            on_reset=self._reset,
            on_emu_command=self._handle,
            on_preflight_check=self.runner.get_preflight_status,
            on_launch_mgba=self._launch_mgba,
        )
        self.control_bar.pack(fill=tk.X, padx=10, pady=10)

        # === Main content area ===
        content = tk.Frame(main, bg='#0a0a1a')
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Left sidebar: Activity Log
        left_sidebar = tk.Frame(content, bg='#0a0a1a', width=280)
        left_sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_sidebar.pack_propagate(False)

        self.widgets['log'] = ActivityLog(left_sidebar)
        self.widgets['log'].pack(fill=tk.BOTH, expand=True)

        # Right sidebar: Memory Grid
        right_sidebar = tk.Frame(content, bg='#0a0a1a', width=280)
        right_sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_sidebar.pack_propagate(False)

        self.widgets['memory'] = MemoryGrid(right_sidebar)
        self.widgets['memory'].pack(fill=tk.BOTH, expand=True)

        # Center area (between sidebars)
        center = tk.Frame(content, bg='#0a0a1a')
        center.pack(fill=tk.BOTH, expand=True)

        # Use grid for center area (3 rows)
        center.grid_rowconfigure(0, weight=3)  # Game view row
        center.grid_rowconfigure(1, weight=1)  # Input/tools row
        center.grid_rowconfigure(2, weight=2)  # Graph row
        center.grid_columnconfigure(0, weight=3)  # Left column (game/input)
        center.grid_columnconfigure(1, weight=2)  # Right column (state/tools)

        # Row 1: Game View | State Display
        game_frame = tk.Frame(center, bg='#0a0a1a')
        game_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5), pady=(0, 5))
        self.widgets['game_view'] = GameView(game_frame, width=480, height=320)
        self.widgets['game_view'].pack(fill=tk.BOTH, expand=True)

        state_frame = tk.Frame(center, bg='#0a0a1a')
        state_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0), pady=(0, 5))
        self.widgets['state'] = StateDisplay(state_frame)
        self.widgets['state'].pack(fill=tk.BOTH, expand=True)

        # Row 2: Input Pad | Tool Map
        input_frame = tk.Frame(center, bg='#0a0a1a')
        input_frame.grid(row=1, column=0, sticky='nsew', padx=(0, 5), pady=5)
        self.widgets['input'] = InputPad(input_frame)
        self.widgets['input'].pack(fill=tk.BOTH, expand=True)

        tools_frame = tk.Frame(center, bg='#0a0a1a')
        tools_frame.grid(row=1, column=1, sticky='nsew', padx=(5, 0), pady=5)
        self.widgets['tools'] = ToolMap(tools_frame)
        self.widgets['tools'].pack(fill=tk.BOTH, expand=True)

        # Row 3: Knowledge Graph (full width)
        graph_frame = tk.Frame(center, bg='#0a0a1a')
        graph_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(5, 0))
        self.widgets['knowledge'] = KnowledgeGraph(graph_frame)
        self.widgets['knowledge'].pack(fill=tk.BOTH, expand=True)

    def _try_connect(self):
        """Try to connect to mGBA on startup."""
        self.runner.try_connect()
        if self.runner.sender:
            self.control_bar.set_sender(self.runner.sender)

    def _poll_events(self):
        """Process events from runner."""
        while not self.events.empty():
            try:
                ev = self.events.get_nowait()
                self._handle(ev)
            except:
                break
        self.root.after(50, self._poll_events)

    def _handle(self, ev: dict):
        """Route runner event to appropriate UI component."""
        t = ev.get("type")

        # Log messages
        if t == "log":
            log = self.widgets.get('log')
            if log:
                log.log(ev.get("msg", ""), ev.get("level", "info"))

        # Frame/image updates
        elif t == "image":
            view = self.widgets.get('game_view')
            if view and ev.get("image"):
                view.update_image(ev["image"])

        # Action taken
        elif t == "action":
            action = ev.get("action", "")
            inp = self.widgets.get('input')
            if inp:
                inp.flash(action)
            kg = self.widgets.get('knowledge')
            if kg:
                kg.set_action(action, self.runner.step_count)
            tools = self.widgets.get('tools')
            if tools:
                tools.set_output("input", f"Pressed: {action.upper()}")

        # Scene detection
        elif t == "scene":
            scene = ev.get("scene", "unknown")
            state = self.widgets.get('state')
            if state:
                state.set_scene(scene)
            kg = self.widgets.get('knowledge')
            if kg:
                kg.set_scene(scene)
            tools = self.widgets.get('tools')
            if tools:
                tools.set_output("vision", f"Detected: {scene}")

        # Game state update
        elif t == "state":
            state_data = ev.get("state")
            if state_data:
                kg = self.widgets.get('knowledge')
                if kg:
                    kg.set_battle_state(
                        state_data.get("battle", False),
                        state_data.get("player_hp"),
                        state_data.get("enemy_hp")
                    )
                    kg.set_position(
                        state_data.get("x", 0),
                        state_data.get("y", 0),
                        state_data.get("map", 0)
                    )
                state_widget = self.widgets.get('state')
                if state_widget:
                    if state_data.get("player_hp") is not None:
                        state_widget.set_player_hp(state_data["player_hp"])
                    if state_data.get("enemy_hp") is not None:
                        state_widget.set_enemy_hp(state_data["enemy_hp"])

        # Strategy/goal updates
        elif t == "strategy":
            kg = self.widgets.get('knowledge')
            if kg:
                kg.set_strategy(ev.get("strategy", ""), ev.get("reason", ""))
        elif t == "goal":
            kg = self.widgets.get('knowledge')
            if kg:
                kg.set_goal(ev.get("goal", ""))

        # Genome/evolution updates
        elif t == "genome":
            genome = ev.get("genome")
            kg = self.widgets.get('knowledge')
            if kg and genome:
                kg.set_genome(
                    genome.id,
                    genome.generation,
                    genome.fitness(),
                    genome.parent_ids
                )
        elif t == "rules":
            genome = ev.get("genome")
            kg = self.widgets.get('knowledge')
            if kg and genome:
                kg.set_rules_from_genome(genome)
        elif t == "active_rule":
            kg = self.widgets.get('knowledge')
            if kg:
                kg.set_active_rule(
                    ev.get("scene", ""),
                    ev.get("action", ""),
                    ev.get("weight", 0.0)
                )
        elif t == "run_stats":
            stats = ev.get("stats", {})
            kg = self.widgets.get('knowledge')
            if kg:
                kg.set_run_stats(
                    battles_won=stats.get("battles_won", 0),
                    battles_lost=stats.get("battles_lost", 0),
                    pokemon_caught=stats.get("pokemon_caught", 0),
                    badges_earned=stats.get("badges_earned", 0)
                )

        # Step/speed updates
        elif t == "step":
            state = self.widgets.get('state')
            if state:
                state.set_step(ev.get("step", 0))
        elif t == "speed":
            state = self.widgets.get('state')
            if state:
                state.set_speed(ev.get("speed", 0))

        # Tool activity
        elif t == "tool_on":
            tools = self.widgets.get('tools')
            if tools:
                tools.activate(ev.get("tool", ""))
        elif t == "tool_off":
            tools = self.widgets.get('tools')
            if tools:
                tools.deactivate(ev.get("tool", ""))
        elif t == "tool_output":
            tools = self.widgets.get('tools')
            if tools:
                tools.set_output(ev.get("tool", ""), ev.get("output", ""))

        # Decision reason
        elif t == "decision":
            tools = self.widgets.get('tools')
            if tools:
                tools.set_output("rules", ev.get("reason", ""))

        # Memory reads
        elif t == "memory":
            memory = self.widgets.get('memory')
            if memory:
                reads = ev.get("reads", [])
                for read in reads:
                    memory.record_read(
                        read.get("addr", 0),
                        read.get("value", 0),
                        read.get("label")
                    )

        # Sender update
        elif t == "sender":
            sender = ev.get("sender")
            if sender:
                self.control_bar.set_sender(sender)

    # -------------------------------------------------------------------------
    # Control callbacks
    # -------------------------------------------------------------------------

    def _start(self):
        """Start the agent."""
        log = self.widgets.get('log')
        if log:
            log.clear()
        memory = self.widgets.get('memory')
        if memory:
            memory.clear()
        tools = self.widgets.get('tools')
        if tools:
            tools.reset_counts()

        settings = self.control_bar.get_settings()
        self.runner.start(settings)

    def _stop(self):
        """Stop the agent."""
        self.runner.stop()

    def _pause(self, paused: bool):
        """Pause/resume the agent."""
        self.runner.pause(paused)

    def _reset(self):
        """Reset the agent state."""
        self.runner.reset()
        state = self.widgets.get('state')
        if state:
            state.reset()
        tools = self.widgets.get('tools')
        if tools:
            tools.reset_counts()
        memory = self.widgets.get('memory')
        if memory:
            memory.clear()
        log = self.widgets.get('log')
        if log:
            log.clear()

    def _launch_mgba(self):
        """Launch mGBA emulator."""
        log = self.widgets.get('log')
        if log:
            log.info("Launching mGBA...")

        launcher = GameLauncher()
        if launcher.launch():
            if log:
                log.success("mGBA launched")
            # Try to connect after launch
            self.root.after(2000, self._try_connect)
        else:
            if log:
                log.error("Failed to launch mGBA")


def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    Dashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
