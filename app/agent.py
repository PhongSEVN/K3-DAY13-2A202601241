from __future__ import annotations

import time
from dataclasses import dataclass

from . import metrics
from .logging_config import get_logger
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .prompt_management import resolve_prompt
from .tracing import child_span, get_langfuse_client, observe, tracing_enabled

log = get_logger()


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe(as_type="generation", capture_input=False, capture_output=False)
    def run(self, user_id: str, feature: str, session_id: str, message: str) -> AgentResult:
        started = time.perf_counter()
        langfuse_client = get_langfuse_client()

        # --- Bước 1: RAG (tra cứu tài liệu) ---
        # Đo riêng bước này vì incident "rag_slow" chèn sleep(2.5s) đúng ở đây.
        # Có span + log riêng thì mới chứng minh được chậm là do RAG chứ không
        # phải do LLM.
        with child_span(langfuse_client, "rag-retrieve") as span:
            rag_started = time.perf_counter()
            docs = retrieve(message)
            rag_ms = int((time.perf_counter() - rag_started) * 1000)
            if span is not None:
                span.update(
                    output={"doc_count": len(docs)},
                    metadata={"retrieval_ms": rag_ms, "doc_count": len(docs)},
                )
        # Ghi ra log JSON để đối chiếu Metrics -> Traces -> Logs.
        # correlation_id/user_id_hash/... đã được bind sẵn ở middleware nên
        # tự động đi kèm, không cần truyền lại.
        log.info(
            "rag_retrieved",
            service="agent",
            latency_ms=rag_ms,
            payload={"doc_count": len(docs)},
        )

        prompt = resolve_prompt(
            langfuse_client,
            feature=feature,
            docs=docs,
            message=message,
            enabled=tracing_enabled(),
        )

        # --- Bước 2: gọi LLM ---
        with child_span(langfuse_client, "llm-generate") as span:
            llm_started = time.perf_counter()
            response = self.llm.generate(prompt.text)
            llm_ms = int((time.perf_counter() - llm_started) * 1000)
            if span is not None:
                span.update(
                    metadata={
                        "generation_ms": llm_ms,
                        "prompt_version": prompt.version,
                        "prompt_label": prompt.label,
                    },
                )
        log.info(
            "llm_generated",
            service="agent",
            latency_ms=llm_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
        )

        quality_score = self._heuristic_quality(message, response.text, docs)
        latency_ms = int((time.perf_counter() - started) * 1000)
        cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)

        langfuse_client.update_current_trace(
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model],
            metadata={
                "prompt_name": prompt.name,
                "prompt_label": prompt.label,
                "prompt_version": prompt.version,
                "prompt_source": prompt.source,
            },
        )
        langfuse_client.update_current_generation(
            model=self.model,
            metadata={
                "doc_count": len(docs),
                "query_preview": summarize_text(message),
                # Bóc tách latency theo từng bước, để mở trace là thấy ngay
                # bước nào ăn hết thời gian (RAG hay LLM).
                "rag_ms": rag_ms,
                "llm_ms": llm_ms,
                "prompt_name": prompt.name,
                "prompt_label": prompt.label,
                "prompt_version": prompt.version,
                "prompt_source": prompt.source,
                "prompt_fetch_error": prompt.fetch_error,
            },
            usage_details={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
            cost_details={"total": cost_usd},
            prompt=prompt.managed_prompt,
        )

        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * 3
        output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)
