"""
Vision Model Benchmark - Drag Race

Compares multiple Ollama vision models for Pokemon game screen analysis.
Tests inference speed, response quality, and consistency.

Improvements:
- Standard deviation for latency consistency
- Tokens per second estimation
- Quality scoring based on JSON completeness
- Side-by-side response comparison
- Exportable results to JSON
- Support for pre-captured test images
"""

import base64
import json
import re
import statistics
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import mss
import requests
from PIL import Image


@dataclass
class BenchmarkResult:
    """Result from a single model benchmark run."""
    model: str
    inference_time: float
    response: str
    parsed_json: dict
    success: bool
    error: str = ""
    response_length: int = 0
    tokens_estimated: int = 0


@dataclass
class ModelSummary:
    """Aggregated results for a model."""
    model: str
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    success_rate: float
    json_parse_rate: float
    avg_response_length: float
    tokens_per_second: float
    quality_score: float
    sample_response: str
    sample_json: dict


POKEMON_PROMPT = """Analyze this Pokemon game screenshot and respond with ONLY a JSON object containing:
{
    "scene_type": "overworld" or "battle" or "menu" or "dialogue" or "title",
    "in_battle": true/false,
    "player_hp_percent": 0-100 (estimate from HP bar if in battle, null if not visible),
    "enemy_hp_percent": 0-100 (estimate from HP bar if in battle, null if not visible),
    "has_dialogue": true/false (text box visible),
    "menu_open": true/false,
    "player_pokemon": "name if visible, null otherwise",
    "enemy_pokemon": "name if visible, null otherwise",
    "location_hint": "brief description of setting if recognizable"
}

Be precise. Only output the JSON object, no other text."""

REQUIRED_FIELDS = ["scene_type", "in_battle", "has_dialogue", "menu_open"]
OPTIONAL_FIELDS = ["player_hp_percent", "enemy_hp_percent", "player_pokemon", "enemy_pokemon", "location_hint"]

MODELS_TO_TEST = [
    "qwen2.5vl:7b",
    "qwen2.5vl:3b",
    "minicpm-v",
    "llama3.2-vision:11b",
]

OLLAMA_URL = "http://localhost:11434"


def capture_screen(monitor_index: int = 1) -> Image.Image:
    """Capture the current screen."""
    with mss.mss() as sct:
        screenshot = sct.grab(sct.monitors[monitor_index])
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img


def load_image(path: str) -> Image.Image:
    """Load an image from file."""
    return Image.open(path).convert("RGB")


def image_to_base64(img: Image.Image, max_size: int = 512) -> str:
    """Convert PIL Image to base64 string, resizing if needed."""
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def parse_json_from_response(response: str) -> dict:
    """Extract JSON object from VLM response text."""
    # Try to find JSON block
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: try parsing the whole thing
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    return {}


def estimate_tokens(text: str) -> int:
    """Rough token count estimation (4 chars per token average)."""
    return len(text) // 4


def calculate_quality_score(parsed_json: dict) -> float:
    """Score JSON output completeness and quality (0-100)."""
    if not parsed_json:
        return 0.0

    score = 0.0

    # Required fields (60 points)
    for field in REQUIRED_FIELDS:
        if field in parsed_json and parsed_json[field] is not None:
            score += 15

    # Optional fields (40 points)
    for field in OPTIONAL_FIELDS:
        if field in parsed_json:
            score += 8

    return min(100.0, score)


def check_model_available(model: str) -> bool:
    """Check if a model is available in Ollama."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        model_names = [m.get("name", "") for m in models]
        return any(model in name or name.startswith(model.split(":")[0]) for name in model_names)
    except:
        return False


def benchmark_model(model: str, img_b64: str) -> BenchmarkResult:
    """Run a single benchmark on a model."""
    payload = {
        "model": model,
        "prompt": POKEMON_PROMPT,
        "images": [img_b64],
        "stream": False,
    }

    try:
        start_time = time.perf_counter()
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        elapsed = time.perf_counter() - start_time

        response_text = response.json().get("response", "")
        parsed = parse_json_from_response(response_text)
        tokens = estimate_tokens(response_text)

        return BenchmarkResult(
            model=model,
            inference_time=elapsed,
            response=response_text,
            parsed_json=parsed,
            success=bool(parsed),
            response_length=len(response_text),
            tokens_estimated=tokens,
        )
    except Exception as e:
        return BenchmarkResult(
            model=model,
            inference_time=0,
            response="",
            parsed_json={},
            success=False,
            error=str(e),
        )


def run_benchmark(
    n_runs: int = 3,
    save_screenshot: bool = True,
    image_path: Optional[str] = None,
    export_json: bool = True,
) -> list[ModelSummary]:
    """Run the full benchmark comparing all models."""

    print("=" * 80)
    print("    VISION MODEL DRAG RACE - Pokemon Screen Analysis Benchmark")
    print("=" * 80)
    print(f"\n  Runs per model: {n_runs}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check which models are available
    print("\n" + "-" * 80)
    print("CHECKING AVAILABLE MODELS")
    print("-" * 80)

    available_models = []
    for model in MODELS_TO_TEST:
        if check_model_available(model):
            print(f"  [OK] {model}")
            available_models.append(model)
        else:
            print(f"  [--] {model} (not installed)")

    if not available_models:
        print("\nNo vision models available! Install with:")
        for model in MODELS_TO_TEST:
            print(f"  ollama pull {model}")
        return []

    # Get or capture image
    if image_path and Path(image_path).exists():
        print(f"\nLoading test image: {image_path}")
        img = load_image(image_path)
    else:
        print(f"\nCapturing screen in 5 seconds...")
        print("Make sure the Pokemon game is visible!")
        for i in range(5, 0, -1):
            print(f"  {i}...")
            time.sleep(1)
        img = capture_screen()

    img_b64 = image_to_base64(img)
    print(f"Image size: {img.size}")

    if save_screenshot:
        screenshot_path = Path("benchmark_screenshot.png")
        img.save(screenshot_path)
        print(f"Saved to: {screenshot_path}")

    # Warmup each model
    print("\n" + "-" * 80)
    print("WARMUP ROUND (first inference is always slower due to model loading)")
    print("-" * 80)

    for model in available_models:
        print(f"\n  Warming up {model}...", end=" ", flush=True)
        result = benchmark_model(model, img_b64)
        if result.success:
            print(f"OK ({result.inference_time:.2f}s)")
        else:
            print(f"Failed: {result.error[:50]}")

    # Run actual benchmarks
    print("\n" + "=" * 80)
    print(f"BENCHMARK: {n_runs} runs per model")
    print("=" * 80)

    results: dict[str, list[BenchmarkResult]] = {m: [] for m in available_models}

    for run in range(n_runs):
        print(f"\n--- Run {run + 1}/{n_runs} ---")
        for model in available_models:
            print(f"  {model:<25}", end=" ", flush=True)
            result = benchmark_model(model, img_b64)
            results[model].append(result)

            if result.success:
                quality = calculate_quality_score(result.parsed_json)
                print(f"{result.inference_time:>6.2f}s | {result.tokens_estimated:>4} tok | Q:{quality:>5.1f}")
            else:
                print(f"FAILED: {result.error[:40]}")

    # Calculate summaries
    summaries: list[ModelSummary] = []

    for model in available_models:
        model_results = results[model]
        successful = [r for r in model_results if r.success]

        if successful:
            times = [r.inference_time for r in successful]
            avg_time = statistics.mean(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0.0

            quality_scores = [calculate_quality_score(r.parsed_json) for r in successful]
            avg_quality = statistics.mean(quality_scores)

            avg_tokens = statistics.mean([r.tokens_estimated for r in successful])
            tps = avg_tokens / avg_time if avg_time > 0 else 0

            summaries.append(ModelSummary(
                model=model,
                avg_time=avg_time,
                min_time=min(times),
                max_time=max(times),
                std_dev=std_dev,
                success_rate=len(successful) / len(model_results) * 100,
                json_parse_rate=sum(1 for r in successful if r.parsed_json) / len(successful) * 100,
                avg_response_length=statistics.mean([r.response_length for r in successful]),
                tokens_per_second=tps,
                quality_score=avg_quality,
                sample_response=successful[0].response[:500] if successful else "",
                sample_json=successful[0].parsed_json if successful else {},
            ))

    # Sort by a composite score (speed + quality)
    # Lower time is better, higher quality is better
    def composite_score(s: ModelSummary) -> float:
        # Normalize: time penalty (0-100 based on 0-10s range), quality bonus (0-100)
        time_score = max(0, 100 - s.avg_time * 10)  # 10s = 0, 0s = 100
        return time_score * 0.4 + s.quality_score * 0.6

    summaries.sort(key=composite_score, reverse=True)

    # Print results
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    print(f"\n{'Rank':<5} {'Model':<22} {'Avg Time':<10} {'Std Dev':<9} {'TPS':<8} {'Quality':<8} {'Success':<8}")
    print("-" * 80)

    for i, s in enumerate(summaries):
        rank = ["1st", "2nd", "3rd", "4th", "5th"][i] if i < 5 else f"{i+1}th"
        print(f"{rank:<5} {s.model:<22} {s.avg_time:>6.2f}s   {s.std_dev:>6.3f}s  "
              f"{s.tokens_per_second:>6.1f}  {s.quality_score:>6.1f}  {s.success_rate:>5.0f}%")

    # Detailed timing breakdown
    print("\n" + "-" * 80)
    print("TIMING BREAKDOWN")
    print("-" * 80)
    print(f"\n{'Model':<22} {'Min':<10} {'Avg':<10} {'Max':<10} {'Consistency':<12}")

    for s in summaries:
        consistency = "Excellent" if s.std_dev < 0.5 else "Good" if s.std_dev < 1.0 else "Variable"
        print(f"{s.model:<22} {s.min_time:>6.2f}s   {s.avg_time:>6.2f}s   {s.max_time:>6.2f}s   {consistency}")

    # Sample outputs comparison
    print("\n" + "=" * 80)
    print("SAMPLE OUTPUTS COMPARISON")
    print("=" * 80)

    for s in summaries:
        print(f"\n--- {s.model} (Quality: {s.quality_score:.1f}/100) ---")
        if s.sample_json:
            print(json.dumps(s.sample_json, indent=2))
        else:
            print(f"Raw: {s.sample_response[:200]}...")

    # Final recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    if summaries:
        fastest = min(summaries, key=lambda x: x.avg_time)
        most_consistent = min(summaries, key=lambda x: x.std_dev)
        best_quality = max(summaries, key=lambda x: x.quality_score)
        best_overall = summaries[0]  # Already sorted by composite

        print(f"\n  Fastest:         {fastest.model} ({fastest.avg_time:.2f}s avg)")
        print(f"  Most Consistent: {most_consistent.model} (std dev: {most_consistent.std_dev:.3f}s)")
        print(f"  Best Quality:    {best_quality.model} (score: {best_quality.quality_score:.1f}/100)")
        print(f"\n  >>> OVERALL WINNER: {best_overall.model}")
        print(f"      Speed: {best_overall.avg_time:.2f}s | Quality: {best_overall.quality_score:.1f}")

    # Export results
    if export_json:
        export_path = Path("benchmark_results.json")
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "runs_per_model": n_runs,
            "models_tested": available_models,
            "results": [asdict(s) for s in summaries],
        }
        with open(export_path, "w") as f:
            json.dump(export_data, f, indent=2)
        print(f"\n  Results exported to: {export_path}")

    print("\n" + "=" * 80)

    return summaries


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark vision models for Pokemon")
    parser.add_argument("--runs", type=int, default=3, help="Number of benchmark runs per model")
    parser.add_argument("--no-save", action="store_true", help="Don't save screenshot")
    parser.add_argument("--image", type=str, help="Use pre-captured image instead of live capture")
    parser.add_argument("--no-export", action="store_true", help="Don't export results to JSON")
    args = parser.parse_args()

    run_benchmark(
        n_runs=args.runs,
        save_screenshot=not args.no_save,
        image_path=args.image,
        export_json=not args.no_export,
    )
