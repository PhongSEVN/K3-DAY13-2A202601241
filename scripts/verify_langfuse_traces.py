"""List recent Langfuse traces and prompt labels without printing secrets."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    public_key = (os.getenv("LANGFUSE_PUBLIC_KEY") or "").strip()
    secret_key = (os.getenv("LANGFUSE_SECRET_KEY") or "").strip()
    host = (os.getenv("LANGFUSE_HOST") or "https://cloud.langfuse.com").strip()
    if not public_key or not secret_key:
        print("BLOCKED: missing Langfuse keys")
        return 2

    from langfuse import Langfuse

    client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    prompt_name = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")

    for label in ("baseline", "candidate", "production"):
        prompt = client.get_prompt(prompt_name, label=label, type="text")
        print(
            f"prompt label={label} version={prompt.version} "
            f"fallback={getattr(prompt, 'is_fallback', False)}"
        )

    api = getattr(client, "api", None)
    if api is None:
        print("trace_list: api client unavailable")
        return 0

    traces = api.trace.list(limit=20)
    data = getattr(traces, "data", traces) or []
    print(f"trace_count={len(data)}")
    with_meta = 0
    for trace in data:
        meta = getattr(trace, "metadata", None) or {}
        if not isinstance(meta, dict):
            meta = {}
        if meta.get("prompt_name") or meta.get("prompt_label"):
            with_meta += 1
        print(
            getattr(trace, "id", None),
            meta.get("prompt_label"),
            meta.get("prompt_version"),
            meta.get("prompt_source"),
        )
    print(f"traces_with_prompt_metadata={with_meta}")
    return 0 if len(data) >= 10 else 1


if __name__ == "__main__":
    raise SystemExit(main())
