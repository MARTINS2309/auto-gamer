"""
AI Screenshot Reviewer - Analyzes screenshots to provide feedback on decisions.

Uses a vision model (e.g., Claude, GPT-4V, or local model) to review
screenshots and provide AI feedback scores for the genome.

This enables the AI to assess:
- Was the action appropriate for the screen state?
- Is the agent making progress?
- Are there obvious improvements?
"""

import base64
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class AIFeedback:
    """Feedback from AI review of a screenshot."""
    strategy_score: float = 0.0  # -1 to 1: Was the strategy good?
    efficiency_score: float = 0.0  # -1 to 1: Was it efficient?
    exploration_score: float = 0.0  # -1 to 1: Good exploration?
    battle_score: float = 0.0  # -1 to 1: Battle handling?
    notes: str = ""  # Free-form observations
    suggested_action: str = ""  # What AI thinks should have been done
    confidence: float = 0.0  # How confident the AI is


class AIReviewer:
    """Reviews screenshots using AI vision model."""

    # Valid actions the AI can suggest (constrained set)
    VALID_ACTIONS = ['a', 'b', 'up', 'down', 'left', 'right', 'start', 'select', 'l', 'r']

    # Valid scenes
    VALID_SCENES = ['battle', 'overworld', 'dialogue', 'menu', 'title', 'unknown']

    def __init__(self, api_key: str = None, model: str = "local", model_path: str = None):
        """
        Initialize AI reviewer.

        Args:
            api_key: API key for cloud models (claude, gpt4v)
            model: Which model to use ('claude', 'gpt4v', 'local', 'ollama')
            model_path: Path to local model (for 'local' mode)
        """
        self.api_key = api_key
        self.model = model
        self.model_path = model_path
        self.enabled = api_key is not None or model in ('local', 'ollama')

        # System prompt that constrains AI behavior
        self.system_prompt = """You are a Pokemon game screenshot analyzer. Your ONLY purpose is to:

1. Analyze Pokemon FireRed/LeafGreen screenshots
2. Provide numerical scores for the bot's decisions
3. Suggest one action from this EXACT list: a, b, up, down, left, right, start, select

CONSTRAINTS - You MUST follow these rules:
- ONLY output JSON in the exact format specified
- ONLY suggest actions from the valid action list
- ONLY provide scores between -1.0 and 1.0
- DO NOT generate any code, scripts, or commands
- DO NOT suggest any actions outside the game
- DO NOT provide any information unrelated to this screenshot
- DO NOT refuse to analyze - always provide scores

You are analyzing a GBA Pokemon game. Focus on:
- Is the player making progress?
- Is the action appropriate for the screen state?
- Would a different button press be more efficient?

If you cannot determine something, use 0.0 (neutral score)."""

        # Prompt for the AI (user message)
        self.review_prompt = """ACTION TAKEN: {action}
SCENE: {scene}
POSITION: ({x}, {y}) on Map {map}
IN BATTLE: {battle}
PLAYER HP: {player_hp}
ENEMY HP: {enemy_hp}

Rate this decision. Output ONLY this JSON (no other text):
{{"strategy": <-1 to 1>, "efficiency": <-1 to 1>, "exploration": <-1 to 1>, "battle": <-1 to 1>, "suggested_action": "<a|b|up|down|left|right|start|select>", "notes": "<10 words max>", "confidence": <0 to 1>}}"""

    def review_screenshot(self, screenshot_path: str, action: str, scene: str,
                          game_state: Dict = None) -> Optional[AIFeedback]:
        """
        Review a screenshot and provide feedback.

        Args:
            screenshot_path: Path to the screenshot file
            action: The action that was taken
            scene: The detected scene type
            game_state: Dictionary with game state info

        Returns:
            AIFeedback with scores, or None if review failed
        """
        if not self.enabled:
            return None

        path = Path(screenshot_path)
        if not path.exists():
            return None

        # Build prompt with game state
        state = game_state or {}
        prompt = self.review_prompt.format(
            action=action,
            scene=scene,
            x=state.get('x', 0),
            y=state.get('y', 0),
            map=state.get('map_num', 0),
            battle=state.get('battle', False),
            player_hp=state.get('player_hp', 0),
            enemy_hp=state.get('enemy_hp', 0),
        )

        try:
            if self.model == "claude":
                feedback = self._review_with_claude(path, prompt)
            elif self.model == "gpt4v":
                feedback = self._review_with_gpt4v(path, prompt)
            elif self.model == "ollama":
                feedback = self._review_with_ollama(path, prompt)
            else:
                feedback = self._review_local(path, prompt)

            # Validate before returning
            if feedback and self.validate_feedback(feedback):
                return feedback
            return None
        except Exception as e:
            print(f"AI review failed: {e}")
            return None

    def _review_with_claude(self, image_path: Path, prompt: str) -> Optional[AIFeedback]:
        """Review using Claude API."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            # Determine media type
            suffix = image_path.suffix.lower()
            media_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(suffix, "image/png")

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )

            # Parse response
            response_text = message.content[0].text
            return self._parse_response(response_text)

        except ImportError:
            print("anthropic package not installed")
            return None
        except Exception as e:
            print(f"Claude API error: {e}")
            return None

    def _review_with_gpt4v(self, image_path: Path, prompt: str) -> Optional[AIFeedback]:
        """Review using GPT-4V API."""
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)

            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )

            response_text = response.choices[0].message.content
            return self._parse_response(response_text)

        except ImportError:
            print("openai package not installed")
            return None
        except Exception as e:
            print(f"GPT-4V API error: {e}")
            return None

    def _review_local(self, image_path: Path, prompt: str) -> Optional[AIFeedback]:
        """Review using local model via Ollama or direct inference."""
        # Try Ollama first (most common local setup)
        try:
            return self._review_with_ollama(image_path, prompt)
        except Exception as e:
            print(f"Ollama failed: {e}")

        # Fallback: try transformers with local model
        try:
            return self._review_with_transformers(image_path, prompt)
        except Exception as e:
            print(f"Transformers failed: {e}")

        return None

    def _review_with_ollama(self, image_path: Path, prompt: str) -> Optional[AIFeedback]:
        """Review using Ollama with a vision model (e.g., llava, bakllava)."""
        import requests

        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        # Ollama API call with vision model
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model_path or "llava",  # Use llava by default
                    "prompt": prompt,
                    "images": [image_data],
                    "system": self.system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temp for consistent output
                        "num_predict": 200,  # Limit output length
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "")
            return self._parse_response(response_text)
        except requests.exceptions.ConnectionError:
            print("Ollama not running. Start with: ollama serve")
            return None

    def _review_with_transformers(self, image_path: Path, prompt: str) -> Optional[AIFeedback]:
        """Review using HuggingFace transformers with a local vision model."""
        try:
            from transformers import AutoProcessor, LlavaForConditionalGeneration
            from PIL import Image
            import torch

            # Load model (cached after first load)
            model_id = self.model_path or "llava-hf/llava-1.5-7b-hf"

            if not hasattr(self, '_local_model'):
                print(f"Loading local model: {model_id}")
                self._local_processor = AutoProcessor.from_pretrained(model_id)
                self._local_model = LlavaForConditionalGeneration.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16,
                    device_map="auto"
                )

            # Load image
            image = Image.open(image_path)

            # Create conversation
            conversation = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt}
                ]}
            ]

            # Process
            text = self._local_processor.apply_chat_template(conversation, add_generation_prompt=True)
            inputs = self._local_processor(text, image, return_tensors="pt").to(self._local_model.device)

            # Generate
            output = self._local_model.generate(**inputs, max_new_tokens=200, do_sample=False)
            response_text = self._local_processor.decode(output[0], skip_special_tokens=True)

            return self._parse_response(response_text)

        except ImportError:
            print("transformers package not installed")
            return None
        except Exception as e:
            print(f"Transformers inference error: {e}")
            return None

    def _parse_response(self, response_text: str) -> Optional[AIFeedback]:
        """Parse AI response JSON into AIFeedback with validation."""
        try:
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start == -1 or end == 0:
                return None

            data = json.loads(response_text[start:end])

            # Validate and sanitize suggested action
            suggested = str(data.get('suggested_action', '')).lower().strip()
            if suggested not in self.VALID_ACTIONS:
                suggested = 'a'  # Default to safe action

            # Sanitize notes (limit length, remove any code-like content)
            notes = str(data.get('notes', ''))[:100]
            # Remove anything that looks like code
            if any(c in notes for c in ['<', '>', '{', '}', '()', '[]', 'import', 'def ', 'class ']):
                notes = "analysis complete"

            return AIFeedback(
                strategy_score=max(-1, min(1, float(data.get('strategy', 0)))),
                efficiency_score=max(-1, min(1, float(data.get('efficiency', 0)))),
                exploration_score=max(-1, min(1, float(data.get('exploration', 0)))),
                battle_score=max(-1, min(1, float(data.get('battle', 0)))),
                notes=notes,
                suggested_action=suggested,
                confidence=max(0, min(1, float(data.get('confidence', 0.5)))),
            )
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse AI response: {e}")
            return None

    def validate_feedback(self, feedback: AIFeedback) -> bool:
        """Validate that feedback is within allowed bounds."""
        if not feedback:
            return False

        # Check scores are in valid range
        scores = [
            feedback.strategy_score,
            feedback.efficiency_score,
            feedback.exploration_score,
            feedback.battle_score,
            feedback.confidence
        ]
        for score in scores:
            if not isinstance(score, (int, float)) or score < -1 or score > 1:
                return False

        # Check suggested action is valid
        if feedback.suggested_action not in self.VALID_ACTIONS:
            return False

        return True

    def review_run(self, screenshot_dir: str, sample_size: int = 10) -> Optional[AIFeedback]:
        """
        Review a completed run by sampling screenshots.

        Args:
            screenshot_dir: Directory containing run screenshots
            sample_size: Number of screenshots to review

        Returns:
            Aggregated AIFeedback for the run
        """
        if not self.enabled:
            return None

        path = Path(screenshot_dir)
        if not path.exists():
            return None

        # Find all screenshots
        screenshots = list(path.glob("*.png"))
        if not screenshots:
            return None

        # Sample evenly across the run
        step = max(1, len(screenshots) // sample_size)
        samples = screenshots[::step][:sample_size]

        # Aggregate feedback
        feedbacks = []
        for screenshot in samples:
            # Load metadata
            meta_path = screenshot.with_suffix('.json')
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                feedback = self.review_screenshot(
                    str(screenshot),
                    meta.get('action', ''),
                    meta.get('scene', ''),
                    meta
                )
                if feedback:
                    feedbacks.append(feedback)

        if not feedbacks:
            return None

        # Average the scores
        return AIFeedback(
            strategy_score=sum(f.strategy_score for f in feedbacks) / len(feedbacks),
            efficiency_score=sum(f.efficiency_score for f in feedbacks) / len(feedbacks),
            exploration_score=sum(f.exploration_score for f in feedbacks) / len(feedbacks),
            battle_score=sum(f.battle_score for f in feedbacks) / len(feedbacks),
            notes=f"Reviewed {len(feedbacks)} screenshots",
            confidence=sum(f.confidence for f in feedbacks) / len(feedbacks),
        )
