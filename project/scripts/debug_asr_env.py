from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"

    # Ensure `import app` works when running as a script.
    sys.path.insert(0, str(project_root))

    print("== ASR env self-check ==")
    print("cwd:", os.getcwd())
    print("project_root:", project_root)
    print(".env exists:", env_path.exists(), str(env_path))

    # Import triggers load_dotenv() in app.services.ai
    from app.services import ai  # noqa: F401

    key_present = bool(os.environ.get("APP_DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"))
    print("APP_DASHSCOPE_API_KEY present:", bool(os.environ.get("APP_DASHSCOPE_API_KEY")))
    print("DASHSCOPE_API_KEY present:", bool(os.environ.get("DASHSCOPE_API_KEY")))
    print("any key present:", key_present)

    model = os.environ.get("APP_QWEN_ASR_MODEL") or "qwen3-asr-flash"
    print("APP_QWEN_ASR_MODEL:", os.environ.get("APP_QWEN_ASR_MODEL"))
    print("effective model:", model)

    print("dashscope.MultiModalConversation available:", hasattr(__import__("dashscope"), "MultiModalConversation"))

    print("\nTip:")
    print("- 如果 any key present=False，说明运行环境没把 .env 带进去或没加载成功。")
    print("- 如果 key 存在但仍然在 /api/voice/chat 里返回 404，通常是模型名不可用/账号无权限。")


if __name__ == "__main__":
    main()
