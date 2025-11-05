"""
LLM Handler - Multi-backend LLM inference with support for llama-cpp-python,
transformers, and OpenAI API.
"""

from typing import Dict, Any, Optional, Union
import logging
import json
from pathlib import Path

from config.settings import get_settings
from llm_processor.model_registry import get_model_config
from llm_processor.model_downloader import ModelDownloader

logger = logging.getLogger(__name__)


class LLMHandler:
    """Manages interactions with Large Language Models."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        backend: Optional[str] = None,
        auto_download: bool = True
    ):
        """
        Initialize LLM handler.

        Args:
            model_name: Name of model to use (from model_registry)
            backend: Backend to use (llama-cpp, transformers, openai)
            auto_download: Automatically download model if not present
        """
        self.settings = get_settings()
        self.model_name = model_name or self.settings.llm_model_name
        self.backend = backend or self.settings.llm_backend
        self.downloader = ModelDownloader()

        # Download model if needed
        if auto_download and self.backend != "openai":
            if not self.downloader.is_model_downloaded(self.model_name):
                logger.info(f"Model not found, downloading: {self.model_name}")
                self.downloader.download_model(self.model_name)

        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load the appropriate LLM model based on backend."""
        logger.info(f"Loading model: {self.model_name} (backend: {self.backend})")

        if self.backend == "llama-cpp":
            self._load_llama_cpp()
        elif self.backend == "transformers":
            self._load_transformers()
        elif self.backend == "openai":
            self._load_openai()
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

        logger.info(f"✓ Model loaded successfully")

    def _load_llama_cpp(self):
        """Load model using llama-cpp-python."""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. Install with: "
                "pip install llama-cpp-python"
            )

        model_path = self.downloader.get_model_path(self.model_name)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        config = get_model_config(self.model_name)

        # Determine chat format based on model
        # NOTE: Gemma and Phi chat formats not working well in llama-cpp, use raw completion
        chat_format = None
        is_gemma = "gemma" in self.model_name.lower()
        is_phi = "phi" in self.model_name.lower()

        # Set chat format for each model family
        if "llama" in self.model_name.lower():
            chat_format = "llama-3"
        elif "qwen" in self.model_name.lower():
            chat_format = "chatml"  # Qwen uses ChatML format
        elif "mistral" in self.model_name.lower():
            chat_format = "mistral-instruct"  # Mistral-Instruct format
        # NOTE: Phi-3 chat format causes issues, use raw completion instead
        # elif "phi" in self.model_name.lower():
        #     chat_format = "phi-3"

        # Gemma and Phi models need minimal config (extra params cause issues)
        if is_gemma or is_phi:
            self.model = Llama(
                model_path=str(model_path),
                n_ctx=min(self.settings.llm_context_length, config.context_length),
                n_gpu_layers=self.settings.llm_n_gpu_layers,
                verbose=False
            )
        else:
            # Llama and other models use full config
            self.model = Llama(
                model_path=str(model_path),
                n_ctx=min(self.settings.llm_context_length, config.context_length),
                n_gpu_layers=self.settings.llm_n_gpu_layers,
                n_threads=self.settings.llm_n_threads,
                n_batch=self.settings.llm_n_batch,
                use_mmap=self.settings.llm_use_mmap,
                use_mlock=self.settings.llm_use_mlock,
                chat_format=chat_format,
                verbose=False
            )

        # Store if model needs chat API or raw completion
        self.use_chat_api = chat_format is not None
        self.is_phi = is_phi  # Store for use in generation

    def _load_transformers(self):
        """Load model using HuggingFace transformers."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
        except ImportError:
            raise ImportError(
                "transformers not installed. Install with: "
                "pip install transformers torch"
            )

        config = get_model_config(self.model_name)

        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(config.repo_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            config.repo_id,
            torch_dtype=torch.float16 if self.settings.llm_n_gpu_layers > 0 else torch.float32,
            device_map="auto" if self.settings.llm_n_gpu_layers > 0 else None
        )

    def _load_openai(self):
        """Setup OpenAI API client."""
        if not self.settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai not installed. Install with: pip install openai"
            )

        self.model = openai
        self.model_name = self.settings.openai_model

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Generate response from LLM.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            stop: Stop sequences
            json_mode: Force JSON output format

        Returns:
            Dict with 'text', 'tokens_used', 'finish_reason'
        """
        max_tokens = max_tokens or self.settings.llm_max_tokens
        temperature = temperature or self.settings.llm_temperature

        try:
            if self.backend == "llama-cpp":
                return self._generate_llama_cpp(prompt, max_tokens, temperature, stop, json_mode)
            elif self.backend == "transformers":
                return self._generate_transformers(prompt, max_tokens, temperature, stop)
            elif self.backend == "openai":
                return self._generate_openai(prompt, max_tokens, temperature, stop, json_mode)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                "text": "",
                "tokens_used": 0,
                "finish_reason": "error",
                "error": str(e)
            }

    def _generate_llama_cpp(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[list[str]],
        json_mode: bool
    ) -> Dict[str, Any]:
        """Generate using llama-cpp-python (chat API or raw completion)."""

        # Llama models use chat API, Gemma uses raw completion
        if self.use_chat_api:
            # Use chat completion API (Llama models)
            response = self.model.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Eres un experto extractor de habilidades técnicas. Respondes SOLO con JSON válido, sin texto adicional."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=self.settings.llm_top_p,
                top_k=self.settings.llm_top_k,
                repeat_penalty=self.settings.llm_repeat_penalty,
                stop=stop or ["```", "\n\n\n"]
            )
            text = response["choices"][0]["message"]["content"].strip()
        else:
            # Use raw completion API (Gemma and Phi models)
            # NOTE: These models need MINIMAL params - top_p/top_k/repeat_penalty cause issues
            # Different stop sequences for different models
            default_stops = ["\n\n\n", "```"] if self.is_phi else ["}\n", "}\r\n"]

            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or default_stops,
                echo=False
            )
            text = response["choices"][0]["text"].strip()

        return {
            "text": text,
            "tokens_used": response["usage"]["total_tokens"],
            "finish_reason": response["choices"][0]["finish_reason"],
            "model": self.model_name
        }

    def _generate_transformers(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[list[str]]
    ) -> Dict[str, Any]:
        """Generate using HuggingFace transformers."""
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt")
        if self.settings.llm_n_gpu_layers > 0:
            inputs = inputs.to("cuda")

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=self.settings.llm_top_p,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )

        generated_text = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )

        return {
            "text": generated_text.strip(),
            "tokens_used": outputs.shape[1],
            "finish_reason": "stop",
            "model": self.model_name
        }

    def _generate_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[list[str]],
        json_mode: bool
    ) -> Dict[str, Any]:
        """Generate using OpenAI API."""
        response = self.model.ChatCompletion.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
            response_format={"type": "json_object"} if json_mode else None
        )

        return {
            "text": response.choices[0].message.content.strip(),
            "tokens_used": response.usage.total_tokens,
            "finish_reason": response.choices[0].finish_reason,
            "model": self.model_name
        }

    def generate_json(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON response from LLM.

        Returns parsed JSON dict or raises ValueError if invalid JSON.
        """
        response = self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=False  # We handle JSON extraction manually
        )

        try:
            # Extract JSON from response (handle markdown code blocks and extra text)
            text = response["text"].strip()

            # Remove markdown code blocks (both ```json and ``` variants)
            # Handle multiline cases where backticks are on separate lines
            if text.startswith("```json"):
                text = text[7:].lstrip()  # Remove ```json and leading whitespace
            elif text.startswith("```"):
                text = text[3:].lstrip()  # Remove ``` and leading whitespace

            if text.endswith("```"):
                text = text[:-3].rstrip()  # Remove trailing ``` and whitespace

            text = text.strip()

            # Try to find JSON object in the response
            # Look for first { and last }
            start_idx = text.find("{")
            end_idx = text.rfind("}")

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                text = text[start_idx:end_idx+1]
            else:
                # Also try array format
                start_idx = text.find("[")
                end_idx = text.rfind("]")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    # Wrap array in skills object
                    text = f'{{"skills": {text[start_idx:end_idx+1]}}}'

            # Try to parse JSON
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as e:
                # Attempt to auto-fix common truncation issues
                # Case 1: Missing ] before } in format {"skills": ["item1", "item2" }
                if '"skills"' in text and '[' in text and ']' not in text.split('[')[1]:
                    logger.warning(f"Detected incomplete JSON array, attempting to fix...")
                    # Find the last [ and insert ] before the final }
                    last_bracket_idx = text.rfind('[')
                    last_brace_idx = text.rfind('}')
                    if last_bracket_idx != -1 and last_brace_idx != -1:
                        text = text[:last_brace_idx] + ']' + text[last_brace_idx:]
                        logger.debug(f"Fixed JSON: {text[:200]}")
                        parsed = json.loads(text)
                    else:
                        raise e
                else:
                    raise e

            response["parsed_json"] = parsed
            return response
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response text: {response['text'][:500]}")
            response["error"] = f"Invalid JSON: {str(e)}"
            return response

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        config = get_model_config(self.model_name)
        return {
            "model_name": self.model_name,
            "display_name": config.display_name,
            "backend": self.backend,
            "context_length": config.context_length,
            "quantization": config.quantization,
            "size_gb": config.size_gb,
            "gpu_layers": self.settings.llm_n_gpu_layers,
        }

    def unload_model(self):
        """Unload model from memory."""
        if self.model is not None:
            del self.model
            self.model = None
            logger.info("Model unloaded from memory") 