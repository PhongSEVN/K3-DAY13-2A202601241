from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

try:
    from langfuse import get_client, observe

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_trace(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

    def get_client():
        return _DummyClient()


def get_langfuse_client():
    return get_client()


@contextmanager
def child_span(client: Any, name: str, **kwargs: Any) -> Iterator[Any]:
    """Bọc một đoạn code thành span con nằm trong trace hiện tại.

    Vì sao cần: mặc định cả request chỉ sinh ra ĐÚNG MỘT span tên "run", nên khi
    latency tăng ta không biết thời gian nằm ở bước RAG hay bước gọi LLM.
    Tách span con thì trace waterfall mới chỉ ra được bước nào chậm (yêu cầu
    CP3: "dùng trace để khoanh vùng span bất thường").

    Hàm này cố tình "mềm": nếu client không có start_as_current_span
    (ví dụ client giả trong test, hoặc chưa cài langfuse) thì vẫn chạy code
    bình thường và trả về None thay vì ném lỗi — tracing không bao giờ được
    phép làm hỏng request của người dùng.
    """
    starter = getattr(client, "start_as_current_span", None)
    if starter is None:
        yield None
        return
    with starter(name=name, **kwargs) as span:
        yield span


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )
