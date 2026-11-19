"""Check the AI configuration with one small request.

    python -m app.agent.check

Prints the provider and model in use and the reply, or the error. The key
itself is never printed.
"""

from __future__ import annotations

import sys

from ..config import get_settings
from .agent import AgentUnavailable, check_connection


def main() -> int:
    s = get_settings()
    print(f"AI_PROVIDER={s.ai_provider}  active={s.active_ai_provider or 'none'}  model={s.ai_model}")
    try:
        out = check_connection()
    except AgentUnavailable as exc:
        print(f"FAILED: {exc}")
        return 1
    print(f"OK: {out['provider']} / {out['model']} replied {out['reply']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
