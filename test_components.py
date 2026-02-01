"""
Test script for all UI components.
"""

import tkinter as tk
from tkinter import ttk
import sys

def test_imports():
    """Test that all components can be imported."""
    print("Testing imports...")

    try:
        from components import (
            ToolMap, InputPad, GameView, StateDisplay,
            ControlBar, ActivityLog, MemoryGrid, KnowledgeGraph,
            DockablePanel, DockManager, ResizableLayout,
            GridLayout, LayoutSelector
        )
        print("  [OK] All components imported successfully")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        return False

def test_control_bar():
    """Test ControlBar component."""
    print("\nTesting ControlBar...")

    from components import ControlBar

    root = tk.Tk()
    root.withdraw()

    try:
        cb = ControlBar(root)
        print("  [OK] ControlBar created")

        # Test get_settings
        settings = cb.get_settings()
        assert 'vision_interval' in settings, "Missing vision_interval"
        assert 'action_delay' in settings, "Missing action_delay"
        print(f"  [OK] get_settings() returns settings")

        # Test preflight
        preflight = cb.get_preflight_status()
        assert 'mgba_window' in preflight, "Missing mgba_window"
        print("  [OK] get_preflight_status() works")

        # Test set_preflight_status
        cb.set_preflight_status('mgba_window', True)
        cb.set_preflight_status('socket_connected', True)
        cb.set_preflight_status('rom_loaded', True)
        assert cb.is_preflight_ready() == True, "Preflight should be ready"
        print("  [OK] set_preflight_status() works")

        root.destroy()
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        root.destroy()
        return False

def test_activity_log():
    """Test ActivityLog component."""
    print("\nTesting ActivityLog...")

    from components import ActivityLog

    root = tk.Tk()
    root.withdraw()

    try:
        log = ActivityLog(root)
        log.pack()
        print("  [OK] ActivityLog created")

        log.info("Test info")
        log.action("Test action")
        log.warning("Test warning")
        log.error("Test error")
        log.success("Test success")
        print("  [OK] All log methods work")

        log.clear()
        print("  [OK] clear() works")

        root.destroy()
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        root.destroy()
        return False

def test_grid_layout():
    """Test GridLayout (VirtualGridLayout) component."""
    print("\nTesting GridLayout...")

    from components import GridLayout, LayoutSelector, ActivityLog

    root = tk.Tk()
    root.withdraw()

    try:
        # VirtualGridLayout uses grid_cols, grid_rows
        grid = GridLayout(root, grid_cols=16, grid_rows=9)
        grid.pack()
        print("  [OK] GridLayout created (16x9)")

        # Test add_component
        widget = grid.add_component(ActivityLog, 'log', row=0, col=0, rowspan=3, colspan=4)
        assert widget is not None, "add_component should return widget"
        print("  [OK] add_component() works")

        # Test get_component
        retrieved = grid.get_component('log')
        assert retrieved == widget, "get_component should return same widget"
        print("  [OK] get_component() works")

        # Test get_layout
        config = grid.get_layout()
        assert 'grid_cols' in config and 'grid_rows' in config
        print("  [OK] get_layout() works")

        # Test overlap detection
        overlap_widget = grid.add_component(ActivityLog, 'overlap', row=1, col=1, rowspan=2, colspan=2)
        assert overlap_widget is None, "Should not allow overlapping components"
        print("  [OK] Overlap detection works")

        # Test clear
        grid.clear()
        assert grid.get_component('log') is None
        print("  [OK] clear() works")

        # Test LayoutSelector (EditModeToggle)
        selector = LayoutSelector(root, grid)
        selector.pack()
        print("  [OK] LayoutSelector created")

        root.destroy()
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        root.destroy()
        return False

def test_game_view():
    """Test GameView component."""
    print("\nTesting GameView...")

    from components import GameView
    from PIL import Image

    root = tk.Tk()
    root.withdraw()

    try:
        gv = GameView(root, width=240, height=160)
        gv.pack()
        print("  [OK] GameView created")

        dummy_img = Image.new('RGB', (240, 160), color='red')
        gv.update_image(dummy_img)
        print("  [OK] update_image() works")

        root.destroy()
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        root.destroy()
        return False

def test_state_display():
    """Test StateDisplay component."""
    print("\nTesting StateDisplay...")

    from components import StateDisplay

    root = tk.Tk()
    root.withdraw()

    try:
        sd = StateDisplay(root)
        sd.pack()
        print("  [OK] StateDisplay created")

        sd.set_scene("battle")
        sd.set_player_hp(75)
        sd.set_enemy_hp(50)
        sd.set_step(100)
        sd.set_speed(10.5)
        print("  [OK] All setters work")

        sd.reset()
        print("  [OK] reset() works")

        root.destroy()
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        root.destroy()
        return False

def test_tool_map():
    """Test ToolMap component."""
    print("\nTesting ToolMap...")

    from components import ToolMap

    root = tk.Tk()
    root.withdraw()

    try:
        tm = ToolMap(root)
        tm.pack()
        print("  [OK] ToolMap created")

        tm.activate("vision")
        tm.deactivate("vision")
        print("  [OK] activate/deactivate work")

        tm.set_output("vision", "Detected: battle")
        print("  [OK] set_output() works")

        tm.reset_counts()
        print("  [OK] reset_counts() works")

        root.destroy()
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        root.destroy()
        return False

def test_input_pad():
    """Test InputPad component."""
    print("\nTesting InputPad...")

    from components import InputPad

    root = tk.Tk()
    root.withdraw()

    try:
        ip = InputPad(root)
        ip.pack()
        print("  [OK] InputPad created")

        ip.flash("a")
        ip.flash("up")
        print("  [OK] flash() works")

        root.destroy()
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        root.destroy()
        return False

def test_knowledge_graph():
    """Test KnowledgeGraph component."""
    print("\nTesting KnowledgeGraph...")

    from components import KnowledgeGraph

    root = tk.Tk()
    root.withdraw()

    try:
        kg = KnowledgeGraph(root)
        kg.pack()
        print("  [OK] KnowledgeGraph created")

        kg.set_scene("battle")
        kg.set_action("a", 100)
        kg.set_goal("win battle")
        print("  [OK] Setters work")

        kg.clear()
        print("  [OK] clear() works")

        root.destroy()
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        root.destroy()
        return False

def test_memory_grid():
    """Test MemoryGrid component."""
    print("\nTesting MemoryGrid...")

    from components import MemoryGrid

    root = tk.Tk()
    root.withdraw()

    try:
        mg = MemoryGrid(root)
        mg.pack()
        print("  [OK] MemoryGrid created")

        mg.clear()
        print("  [OK] clear() works")

        root.destroy()
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        root.destroy()
        return False

def run_all_tests():
    """Run all component tests."""
    print("=" * 50)
    print("COMPONENT TEST SUITE")
    print("=" * 50)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("ControlBar", test_control_bar()))
    results.append(("ActivityLog", test_activity_log()))
    results.append(("GridLayout", test_grid_layout()))
    results.append(("GameView", test_game_view()))
    results.append(("StateDisplay", test_state_display()))
    results.append(("ToolMap", test_tool_map()))
    results.append(("InputPad", test_input_pad()))
    results.append(("KnowledgeGraph", test_knowledge_graph()))
    results.append(("MemoryGrid", test_memory_grid()))

    print("\n" + "=" * 50)
    print("RESULTS SUMMARY")
    print("=" * 50)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
