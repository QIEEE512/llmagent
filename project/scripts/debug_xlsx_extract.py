from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.documents import extract_text


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_xlsx_extract.py <xlsx_path>")
        return 2

    fp = Path(sys.argv[1])
    text, meta = extract_text(fp, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    print("meta:", meta)
    print("text head:\n", text[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
