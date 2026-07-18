
import sys
from pathlib import Path

# parent of this scripts/ folder -- on sys.path so `app` is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings 
from app.database import ensure_database_exists


def main() -> None:
    target_db = settings.database_url.rsplit("/", 1)[-1]
    ensure_database_exists()
    print(f"Database '{target_db}' is ready (created if it didn't already exist).")


if __name__ == "__main__":
    sys.exit(main())
