import contextvars
from dataclasses import dataclass, field

from app.config import settings


@dataclass
class AIUsageStats:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_calls: dict[str, int] = field(default_factory=dict)

    def record(self, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        self.prompt_tokens += max(0, int(prompt_tokens or 0))
        self.completion_tokens += max(0, int(completion_tokens or 0))
        self.total_tokens += max(0, int(total_tokens or 0))
        key = model or "unknown"
        self.model_calls[key] = self.model_calls.get(key, 0) + 1

    def estimate_cost_usd(self) -> float:
        input_rate = settings.AI_COST_INPUT_PER_1M_TOKENS
        output_rate = settings.AI_COST_OUTPUT_PER_1M_TOKENS
        return (
            (self.prompt_tokens / 1_000_000) * input_rate
            + (self.completion_tokens / 1_000_000) * output_rate
        )


_usage_var: contextvars.ContextVar[AIUsageStats | None] = contextvars.ContextVar(
    "ai_usage_stats", default=None
)


def start_ai_usage_tracking() -> None:
    _usage_var.set(AIUsageStats())


def get_ai_usage_stats() -> AIUsageStats:
    stats = _usage_var.get()
    if stats is None:
        stats = AIUsageStats()
        _usage_var.set(stats)
    return stats


def clear_ai_usage_tracking() -> None:
    _usage_var.set(None)


def record_completion_usage(model: str, usage_obj) -> None:
    if usage_obj is None:
        return

    prompt_tokens = getattr(usage_obj, "prompt_tokens", 0) or getattr(usage_obj, "input_tokens", 0) or 0
    completion_tokens = getattr(usage_obj, "completion_tokens", 0) or getattr(usage_obj, "output_tokens", 0) or 0
    total_tokens = getattr(usage_obj, "total_tokens", 0) or (prompt_tokens + completion_tokens)

    get_ai_usage_stats().record(model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens)
