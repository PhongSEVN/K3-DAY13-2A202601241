"""Create day13-chat prompt v1/v2 on Langfuse when keys are configured.

Usage:
  python scripts/setup_langfuse_prompts.py
  python scripts/setup_langfuse_prompts.py --promote-v2
  python scripts/setup_langfuse_prompts.py --rollback-v1

Does not print secret values. Exits non-zero if Langfuse keys are missing
or the API call fails.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

PROMPT_NAME_DEFAULT = "day13-chat"

V1_TEMPLATE = (
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Answer briefly in 2-3 sentences."
)

V2_TEMPLATE = (
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Answer in a short bullet list (max 4 bullets)."
)


def _client():
    from langfuse import Langfuse

    public_key = (os.getenv("LANGFUSE_PUBLIC_KEY") or "").strip()
    secret_key = (os.getenv("LANGFUSE_SECRET_KEY") or "").strip()
    host = (os.getenv("LANGFUSE_HOST") or "https://cloud.langfuse.com").strip()
    if not public_key or not secret_key:
        raise RuntimeError("LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set in .env")
    return Langfuse(public_key=public_key, secret_key=secret_key, host=host), host


def create_versions(client, prompt_name: str) -> tuple[int, int]:
    v1 = client.create_prompt(
        name=prompt_name,
        prompt=V1_TEMPLATE,
        labels=["baseline", "production"],
        type="text",
        commit_message="day13 baseline production",
    )
    v2 = client.create_prompt(
        name=prompt_name,
        prompt=V2_TEMPLATE,
        labels=["candidate"],
        type="text",
        commit_message="day13 candidate format change",
    )
    return int(v1.version), int(v2.version)


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--promote-v2", action="store_true", help="Move production label to latest candidate version")
    parser.add_argument("--rollback-v1", action="store_true", help="Move production label back to baseline version")
    args = parser.parse_args()

    prompt_name = os.getenv("LANGFUSE_PROMPT_NAME", PROMPT_NAME_DEFAULT)

    try:
        client, host = _client()
    except RuntimeError as exc:
        print(f"BLOCKED: {exc}")
        print("Fill keys from Lab Coach project, then re-run this script.")
        return 2
    except ImportError:
        print("BLOCKED: langfuse package not installed. pip install -r requirements.txt")
        return 2

    print(f"Host configured: {bool(host)}")
    print(f"Prompt name: {prompt_name}")

    try:
        if args.promote_v2:
            candidate = client.get_prompt(prompt_name, label="candidate", type="text")
            client.update_prompt(
                name=prompt_name,
                version=int(candidate.version),
                new_labels=["candidate", "production"],
            )
            client.flush()
            print(f"PROMOTED: production -> version {candidate.version}")
            return 0

        if args.rollback_v1:
            baseline = client.get_prompt(prompt_name, label="baseline", type="text")
            client.update_prompt(
                name=prompt_name,
                version=int(baseline.version),
                new_labels=["baseline", "production"],
            )
            client.flush()
            print(f"ROLLBACK: production -> version {baseline.version}")
            return 0

        v1, v2 = create_versions(client, prompt_name)
        client.flush()
        print(f"Created v1 version={v1} labels=baseline,production")
        print(f"Created v2 version={v2} labels=candidate")
        print("DONE: prompt versions ready.")
        print("Next:")
        print("  1) uvicorn app.main:app --reload --env-file .env")
        print("  2) python scripts/load_test.py --concurrency 5")
        print("  3) Same chat with LANGFUSE_PROMPT_LABEL=baseline then candidate")
        print("  4) python scripts/setup_langfuse_prompts.py --promote-v2")
        print("  5) python scripts/setup_langfuse_prompts.py --rollback-v1")
        print("  6) Capture screenshots/trace IDs into submission/evidence/")
        return 0
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
