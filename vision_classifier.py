"""
Vision Classifier Module

Generic screen-to-state classification using local vision-language models (VLMs).
Uses Ollama API with LLaVA or similar multimodal models.
"""

import base64
import json
import re
import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Optional

import mss
import requests
from PIL import Image


@dataclass
class GameState:
    """Generic game state extracted from screen."""
    scene_type: str = "unknown"
    raw_response: str = ""
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    extra: dict = field(default_factory=dict)


class VisionClassifier:
    """
    Generic vision classifier that captures screen and queries a local VLM.

    Attributes:
        model: Name of the Ollama model to use (e.g., 'llava:7b', 'llava:13b')
        ollama_url: URL of the Ollama API endpoint
        capture_region: Optional tuple (left, top, width, height) to capture specific region
    """

    def __init__(
        self,
        model: str = "llava:7b",
        ollama_url: str = "http://localhost:11434",
        capture_region: Optional[tuple[int, int, int, int]] = None,
        monitor_index: int = 1,
    ):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.capture_region = capture_region
        self.monitor_index = monitor_index
        self._sct = mss.mss()

    def capture_screen(self) -> Image.Image:
        """Capture the screen or specified region."""
        if self.capture_region:
            left, top, width, height = self.capture_region
            region = {"left": left, "top": top, "width": width, "height": height}
            screenshot = self._sct.grab(region)
        else:
            screenshot = self._sct.grab(self._sct.monitors[self.monitor_index])

        # Convert to PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img

    def image_to_base64(self, img: Image.Image, max_size: int = 512) -> str:
        """Convert PIL Image to base64 string, resizing if needed."""
        # Resize to reduce token usage
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def query_vlm(
        self,
        image: Image.Image,
        prompt: str,
        timeout: float = 60.0,
    ) -> str:
        """
        Send image and prompt to local VLM via Ollama API.

        Args:
            image: PIL Image to analyze
            prompt: Text prompt describing what to extract
            timeout: Request timeout in seconds

        Returns:
            Raw text response from the model
        """
        img_b64 = self.image_to_base64(image)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
        }

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.RequestException as e:
            print(f"VLM query error: {e}")
            return ""

    def classify(self, prompt: str) -> GameState:
        """
        Capture screen and classify the current game state.

        Args:
            prompt: Prompt describing what information to extract

        Returns:
            GameState with extracted information
        """
        img = self.capture_screen()
        start_time = time.time()
        response = self.query_vlm(img, prompt)
        elapsed = time.time() - start_time

        return GameState(
            raw_response=response,
            confidence=1.0 if response else 0.0,
            timestamp=start_time,
            extra={"inference_time": elapsed},
        )

    def classify_with_image(
        self,
        image: Image.Image,
        prompt: str,
    ) -> GameState:
        """
        Classify a provided image instead of capturing screen.

        Args:
            image: PIL Image to analyze
            prompt: Prompt describing what information to extract

        Returns:
            GameState with extracted information
        """
        start_time = time.time()
        response = self.query_vlm(image, prompt)
        elapsed = time.time() - start_time

        return GameState(
            raw_response=response,
            confidence=1.0 if response else 0.0,
            timestamp=start_time,
            extra={"inference_time": elapsed},
        )

    def check_ollama_status(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()

            # Check if model is available
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check for exact match or partial match (e.g., "llava:7b" in "llava:7b-v1.6")
            model_base = self.model.split(":")[0]
            return any(model_base in name for name in model_names)
        except requests.exceptions.RequestException:
            return False

    def __del__(self):
        """Cleanup screen capture resources."""
        if hasattr(self, "_sct"):
            self._sct.close()


def parse_json_from_response(response: str) -> dict:
    """
    Extract JSON object from VLM response text.

    The VLM may include extra text around the JSON, so we try to find
    and parse just the JSON portion.
    """
    # Try to find JSON in the response
    json_patterns = [
        r"\{[^{}]*\}",  # Simple JSON object
        r"\{.*?\}",     # Greedy JSON object
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    return {}


def extract_number(text: str, default: int = 0) -> int:
    """Extract first number from text."""
    match = re.search(r"\d+", str(text))
    return int(match.group()) if match else default


def extract_boolean(text: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in text (case-insensitive)."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


if __name__ == "__main__":
    # Quick test
    print("Testing Vision Classifier...")

    classifier = VisionClassifier(model="llava:7b")

    # Check Ollama status
    if classifier.check_ollama_status():
        print("✓ Ollama is running and model is available")
    else:
        print("✗ Ollama not running or model not found")
        print("  Run: ollama pull llava:7b")
        exit(1)

    # Test screen capture
    img = classifier.capture_screen()
    print(f"✓ Screen captured: {img.size}")

    # Test classification
    print("Testing VLM query (this may take a few seconds)...")
    state = classifier.classify("Describe what you see in this image briefly.")
    print(f"✓ Response received in {state.extra.get('inference_time', 0):.2f}s")
    print(f"  Response: {state.raw_response[:100]}...")
