# Pokemon AI Agent - Complete Setup Plan

## Overview

This document provides a complete step-by-step plan to install all prerequisites, configure the environment, and run the Pokemon AI agent that learns to play the game by watching the screen.

**Target System**: Windows 11, Ryzen 7800X3D, 32GB RAM, AMD 7900 XTX (24GB VRAM)

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Architecture Overview](#2-architecture-overview)
3. [Module Definitions](#3-module-definitions)
4. [Installation Steps](#4-installation-steps)
5. [Configuration](#5-configuration)
6. [Verification Tests](#6-verification-tests)
7. [Running the Agent](#7-running-the-agent)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. System Requirements

### Your Hardware (Excellent!)

| Component | Your Specs | Notes |
|-----------|------------|-------|
| CPU | Ryzen 7800X3D | Has integrated GPU (gfx1036) - may need config |
| RAM | 32 GB | More than enough |
| GPU | 7900 XTX (24GB) | gfx1100 - **Officially supported by Ollama ROCm** |
| Storage | 4TB SSD | Plenty of space |
| Network | 1Gb fiber | Fast model downloads |

### Operating System

- **Windows 11** (Native) ✅ **RECOMMENDED**
  - Full ROCm support for 7900 XTX
  - Native emulator support
  - pyautogui works perfectly

- ~~WSL2~~ ❌ Not recommended
  - Cannot capture Windows screen from WSL2
  - ROCm passthrough is problematic
  - Adds unnecessary complexity

### Software Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Runtime environment |
| Ollama | Latest | Local LLM inference (with ROCm/GPU) |
| AMD Adrenalin | Latest | GPU drivers with ROCm support |
| mGBA | Latest | GBA emulator |

### GPU Performance Expectations

With your 7900 XTX and Ollama using ROCm:

| Model | VRAM Usage | Inference Speed |
|-------|------------|-----------------|
| llava:7b | ~5 GB | ~0.5-1 second |
| llava:13b | ~10 GB | ~1-2 seconds |
| llava:34b | ~20 GB | ~3-5 seconds |

Your 24GB VRAM can run even the largest vision models!

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        POKEMON AI AGENT                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   SCREEN     │    │  VISION MODULE   │    │   RL MODULE      │  │
│  │   CAPTURE    │───▶│  (Local LLaVA)   │───▶│   (PPO Agent)    │  │
│  │   (mss)      │    │                  │    │                  │  │
│  └──────────────┘    └──────────────────┘    └──────────────────┘  │
│         │                    │                        │             │
│         │              PokemonState              Action             │
│         │              - scene_type             Selection           │
│         │              - in_battle                  │               │
│         │              - player_hp                  │               │
│         │              - enemy_hp                   │               │
│         │              - can_catch                  ▼               │
│         │                                   ┌──────────────────┐   │
│         │                                   │  INPUT MODULE    │   │
│         │                                   │  (pyautogui)     │   │
│         │                                   └──────────────────┘   │
│         │                                           │               │
│         │                                           ▼               │
│         │    ┌──────────────────────────────────────────────────┐  │
│         └────│              GBA EMULATOR (mGBA)                 │  │
│              │              Running Pokemon ROM                  │  │
│              └──────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Screen Capture**: `mss` library captures emulator window at ~60 FPS
2. **Vision Processing**: Image sent to local LLaVA model via Ollama API
3. **State Extraction**: LLM response parsed into structured `PokemonState`
4. **Decision Making**: PPO agent selects action based on state vector
5. **Input Execution**: `pyautogui` sends keypress to emulator
6. **Loop**: Process repeats every ~0.3-2 seconds

---

## 3. Module Definitions

### 3.1 Core Python Packages

| Package | Version | Purpose | Install Size |
|---------|---------|---------|--------------|
| `mss` | ≥9.0.0 | Fast cross-platform screen capture | ~50 KB |
| `pyautogui` | ≥0.9.54 | Keyboard/mouse automation | ~100 KB |
| `numpy` | ≥1.24.0 | Numerical operations, array handling | ~15 MB |
| `pillow` | ≥10.0.0 | Image processing and format conversion | ~3 MB |
| `requests` | ≥2.31.0 | HTTP client for Ollama API | ~500 KB |
| `gymnasium` | ≥0.29.0 | Reinforcement learning environment interface | ~2 MB |
| `stable-baselines3` | ≥2.2.0 | PPO algorithm implementation | ~5 MB |

### 3.2 Project Files

| File | Purpose |
|------|---------|
| `vision_classifier.py` | Generic screen-to-state classification using local VLM |
| `rl_agent.py` | Generic RL environment and PPO agent wrapper |
| `pokemon_agent.py` | Pokemon-specific state detection, rewards, and actions |
| `main.py` | CLI entry point for generic games |
| `test_input.py` | Utility to verify emulator key mappings |

### 3.3 External Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| **Ollama** | Local LLM runtime | Runs LLaVA vision model |
| **LLaVA 7B** | Vision-language model | ~4 GB VRAM required |
| **mGBA** | GBA emulator | Or any GBA emulator |
| **Pokemon ROM** | Game to play | User-provided |

---

## 4. Installation Steps

### Step 1: Install AMD GPU Drivers

**IMPORTANT**: Your 7800X3D has an integrated GPU (gfx1036) alongside your 7900 XTX (gfx1100). Ollama may get confused and try to use the wrong one. We'll configure this.

```powershell
# 1. Download latest AMD Adrenalin drivers from:
#    https://www.amd.com/en/support
#    Select: Graphics → AMD Radeon™ RX 7000 Series → AMD Radeon™ RX 7900 XTX

# 2. Run installer, select "Full Install" to get ROCm/HIP components

# 3. Restart your PC after installation
```

### Step 2: Install Python

```powershell
# Option A: Microsoft Store (easiest)
# Search "Python 3.11" in Microsoft Store and install

# Option B: Official installer
# Download from https://www.python.org/downloads/
# ⚠️ CHECK "Add Python to PATH" during installation

# Verify installation (open new PowerShell window)
python --version
# Should show: Python 3.11.x or 3.12.x
```

### Step 3: Create Project Environment

```powershell
# Open PowerShell as Administrator (for first-time setup)

# Create project directory
mkdir C:\Projects\pokemon-agent
cd C:\Projects\pokemon-agent

# Create virtual environment
python -m venv venv

# Allow script execution (one-time)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# You should see (venv) in your prompt now
```

### Step 4: Install Python Packages

```powershell
# Make sure venv is activated: (venv) should appear in prompt

# Upgrade pip
python -m pip install --upgrade pip

# Install all required packages
pip install mss pyautogui numpy pillow requests gymnasium stable-baselines3

# Verify installation
python -c "import mss, pyautogui, numpy, gymnasium; print('All packages OK')"
```

### Step 5: Install Ollama

```powershell
# 1. Download Ollama for Windows from:
#    https://ollama.com/download/windows

# 2. Run OllamaSetup.exe

# 3. Ollama starts automatically as a Windows service

# 4. Verify installation (open new PowerShell)
ollama --version
```

### Step 6: Configure Ollama for Your GPU

**CRITICAL**: Because you have both an integrated GPU (7800X3D) and discrete GPU (7900 XTX), you need to tell Ollama which one to use.

```powershell
# Check which GPUs Ollama sees
ollama serve
# Look for lines like:
#   Device 0: AMD Radeon(TM) Graphics, gfx1036  ← Integrated (IGNORE)
#   Device 1: AMD Radeon RX 7900 XTX, gfx1100   ← Your GPU (USE THIS)

# Stop Ollama (Ctrl+C)

# Set environment variable to use only the 7900 XTX
# Find the device number for gfx1100 (likely 1, but check logs)

# Method 1: Set for current session
$env:ROCR_VISIBLE_DEVICES = "1"  # Use the device number for 7900 XTX

# Method 2: Set permanently (recommended)
[System.Environment]::SetEnvironmentVariable("ROCR_VISIBLE_DEVICES", "1", "User")
```

**Alternative: Set via System Properties**
1. Press Win+R, type `sysdm.cpl`, press Enter
2. Advanced tab → Environment Variables
3. Under "User variables", click New
4. Variable name: `ROCR_VISIBLE_DEVICES`
5. Variable value: `1` (or whichever device is your 7900 XTX)
6. Click OK, restart Ollama

### Step 7: Download Vision Model

```powershell
# Pull the vision model (downloads ~4GB)
ollama pull llava:7b

# For better accuracy (your GPU can handle it!)
ollama pull llava:13b

# Verify model is using GPU
ollama run llava:7b "describe this test"
# Check Task Manager → Performance → GPU 1
# Should show activity on your 7900 XTX
```

### Step 8: Install mGBA Emulator

1. Download from: https://mgba.io/downloads.html
   - Get "Windows (64-bit, installer)" or portable zip
2. Install to default location or `C:\Programs\mGBA\`
3. Open mGBA
4. Load your Pokemon ROM: File → Load ROM

### Step 9: Configure mGBA

**Window Settings:**
- Emulation → Video size → 2x or 3x (not fullscreen)
- Keep window fully visible during training

**Verify Key Bindings** (Tools → Settings → Keyboard):

| Button | Default Key | Our Code Expects |
|--------|-------------|------------------|
| A | X | X ✓ |
| B | Z | Z ✓ |
| Start | Enter | Enter ✓ |
| Select | Backspace | Backspace ✓ |
| Up | ↑ | ↑ ✓ |
| Down | ↓ | ↓ ✓ |
| Left | ← | ← ✓ |
| Right | → | → ✓ |

### Step 10: Download Project Files

Save all project files to `C:\Projects\pokemon-agent\`:

```
pokemon-agent/
├── venv/                    # Created in Step 3
├── vision_classifier.py     # Vision module
├── rl_agent.py             # RL module  
├── pokemon_agent.py        # Pokemon-specific agent
├── main.py                 # Generic CLI
├── test_input.py           # Input testing
├── requirements.txt        # Dependencies
└── SETUP_PLAN.md          # This document
```

---

## 5. Configuration

### 5.1 Emulator Key Mapping

If your emulator uses different keys, edit `pokemon_agent.py`:

```python
class EmulatorKeys:
    MGBA = {
        "a": "x",           # Change these to match
        "b": "z",           # your emulator's bindings
        "start": "enter",
        "select": "backspace",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "l": "a",
        "r": "s",
    }
```

### 5.2 Vision Model Selection

| Model | VRAM | Speed | Accuracy | Command |
|-------|------|-------|----------|---------|
| llava:7b | ~4 GB | ~1.5s | Good | `ollama pull llava:7b` |
| llava:13b | ~8 GB | ~3s | Better | `ollama pull llava:13b` |
| llava:34b | ~20 GB | ~8s | Best | `ollama pull llava:34b` |
| bakllava | ~4 GB | ~1.5s | Good | `ollama pull bakllava` |

To use a different model:

```bash
python pokemon_agent.py train --model llava:13b
```

### 5.3 Training Parameters

Edit `pokemon_agent.py` to adjust:

```python
class PokemonEnv:
    def __init__(
        self,
        step_delay: float = 0.3,        # Time between actions (seconds)
        max_episode_steps: int = 2000,  # Steps before episode reset
    ):
        ...

class PokemonAgent:
    def _setup_model(self):
        self.model = PPO(
            "MlpPolicy",
            self.env,
            learning_rate=3e-4,    # Learning rate
            n_steps=512,           # Steps before policy update
            batch_size=64,         # Batch size for training
            ent_coef=0.05,         # Exploration coefficient
            policy_kwargs={"net_arch": [128, 128]}  # Network size
        )
```

---

## 6. Verification Tests

Run these tests in order to verify everything works.

### Test 1: Python Environment

```powershell
cd C:\Projects\pokemon-agent
.\venv\Scripts\Activate.ps1

python -c "
import mss
import pyautogui
import numpy as np
from PIL import Image
import requests
import gymnasium
from stable_baselines3 import PPO
print('✓ All Python packages installed correctly')
"
```

**Expected**: `✓ All Python packages installed correctly`

### Test 2: Ollama Connection & GPU Detection

```powershell
# Check Ollama is running and using GPU
ollama list

# Run a quick test
ollama run llava:7b "say hello"

# While running, check GPU usage:
# Open Task Manager → Performance → GPU 1 (your 7900 XTX)
# Should show activity
```

**Expected**: Response from model, GPU utilization visible

### Test 3: Verify Correct GPU is Being Used

```powershell
# Check Ollama logs for GPU selection
# Look for "gfx1100" (7900 XTX) not "gfx1036" (integrated)

ollama serve
# Output should show something like:
# "loading library=ROCm compute=gfx1100"
```

If you see `gfx1036`, the integrated GPU is being used. Set `ROCR_VISIBLE_DEVICES` as described in Step 6.

### Test 4: Screen Capture

```powershell
python -c "
import mss
with mss.mss() as sct:
    img = sct.grab(sct.monitors[1])
    print(f'Screen: {img.width}x{img.height}')
    print('✓ Screen capture OK')
"
```

**Expected**: Your screen resolution and success message

### Test 5: Vision Model Speed Test

```powershell
python -c "
import requests
import base64
import time
from PIL import Image
from io import BytesIO

# Create test image
img = Image.new('RGB', (512, 512), color='blue')
buffer = BytesIO()
img.save(buffer, format='PNG')
img_b64 = base64.b64encode(buffer.getvalue()).decode()

start = time.time()
response = requests.post(
    'http://localhost:11434/api/generate',
    json={
        'model': 'llava:7b',
        'prompt': 'What color is this image? Be brief.',
        'images': [img_b64],
        'stream': False
    },
    timeout=60
)
elapsed = time.time() - start

print(f'Response: {response.json().get(\"response\", \"\")[:50]}')
print(f'Time: {elapsed:.2f} seconds')
print('✓ Vision model working' if elapsed < 5 else '⚠️ Slow - check GPU')
"
```

**Expected with GPU**: Response in ~0.5-2 seconds
**If CPU only**: Response in ~5-10 seconds (need to fix GPU config)

### Test 6: Keyboard Input to Emulator

```powershell
# Open mGBA with Pokemon loaded first!

python test_input.py mgba
# Select option 1 (test all buttons)
# QUICKLY click on mGBA window within 5 seconds
# Watch for button presses registering in game
```

**Expected**: All buttons register in emulator

### Test 7: Full Vision Classifier Test

```powershell
# Have mGBA open with Pokemon running (overworld or start a battle)

python pokemon_agent.py demo --emulator mgba
# Click on mGBA window within 5 seconds to keep it visible
```

**Expected**: 5 classifications showing scene type, HP levels, etc.

---

## 7. Running the Agent

### Every Session Startup

```powershell
# PowerShell Window 1: Ollama should auto-start as service
# But if needed, manually start:
ollama serve

# PowerShell Window 2: Run the agent
cd C:\Projects\pokemon-agent
.\venv\Scripts\Activate.ps1

# Open mGBA, load Pokemon ROM, navigate to grass area
# Create save state: Shift+F1

# Test classifier first
python pokemon_agent.py demo

# Train the agent
python pokemon_agent.py train --steps 20000

# Watch it play
python pokemon_agent.py play --steps 500
```

### Command Reference

| Command | Description |
|---------|-------------|
| `python pokemon_agent.py demo` | Test vision classifier (5 captures) |
| `python pokemon_agent.py train --steps N` | Train for N steps |
| `python pokemon_agent.py play --steps N` | Run trained agent |
| `python pokemon_agent.py train --model llava:13b` | Use larger model |
| `python test_input.py mgba` | Test emulator key mappings |
| `python main.py check` | Verify all dependencies |

### Training Session Workflow

1. **Open mGBA** → Load ROM → Get to tall grass area
2. **Create Save State** (Shift+F1) - You'll restore this if training goes wrong
3. **Position Windows** - mGBA fully visible, not overlapped
4. **Start Training** - `python pokemon_agent.py train --steps 20000`
5. **Monitor** - Watch the terminal for reward trends
6. **Speed Up** (Optional) - Press Tab in mGBA to fast-forward

### Performance Tips

With your 7900 XTX:
- Use `llava:13b` for better accuracy (you have the VRAM)
- Set `step_delay=0.2` for faster training (model responds quickly)
- Run 50,000+ steps for meaningful learning

---

## 8. Troubleshooting

### Issue: Ollama using CPU instead of GPU

**Symptoms**: Slow inference (5+ seconds), no GPU activity in Task Manager

**Fix 1**: Check which GPU Ollama sees
```powershell
ollama serve
# Look for gfx1100 (7900 XTX) vs gfx1036 (integrated)
```

**Fix 2**: Force correct GPU
```powershell
# Set environment variable
$env:ROCR_VISIBLE_DEVICES = "1"  # Adjust number based on logs
ollama serve
```

**Fix 3**: Set permanently via System Environment Variables
1. Win+R → `sysdm.cpl` → Advanced → Environment Variables
2. Add User variable: `ROCR_VISIBLE_DEVICES` = `1`
3. Restart Ollama

### Issue: "ROCm error: invalid device function"

This is a known bug in some Ollama versions (0.11.5+).

**Fix**: Use an older Ollama version
```powershell
# Uninstall current Ollama
# Download 0.11.4 from: https://github.com/ollama/ollama/releases/tag/v0.11.4
# Install that version instead
```

### Issue: Keys not registering in emulator

**Fix 1**: Click on mGBA window to focus it BEFORE running agent

**Fix 2**: Verify key bindings match
```powershell
python test_input.py mgba
# Select interactive mode (option 4)
# Test each key individually
```

**Fix 3**: Edit `EmulatorKeys.MGBA` in `pokemon_agent.py` to match your bindings

### Issue: Screen capture shows wrong monitor

```python
# Edit vision_classifier.py, change monitor index:
screenshot = self._sct.grab(sct.monitors[2])  # Try 2 instead of 1
```

### Issue: Classification always returns "unknown"

**Fix 1**: Use larger model
```powershell
ollama pull llava:13b
python pokemon_agent.py demo --model llava:13b
```

**Fix 2**: Ensure emulator window is clearly visible and not minimized

**Fix 3**: Try reducing window size (2x instead of 3x)

### Issue: Training not improving

1. **Better starting point**: Save state in tall grass with low-level Pokemon nearby
2. **More steps**: Train for 50,000+ steps
3. **Check rewards**: Add debug prints to see if rewards are being given
4. **Reduce exploration**: Lower `ent_coef` in `PokemonAgent._setup_model()`

### Issue: pyautogui "failsafe triggered"

```python
# Add to start of your script:
import pyautogui
pyautogui.FAILSAFE = False
```

### Issue: Ollama not found / won't start

```powershell
# Check if service is running
Get-Service -Name "Ollama*"

# If not, start manually
ollama serve

# Or reinstall from https://ollama.com/download/windows
```

---

## 9. Performance Benchmarks (Your System)

Expected performance with Ryzen 7800X3D + 7900 XTX:

| Task | Time | Notes |
|------|------|-------|
| Vision classification (llava:7b) | ~0.5-1s | Per frame |
| Vision classification (llava:13b) | ~1-2s | Better accuracy |
| One training step | ~1-2s | Including game delay |
| 10,000 training steps | ~3-5 hours | With fast-forward |
| 50,000 training steps | ~15-25 hours | Overnight run |

### Recommended Settings for Your Hardware

```python
# In pokemon_agent.py, optimize for your GPU:

class PokemonAgent:
    def __init__(self):
        # Use the bigger model - you have the VRAM
        self.classifier = PokemonClassifier(model="llava:13b")
        
class PokemonEnv:
    def __init__(self):
        # Faster step delay since GPU inference is fast
        self.step_delay = 0.2  # Down from 0.3
```

---

## Appendix A: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                 POKEMON AGENT QUICK REFERENCE               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STARTUP:                                                   │
│    cd C:\Projects\pokemon-agent                             │
│    .\venv\Scripts\Activate.ps1                              │
│                                                             │
│  COMMANDS:                                                  │
│    python pokemon_agent.py demo      # Test vision          │
│    python pokemon_agent.py train     # Train agent          │
│    python pokemon_agent.py play      # Watch it play        │
│    python test_input.py mgba         # Test keys            │
│                                                             │
│  mGBA HOTKEYS:                                              │
│    Tab        = Fast forward                                │
│    Shift+F1   = Save state                                  │
│    F1         = Load state                                  │
│                                                             │
│  GPU CHECK:                                                 │
│    Task Manager → Performance → GPU 1 (7900 XTX)            │
│                                                             │
│  ENVIRONMENT VARIABLE (if GPU not detected):                │
│    $env:ROCR_VISIBLE_DEVICES = "1"                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Appendix B: Complete Requirements

`requirements.txt`:

```
mss>=9.0.0
pyautogui>=0.9.54
numpy>=1.24.0
pillow>=10.0.0
requests>=2.31.0
gymnasium>=0.29.0
stable-baselines3>=2.2.0
```

---

## Appendix C: Directory Structure

```
C:\Projects\pokemon-agent\
├── venv\                    # Python virtual environment
│   ├── Scripts\
│   │   └── Activate.ps1     # Activation script
│   └── Lib\
├── models\                  # Saved RL models (created during training)
│   └── pokemon_agent.zip
├── vision_classifier.py     # Generic vision module
├── rl_agent.py             # Generic RL module
├── pokemon_agent.py        # Pokemon-specific agent
├── main.py                 # Generic CLI
├── test_input.py           # Input testing utility
├── requirements.txt        # Python dependencies
├── README.md               # Project overview
├── POKEMON_QUICKSTART.md   # Quick start guide
└── SETUP_PLAN.md          # This document
```

---

## Appendix D: Your System Configuration Summary

| Component | Value | Status |
|-----------|-------|--------|
| OS | Windows 11 | ✓ Supported |
| CPU | Ryzen 7800X3D | ✓ Excellent |
| iGPU | Radeon Graphics (gfx1036) | ⚠️ Must disable for Ollama |
| dGPU | 7900 XTX (gfx1100) | ✓ Officially supported |
| VRAM | 24 GB | ✓ Can run llava:34b |
| RAM | 32 GB | ✓ More than enough |
| Storage | 4TB SSD | ✓ Fast model loading |
| Network | 1Gb | ✓ Fast model downloads |

**Key Configuration**: Set `ROCR_VISIBLE_DEVICES=1` to use 7900 XTX

---

## Summary Checklist

### One-Time Setup
- [ ] AMD Adrenalin drivers installed (latest)
- [ ] Python 3.11+ installed and in PATH
- [ ] Project folder created: `C:\Projects\pokemon-agent`
- [ ] Virtual environment created and working
- [ ] All pip packages installed
- [ ] Ollama installed
- [ ] `ROCR_VISIBLE_DEVICES` environment variable set
- [ ] llava:7b (or 13b) model downloaded
- [ ] mGBA emulator installed
- [ ] Pokemon ROM available

### Before Each Session
- [ ] Ollama service running (auto-starts with Windows)
- [ ] Virtual environment activated
- [ ] mGBA open with ROM loaded
- [ ] Save state created near wild Pokemon
- [ ] mGBA window fully visible (not overlapped)

### Verification
- [ ] Test 1: Python imports work
- [ ] Test 2: Ollama responds
- [ ] Test 3: GPU being used (not CPU)
- [ ] Test 4: Screen capture works
- [ ] Test 5: Vision model fast (<2s with GPU)
- [ ] Test 6: Key presses register in mGBA
- [ ] Test 7: Vision classifier detects game state

### Ready to Train!
- [ ] All checks passed
- [ ] `python pokemon_agent.py train --steps 20000`

---

*Document Version: 2.0 (Windows + AMD 7900 XTX)*
*Last Updated: 2025-02-01*
