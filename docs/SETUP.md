# Setup Guide

## Requirements

- **OS**: Linux (Ubuntu 22.04+ recommended) or Windows via WSL2 (Ubuntu 22.04)
- **Node.js**: v18+ with `pnpm`
- **Python**: v3.10+
- **Hardware**:
  - **CPU**: Multi-core processor highly recommended (simulations are CPU intensive)
  - **RAM**: 16GB+
  - **GPU**: Optional but recommended for training speed.
    - **NVIDIA**: Install standard CUDA drivers.
    - **AMD**: Supported via PyTorch ROCm. 
    - **Apple**: Supported via MPS (Metal Performance Shaders) on M1/M2/M3 chips.

## AMD GPU Setup (ROCm)

Modern AMD GPUs (e.g., RX 7900 XTX) are supported for training using PyTorch's ROCm backend. Stable Baselines3 runs on top of PyTorch and works seamlessly with ROCm.

### Option 1: WSL2 (Recommended)
1. Ensure you have the latest drivers installed on Windows.
2. In your WSL2 terminal, set the necessary environment variables for your GPU architecture:
   ```bash
   # For RDNA 3 (e.g., 7900 XTX)
   export HSA_OVERRIDE_GFX_VERSION=11.0.0 
   
   # For stability in WSL2
   export HSA_ENABLE_SDMA=0 
   ```
3. Install PyTorch with ROCm support:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0
   ```
4. In the app configuration, select **CUDA / ROCm** as the Compute Device. Since ROCm uses the HIP translation layer, it accepts `cuda` device calls transparently.

### Option 2: Docker
Use the official ROCm PyTorch Docker image:
```bash
docker run -it --ipc=host --network=host \
  --device=/dev/kfd --device=/dev/dri \
  --group-add video --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  rocm/pytorch:rocm6.0_ubuntu22.04_py3.10_pytorch_2.1.2 /bin/bash
```

## Running the App

1. **Install dependencies**:
   ```bash
   pnpm install
   ```
   
2. **Setup Python environment**:
   ```bash
   cd apps/api
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Start Development Servers**:
   ```bash
   # Terminal 1 (Frontend)
   pnpm dev:web

   # Terminal 2 (Backend)
   pnpm dev:api
   ```
