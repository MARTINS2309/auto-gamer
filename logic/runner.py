"""
Agent Runner - Manages the agent run loop.

Handles:
- mGBA connection and management
- Vision capture and scene detection
- Decision making and action execution
- Evolution/learning integration
- Event emission for UI updates
"""

import time
import threading
from queue import Queue
from typing import Optional, Dict, Any, Set, List
from dataclasses import dataclass, field

from logic.consume import ScreenCapture
from logic.act import InputSender, GameLauncher, ActionBlockRunner, install_default_blocks
from logic.review import RunLogger, ScreenshotLogger
from logic.evolve import MemoryEvolution, KnowledgeGenome, GenomeStats
from logic.learn import RunAnalyst, SaveStateExperimenter, ActionBlockLearner


@dataclass
class RunnerSettings:
    """
    Settings for the agent runner.

    Frame-based timing for deterministic, reproducible training:
    - stride: frames between decisions (e.g., 10 = decide every 10 frames)
    - batch_size: actions per log entry (screenshot + summary per batch)
    - max_steps: total decisions to make (0 = unlimited)
    """
    stride: int = 10           # Frames between decisions (~6 decisions/sec at 60fps)
    batch_size: int = 5        # Actions per log entry
    max_steps: int = 0         # Total steps (0 = unlimited)
    auto_launch: bool = True
    turbo: bool = True
    use_learning: bool = True
    auto_train: bool = False   # Automatically start new runs after analysis
    train_runs: int = 10       # Number of runs in auto-train mode

    @classmethod
    def from_dict(cls, d: dict) -> 'RunnerSettings':
        return cls(
            stride=d.get('stride', 10),
            batch_size=d.get('batch_size', 5),
            max_steps=d.get('max_steps', 0),
            auto_launch=d.get('auto_launch', True),
            turbo=d.get('turbo', True),
            use_learning=d.get('use_learning', True),
            auto_train=d.get('auto_train', False),
            train_runs=d.get('train_runs', 10),
        )


class AgentRunner:
    """
    Manages the Pokemon AI agent run loop.

    Emits events via the event_queue for UI updates.
    All run logic lives here - app.py just wires events to UI.
    """

    def __init__(self, event_queue: Queue):
        self.events = event_queue

        # State
        self.running = False
        self.paused = False
        self.step_count = 0
        self.start_time: Optional[float] = None

        # Shared resources
        self.capture: Optional[ScreenCapture] = None
        self.sender: Optional[InputSender] = None

        # Thread management
        self._thread: Optional[threading.Thread] = None

    def emit(self, event_type: str, **kwargs):
        """Emit an event to the queue."""
        self.events.put({"type": event_type, **kwargs})

    def log(self, msg: str, level: str = "info"):
        """Emit a log event."""
        self.emit("log", msg=msg, level=level)

    @property
    def is_connected(self) -> bool:
        return self.sender is not None and self.sender.is_connected

    def try_connect(self) -> bool:
        """Try to connect to mGBA emulator."""
        self.capture = ScreenCapture()
        hwnd = self.capture.find_window("mGBA")

        if hwnd:
            self.sender = InputSender(hwnd)
            self.emit("sender", sender=self.sender)

            if self.sender.is_connected:
                self.log(f"Connected to mGBA (port {self.sender.socket_port})", "success")
                return True
            else:
                self.log("mGBA found - socket not available", "warning")
                self.log("Restart mGBA via Launch button to auto-load script", "info")
                return False
        else:
            self.log("mGBA not running - will connect on Start", "info")
            return False

    def start(self, settings: dict):
        """Start the agent run loop."""
        if self.running:
            return

        self.running = True
        self.paused = False
        self.step_count = 0
        self.start_time = time.time()

        run_settings = RunnerSettings.from_dict(settings)
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(run_settings,),
            daemon=True
        )
        self._thread.start()

    def stop(self):
        """Stop the agent run loop."""
        self.running = False

    def pause(self, paused: bool):
        """Set pause state."""
        self.paused = paused

    def reset(self):
        """Reset runner state."""
        self.step_count = 0

    def get_preflight_status(self) -> Dict[str, bool]:
        """Get preflight status for UI."""
        # Always do a fresh window search
        capture = self.capture or ScreenCapture()
        hwnd = capture.find_window("mGBA")
        window_valid = hwnd is not None and capture.is_window_valid(hwnd)

        # Check socket connection
        socket_ok = False
        rom_loaded = False

        if window_valid and self.sender:
            # Re-validate sender's hwnd matches current window
            if self.sender.hwnd != hwnd:
                # Window changed, need to reconnect
                self.sender = None
            else:
                socket_ok = self.sender.is_connected
                if socket_ok:
                    info = self.sender.get_info()
                    rom_loaded = info is not None

                    # Emit live memory data for MemoryGrid even when not running
                    if not self.running:
                        self._emit_live_memory()

        return {
            'mgba_window': window_valid,
            'socket_connected': socket_ok,
            'rom_loaded': rom_loaded,
        }

    def _emit_live_memory(self):
        """Emit memory reads for MemoryGrid when idle (not running)."""
        if not self.sender or not self.sender.is_connected:
            return

        game_state = self.sender.get_state()
        if game_state:
            self.emit("memory", reads=[
                {"addr": 0x02036E38, "value": game_state.x, "label": "PLAYER_X"},
                {"addr": 0x02036E3A, "value": game_state.y, "label": "PLAYER_Y"},
                {"addr": 0x02036E36, "value": game_state.map_num, "label": "MAP_NUM"},
                {"addr": 0x02022B4C, "value": 1 if game_state.battle else 0, "label": "BATTLE_FLAG"},
                {"addr": 0x02023BE4, "value": game_state.player_hp, "label": "PLAYER_HP"},
                {"addr": 0x02023BE6, "value": game_state.player_max_hp, "label": "PLAYER_MAX_HP"},
                {"addr": 0x02023C08, "value": game_state.enemy_hp, "label": "ENEMY_HP"},
                {"addr": 0x02023C0A, "value": game_state.enemy_max_hp, "label": "ENEMY_MAX_HP"},
                {"addr": 0x02023C00, "value": game_state.enemy_species, "label": "ENEMY_SPECIES"},
                {"addr": 0x02024029, "value": game_state.party_count, "label": "PARTY_COUNT"},
                {"addr": 0x02025000, "value": game_state.money, "label": "MONEY"},
                {"addr": 0x02025028, "value": game_state.badges, "label": "BADGES"},
            ])

    def _run_loop(self, settings: RunnerSettings):
        """Main agent run loop (runs in background thread)."""
        max_steps = settings.max_steps
        auto_train = settings.auto_train
        train_runs = settings.train_runs

        # Track training progress
        run_number = 0
        max_runs = train_runs if auto_train else 1

        while self.running and run_number < max_runs:
            run_number += 1
            if auto_train:
                self.log(f"=== TRAINING RUN {run_number}/{max_runs} ===", "success")

            self._execute_single_run(settings, run_number)

            # Brief pause between runs in auto-train mode
            if auto_train and run_number < max_runs and self.running:
                self.log("Starting next run in 3s...", "info")
                time.sleep(3)

        if auto_train:
            self.log(f"=== TRAINING COMPLETE ({run_number} runs) ===", "success")

        self.running = False

    def _execute_single_run(self, settings: RunnerSettings, run_number: int = 1):
        """Execute a single training run with frame-based timing."""
        stride = settings.stride          # Frames between decisions
        batch_size = settings.batch_size  # Actions per log batch
        max_steps = settings.max_steps
        auto_launch = settings.auto_launch
        use_turbo = settings.turbo
        use_evolution = settings.use_learning

        # Init modules - reuse existing if available
        capture = self.capture or ScreenCapture()
        logger = RunLogger()
        launcher = GameLauncher()
        screenshot_log = ScreenshotLogger()
        sender = self.sender

        # Action blocks for scripted sequences (intro, menus, etc.)
        block_runner: ActionBlockRunner = None

        # Evolution system - get genome for this run
        evolution = MemoryEvolution()
        if use_evolution:
            genome = evolution.get_genome()
            self.log(f"Using genome {genome.id} (gen {genome.generation})", "success")
            self.emit("genome", genome=genome)
            self.emit("rules", genome=genome)
        else:
            genome = KnowledgeGenome()
            self.emit("rules", genome=genome)

        # Track stats for this run
        run_stats = GenomeStats()
        last_position = None
        visited_maps: Set[int] = set()
        last_party_count = 0
        last_badges = 0
        last_player_hp = 100

        # Find or launch mGBA
        if not sender or not sender.is_connected:
            hwnd = capture.find_window("mGBA")

            if not hwnd:
                if auto_launch:
                    self.log("Launching mGBA...", "info")
                    if launcher.launch():
                        hwnd = launcher.window_handle
                        capture.hwnd = hwnd
                    else:
                        self.log("Failed to launch mGBA!", "error")
                        self.running = False
                        return
                else:
                    self.log("mGBA not found!", "error")
                    self.running = False
                    return

            sender = InputSender(hwnd)
            self.sender = sender
            self.log(f"mGBA ready (hwnd={hwnd})", "success")
            self.emit("sender", sender=sender)
        else:
            self.log("Using existing mGBA connection", "success")

        # Check connection status
        if sender.is_connected:
            self.log(f"Socket connected (port {sender.socket_port})", "success")
            # Wire sender to capture for socket-based screenshots
            capture.set_sender(sender)
        else:
            self.log("Socket not available - using PostMessage fallback", "warning")
            self.log("Load ai_control.lua in mGBA for full features", "info")

        # Reset ROM for uniform starting conditions (title screen)
        if sender.use_socket:
            self.log("Resetting ROM for uniform start...", "info")
            if sender.reset():
                time.sleep(0.5)  # Wait for reset to complete
                self.log("ROM reset to title screen", "success")
            else:
                self.log("ROM reset failed - continuing from current state", "warning")

        # Save initial checkpoint
        if sender.use_socket:
            sender.save_state(0)
            self.log("Saved checkpoint (slot 0)", "info")

        # Speed mode selection:
        # - Socket mode: Use frame_advance exclusively (deterministic, no Tab turbo)
        # - Fallback mode: Use Tab turbo + time.sleep (fast but non-deterministic)
        use_frame_stepping = sender.use_socket

        if use_turbo and not use_frame_stepping:
            # Only use Tab turbo in fallback mode (no socket)
            sender.enable_turbo()
            self.log("Turbo mode enabled (fallback)", "info")
        elif use_frame_stepping:
            self.log("Frame-step mode (deterministic)", "success")

        # Initialize action blocks for scripted sequences
        block_runner = ActionBlockRunner(sender)
        if len(block_runner.blocks) == 0:
            self.log("Installing default action blocks...", "info")
            install_default_blocks(block_runner)
        self.log(f"Action blocks: {len(block_runner.blocks)} loaded", "info")

        logger.start_run()
        screenshot_log.start_run(genome.id)
        self.log(f"Screenshots: {screenshot_log.run_dir}", "info")
        self.log(f"Settings: stride={stride} frames, batch={batch_size} actions", "info")

        step = 0
        frame = 0
        scene = "unknown"
        game_state = None
        in_battle = False
        prev_battle = False

        # Batched logging: collect actions, log with one screenshot per batch
        batch_actions: List[str] = []
        batch_start_step = 0
        batch_start_frame = 0

        save_state_interval = 500
        save_state_slot = 1
        health_check_interval = 50
        reconnect_attempts = 0
        max_reconnect_attempts = 3

        try:
            while self.running:
                if self.paused:
                    if sender and sender.turbo_active:
                        sender.disable_turbo()
                    time.sleep(0.1)
                    continue
                else:
                    # Only re-enable Tab turbo in fallback mode
                    if use_turbo and not use_frame_stepping and sender and not sender.turbo_active:
                        sender.enable_turbo()

                if max_steps > 0 and step >= max_steps:
                    break

                step += 1
                self.step_count = step

                # Connection health check (every N steps)
                if step % health_check_interval == 0 and sender:
                    if not sender.check_connection():
                        self.log("Connection lost to mGBA!", "error")
                        while reconnect_attempts < max_reconnect_attempts:
                            reconnect_attempts += 1
                            self.log(f"Reconnect attempt {reconnect_attempts}/{max_reconnect_attempts}...", "warning")
                            if sender.reconnect():
                                self.log("Reconnected to mGBA!", "success")
                                reconnect_attempts = 0
                                break
                            time.sleep(1)
                        else:
                            self.log("Failed to reconnect. Stopping run.", "error")
                            break
                    else:
                        reconnect_attempts = 0

                # Get current game state (every step for accurate decisions)
                self.emit("tool_on", tool="vision")
                game_state = sender.get_state()
                if game_state:
                    scene = game_state.scene
                    frame = game_state.frame

                    # Update UI state
                    hp_pct = int(100 * game_state.player_hp / max(1, game_state.player_max_hp)) if game_state.player_max_hp else 100
                    enemy_pct = int(100 * game_state.enemy_hp / max(1, game_state.enemy_max_hp)) if game_state.enemy_max_hp else 100
                    self.emit("state", state={
                        "battle": game_state.battle,
                        "player_hp": hp_pct,
                        "enemy_hp": enemy_pct,
                        "x": game_state.x,
                        "y": game_state.y,
                        "map": game_state.map_num,
                        "frame": frame,
                    })

                    # Emit memory reads for visualization
                    self.emit("memory", reads=[
                        {"addr": 0x02036E38, "value": game_state.x, "label": "PLAYER_X"},
                        {"addr": 0x02036E3A, "value": game_state.y, "label": "PLAYER_Y"},
                        {"addr": 0x02036E36, "value": game_state.map_num, "label": "MAP_NUM"},
                        {"addr": 0x02022B4C, "value": 1 if game_state.battle else 0, "label": "BATTLE_FLAG"},
                        {"addr": 0x02023BE4, "value": game_state.player_hp, "label": "PLAYER_HP"},
                        {"addr": 0x02023C08, "value": game_state.enemy_hp, "label": "ENEMY_HP"},
                        {"addr": 0x02024029, "value": game_state.party_count, "label": "PARTY_COUNT"},
                        {"addr": 0x02025028, "value": game_state.badges, "label": "BADGES"},
                    ])

                    # Track stats
                    in_battle = game_state.battle
                    if prev_battle and not in_battle:
                        if game_state.player_hp > 0:
                            run_stats.battles_won += 1
                        else:
                            run_stats.battles_lost += 1
                    prev_battle = in_battle

                    if game_state.party_count > last_party_count and last_party_count > 0:
                        caught = game_state.party_count - last_party_count
                        run_stats.pokemon_caught += caught
                        self.log(f"Caught {caught} Pokemon!", "success")
                    last_party_count = game_state.party_count

                    if game_state.badges > last_badges:
                        earned = game_state.badges - last_badges
                        run_stats.badges_earned += earned
                        self.log(f"Earned {earned} badge(s)!", "success")
                    last_badges = game_state.badges

                    if last_player_hp > 0 and game_state.player_hp == 0 and game_state.player_max_hp > 0:
                        run_stats.deaths += 1
                        self.log("Pokemon fainted!", "warning")
                    last_player_hp = game_state.player_hp

                    pos = (game_state.x, game_state.y, game_state.map_num)
                    if last_position and pos != last_position:
                        run_stats.distance_traveled += 1
                    last_position = pos

                    visited_maps.add(game_state.map_num)
                    run_stats.unique_maps_visited = len(visited_maps)
                    run_stats.max_money = max(run_stats.max_money, game_state.money)

                    self.emit("run_stats", stats={
                        "battles_won": run_stats.battles_won,
                        "battles_lost": run_stats.battles_lost,
                        "pokemon_caught": run_stats.pokemon_caught,
                        "badges_earned": run_stats.badges_earned,
                    })

                    goal = {
                        "battle": "win battle" if not game_state.can_catch else "catch pokemon",
                        "dialogue": "read text",
                        "menu": "navigate menu",
                        "title": "start game",
                        "overworld": "explore",
                    }.get(scene, "explore")
                    self.emit("goal", goal=goal)
                else:
                    scene = "overworld"

                self.emit("tool_off", tool="vision")
                self.emit("scene", scene=scene)

                # Check for action blocks (scripted sequences)
                # These take priority over genome decisions for deterministic sections
                action = None
                reason = ""

                if block_runner and game_state:
                    if not block_runner.current_block:
                        triggered_block = block_runner.check_triggers(game_state)
                        if triggered_block:
                            self.log(f"Action block triggered: {triggered_block.name}", "success")
                            block_runner.start_block(triggered_block)
                            self.emit("strategy", strategy="block", reason=triggered_block.name)

                    if block_runner.current_block:
                        block_runner.capture_data(game_state)
                        if not block_runner.execute_step():
                            action = "block"
                            reason = f"block:{block_runner.current_block.name}"

                # Decide using genome (when no action block is active)
                if action is None:
                    self.emit("tool_on", tool="rules")
                    action = genome.decide(scene)
                    weight = genome.weights.get(scene, {}).get(action, 1.0)
                    reason = f"w={weight:.2f}"
                    self.emit("decision", reason=f"{scene} → {action}: {reason}")
                    self.emit("strategy", strategy=action, reason=reason)
                    self.emit("active_rule", scene=scene, action=action, weight=weight)
                    self.emit("tool_off", tool="rules")

                    # Execute action
                    self.emit("tool_on", tool="input")
                    sender.send(action)
                    self.emit("tool_off", tool="input")

                self.emit("action", action=action)
                self.emit("step", step=step)

                # Add to current batch
                batch_actions.append(action)

                # Log batch when full
                if len(batch_actions) >= batch_size:
                    # Take screenshot for this batch
                    img = capture.capture()
                    if img:
                        self.emit("image", image=img)

                    # Summarize batch actions
                    action_summary = ",".join(batch_actions)
                    frames_elapsed = frame - batch_start_frame if batch_start_frame else stride * batch_size

                    # Log to file with batch info
                    logger.log_step(step, time.time(), scene, action_summary, f"batch:{batch_start_step}-{step} f:{frames_elapsed}")

                    # Log screenshot with batch data
                    if game_state:
                        screenshot_log.log_screenshot(
                            sender, step, scene, action_summary,
                            f"steps:{batch_start_step}-{step}", game_state, 1.0
                        )

                    # Emit summary to UI
                    self.emit("log", msg=f"[{batch_start_step}-{step}] {scene}: {action_summary}", level="action")

                    # Reset batch
                    batch_actions = []
                    batch_start_step = step + 1
                    batch_start_frame = frame

                # Update speed display
                elapsed = time.time() - self.start_time if self.start_time else 1
                if elapsed > 0:
                    self.emit("speed", speed=step / elapsed)

                # Periodic save states
                if sender and sender.use_socket and step % save_state_interval == 0 and step > 0:
                    sender.save_state(save_state_slot)
                    self.log(f"Checkpoint saved (slot {save_state_slot})", "info")
                    save_state_slot = (save_state_slot % 7) + 1

                # Advance emulation by stride frames (frame-based timing)
                if sender.use_socket:
                    sender.frame_advance(stride)
                else:
                    # Fallback to time-based if no socket
                    time.sleep(stride / 60.0)  # Approximate at 60fps

        except Exception as e:
            self.log(f"Error: {e}", "error")
        finally:
            # Cleanup
            if sender and sender.turbo_active:
                sender.disable_turbo()

            run_stats.total_steps = step
            run_stats.playtime_seconds = time.time() - self.start_time if self.start_time else 0

            if use_evolution:
                evolution.complete_run(genome, run_stats)
                self.log(f"Genome {genome.id} fitness: {genome.fitness():.1f}", "success")
                pop_stats = evolution.get_stats()
                self.log(f"Population: {pop_stats['population']} genomes, best: {pop_stats.get('best_fitness', 0):.1f}", "info")

            # Run summary
            self.log("=== RUN SUMMARY ===", "info")
            self.log(f"Steps: {run_stats.total_steps} | Time: {run_stats.playtime_seconds:.1f}s", "info")
            self.log(f"Battles: {run_stats.battles_won}W / {run_stats.battles_lost}L | Deaths: {run_stats.deaths}", "info")
            self.log(f"Caught: {run_stats.pokemon_caught} | Badges: {run_stats.badges_earned}", "info")
            self.log(f"Maps: {run_stats.unique_maps_visited} | Distance: {run_stats.distance_traveled}", "info")
            self.log(f"Max Money: ${run_stats.max_money}", "info")

            log_path = logger.end_run()
            self.log(f"Saved log: {log_path}", "info")
            screenshot_path = screenshot_log.end_run(run_stats)
            self.log(f"Screenshots: {screenshot_path}", "info")

            # AI Analysis
            if use_evolution and screenshot_log.run_dir:
                self._run_analysis(screenshot_log, sender, genome, evolution)

            self.log("Run complete", "info")

    def _run_analysis(self, screenshot_log, sender, genome, evolution):
        """Run AI analysis phase after a run."""
        self.log("=== AI ANALYSIS ===", "info")

        try:
            analyst = RunAnalyst()
            result = analyst.analyze_run(screenshot_log.run_dir)

            if result:
                self.log(f"Score: {result.overall_score:.2f}", "info")

                for obs in result.observations[:3]:
                    self.log(f"  • {obs}", "info")

                # Test changes if socket available - use multi-approach testing
                if sender and sender.use_socket and result.weight_adjustments:
                    self.log("Testing multiple approaches with save states...", "info")
                    experimenter = SaveStateExperimenter(sender)

                    improvement, all_results, best_approach = experimenter.test_multiple_approaches(
                        genome, result, test_steps=100
                    )

                    result.tested_changes = True
                    result.test_improvement = improvement

                    # Log all approach results
                    self.log(f"Baseline: {all_results.get('baseline', 0):.1f}", "info")
                    self.log(f"Proposed: {all_results.get('proposed', 0):.1f}", "info")
                    self.log(f"Opposite: {all_results.get('opposite', 0):.1f}", "info")
                    self.log(f"Random:   {all_results.get('random', 0):.1f}", "info")
                    self.log(f"Amplified:{all_results.get('amplified', 0):.1f}", "info")
                    self.log(f"Best approach: {best_approach} ({improvement:+.1%})", "success" if improvement > 0 else "warning")

                # ALWAYS apply some learning - the key fix
                # If tested and improved: apply full changes
                # If tested and neutral/worse: apply with reduced weight
                # If not tested: apply anyway (we need to try things)
                should_apply = True
                apply_scale = 1.0

                if result.tested_changes:
                    if result.test_improvement > 0.1:
                        apply_scale = 1.5  # Amplify good changes
                        self.log("Amplifying successful changes", "success")
                    elif result.test_improvement < -0.1:
                        apply_scale = -0.5  # Reverse bad changes
                        self.log("Reversing unsuccessful changes", "warning")
                    else:
                        apply_scale = 0.5  # Apply with caution
                        self.log("Applying changes cautiously", "info")
                else:
                    self.log("Applying untested changes", "info")

                if should_apply and result.weight_adjustments:
                    # Scale the adjustments
                    for scene in result.weight_adjustments:
                        for action in result.weight_adjustments[scene]:
                            result.weight_adjustments[scene][action] *= apply_scale

                    if analyst.apply_to_genome(result, genome):
                        evolution.save_genome(genome)
                        self.log(f"Updated genome weights (scale: {apply_scale:.1f}x)", "success")

                # Evolve population periodically
                pop_stats = evolution.get_stats()
                if pop_stats.get("total_runs", 0) % 5 == 0:
                    self.log("Evolving population...", "info")
                    evolution.evolve_generation()
                    new_stats = evolution.get_stats()
                    self.log(f"Population: {new_stats['population']} genomes", "info")

                    # Also check for new action block patterns every 5 runs
                    try:
                        block_learner = ActionBlockLearner()
                        suggestions = block_learner.suggest_blocks()
                        if suggestions:
                            self.log(f"Found {len(suggestions)} potential action blocks:", "info")
                            for sug in suggestions[:3]:
                                self.log(f"  • {sug['suggested_name']} ({sug['occurrences']}x)", "info")
                    except Exception as be:
                        pass  # Don't fail on block learning errors

                for rec in result.recommendations[:2]:
                    self.log(f"  → {rec}", "info")
            else:
                self.log("No analysis results", "warning")

        except Exception as e:
            self.log(f"Analysis error: {e}", "error")
