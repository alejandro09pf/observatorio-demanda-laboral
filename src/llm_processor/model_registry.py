"""
Model Registry - Centralized configuration for all supported LLM models.
Includes download URLs, model specs, and recommended settings.
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Configuration for a single LLM model."""
    name: str
    display_name: str
    repo_id: str  # HuggingFace repo
    filename: str  # GGUF filename
    size_gb: float
    context_length: int
    recommended_gpu_layers: int
    description: str
    quantization: str
    url: str = ""  # Auto-generated

    def __post_init__(self):
        self.url = f"https://huggingface.co/{self.repo_id}/resolve/main/{self.filename}"


# Model Registry - All supported models
MODEL_REGISTRY: Dict[str, ModelConfig] = {
    # Gemma 3 1B Instruct (Google's latest generation)
    "gemma-3-1b-instruct": ModelConfig(
        name="gemma-3-1b-instruct",
        display_name="Gemma 3 1B Instruct",
        repo_id="unsloth/gemma-3-1b-it-GGUF",
        filename="gemma-3-1b-it-Q4_K_M.gguf",
        size_gb=0.7,
        context_length=8192,
        recommended_gpu_layers=18,
        quantization="Q4_K_M",
        description="Google's Gemma 3 1B. Smallest and fastest model, latest generation."
    ),

    # Gemma 3 4B Instruct (Google's latest generation)
    "gemma-3-4b-instruct": ModelConfig(
        name="gemma-3-4b-instruct",
        display_name="Gemma 3 4B Instruct",
        repo_id="unsloth/gemma-3-4b-it-GGUF",
        filename="gemma-3-4b-it-Q4_K_M.gguf",
        size_gb=2.8,
        context_length=8192,
        recommended_gpu_layers=32,
        quantization="Q4_K_M",
        description="Google's Gemma 3 4B. Latest generation, good balance of speed and quality."
    ),

    # Llama 3.2 3B Instruct (Meta's latest small model)
    "llama-3.2-3b-instruct": ModelConfig(
        name="llama-3.2-3b-instruct",
        display_name="Llama 3.2 3B Instruct",
        repo_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
        filename="Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        size_gb=2.1,
        context_length=131072,  # 128K context!
        recommended_gpu_layers=28,
        quantization="Q4_K_M",
        description="Meta's Llama 3.2 3B. Excellent multilingual performance, huge context window."
    ),

    # Mistral 7B Instruct v0.3 (Popular baseline)
    "mistral-7b-instruct": ModelConfig(
        name="mistral-7b-instruct",
        display_name="Mistral 7B Instruct v0.3",
        repo_id="bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        filename="Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        size_gb=4.4,
        context_length=32768,
        recommended_gpu_layers=35,
        quantization="Q4_K_M",
        description="Mistral 7B v0.3. Excellent reasoning, good for complex skill normalization."
    ),

    # Qwen 2.5 3B Instruct
    "qwen2.5-3b-instruct": ModelConfig(
        name="qwen2.5-3b-instruct",
        display_name="Qwen 2.5 3B Instruct",
        repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
        filename="qwen2.5-3b-instruct-q4_k_m.gguf",
        size_gb=2.1,
        context_length=32768,
        recommended_gpu_layers=28,
        quantization="Q4_K_M",
        description="Qwen 2.5 3B. Excellent for structured outputs, compact size."
    ),

    # Qwen 2.5 7B Instruct (Best for structured outputs per benchmarks)
    "qwen2.5-7b-instruct": ModelConfig(
        name="qwen2.5-7b-instruct",
        display_name="Qwen 2.5 7B Instruct",
        repo_id="bartowski/Qwen2.5-7B-Instruct-GGUF",
        filename="Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        size_gb=4.68,
        context_length=32768,
        recommended_gpu_layers=35,
        quantization="Q4_K_M",
        description="Qwen 2.5 7B. #1 ranked for structured outputs and chatbots (2025 benchmarks)."
    ),

    # Qwen3 4B (Latest 2025 release)
    "qwen3-4b": ModelConfig(
        name="qwen3-4b",
        display_name="Qwen3 4B",
        repo_id="unsloth/Qwen3-4B-GGUF",
        filename="Qwen3-4B-Q4_K_M.gguf",
        size_gb=2.5,
        context_length=32768,
        recommended_gpu_layers=32,
        quantization="Q4_K_M",
        description="Qwen3 4B (April 2025). Latest generation, 36T tokens, hybrid reasoning mode."
    ),

    # Qwen3 8B (Latest 2025 release)
    "qwen3-8b": ModelConfig(
        name="qwen3-8b",
        display_name="Qwen3 8B",
        repo_id="unsloth/Qwen3-8B-GGUF",
        filename="Qwen3-8B-Q4_K_M.gguf",
        size_gb=5.03,
        context_length=32768,
        recommended_gpu_layers=40,
        quantization="Q4_K_M",
        description="Qwen3 8B (April 2025). Top-tier, hybrid reasoning, Apache 2.0 license."
    ),

    # Phi-3.5 Mini (Microsoft's efficient small model)
    "phi-3.5-mini": ModelConfig(
        name="phi-3.5-mini",
        display_name="Phi-3.5 Mini (3.8B)",
        repo_id="bartowski/Phi-3.5-mini-instruct-GGUF",
        filename="Phi-3.5-mini-instruct-Q4_K_M.gguf",
        size_gb=2.4,
        context_length=131072,  # 128K context!
        recommended_gpu_layers=32,
        quantization="Q4_K_M",
        description="Microsoft Phi-3.5 Mini. Exceptional instruction following, huge context."
    ),

    # DeepSeek Coder 6.7B (Good for structured data)
    "deepseek-coder-6.7b": ModelConfig(
        name="deepseek-coder-6.7b",
        display_name="DeepSeek Coder 6.7B Instruct",
        repo_id="TheBloke/deepseek-coder-6.7B-instruct-GGUF",
        filename="deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        size_gb=4.0,
        context_length=16384,
        recommended_gpu_layers=34,
        quantization="Q4_K_M",
        description="DeepSeek Coder 6.7B. Excellent reasoning and structured data extraction."
    ),

    # Higher quality quantizations (optional)
    "gemma-2-2.6b-q5": ModelConfig(
        name="gemma-2-2.6b-q5",
        display_name="Gemma 2 2.6B (Q5_K_M)",
        repo_id="bartowski/gemma-2-2b-it-GGUF",
        filename="gemma-2-2b-it-Q5_K_M.gguf",
        size_gb=2.1,
        context_length=8192,
        recommended_gpu_layers=26,
        quantization="Q5_K_M",
        description="Higher quality quantization of Gemma 2 2.6B. Better accuracy, slower inference."
    ),

    "llama-3.2-3b-q5": ModelConfig(
        name="llama-3.2-3b-q5",
        display_name="Llama 3.2 3B (Q5_K_M)",
        repo_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
        filename="Llama-3.2-3B-Instruct-Q5_K_M.gguf",
        size_gb=2.5,
        context_length=131072,
        recommended_gpu_layers=28,
        quantization="Q5_K_M",
        description="Higher quality Llama 3.2 3B. Best accuracy for small models."
    ),

    "mistral-7b-q5": ModelConfig(
        name="mistral-7b-q5",
        display_name="Mistral 7B (Q5_K_M)",
        repo_id="bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        filename="Mistral-7B-Instruct-v0.3-Q5_K_M.gguf",
        size_gb=5.2,
        context_length=32768,
        recommended_gpu_layers=35,
        quantization="Q5_K_M",
        description="Higher quality Mistral 7B. Best overall quality."
    ),
}

# Default models for comparison benchmarks
DEFAULT_COMPARISON_MODELS = [
    "gemma-3-1b-instruct",
    "gemma-3-4b-instruct",
    "llama-3.2-3b-instruct"
]

# Recommended models based on use case
RECOMMENDATIONS = {
    "fastest": "gemma-3-1b-instruct",
    "best_quality": "mistral-7b-q5",
    "best_balance": "llama-3.2-3b-instruct",
    "lowest_memory": "gemma-3-1b-instruct",
    "largest_context": "llama-3.2-3b-instruct",
}


def get_model_config(model_name: str) -> ModelConfig:
    """Get configuration for a specific model."""
    if model_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Model '{model_name}' not found. Available models: {list(MODEL_REGISTRY.keys())}"
        )
    return MODEL_REGISTRY[model_name]


def list_available_models() -> Dict[str, ModelConfig]:
    """List all available models."""
    return MODEL_REGISTRY


def get_recommended_model(criteria: str = "best_balance") -> str:
    """Get recommended model name based on criteria."""
    return RECOMMENDATIONS.get(criteria, "llama-3.2-3b-instruct")
