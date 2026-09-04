"""Full migration chain up and back down on a throwaway SQLite database."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _alembic(*args, db_url):
    env = {**os.environ, "DATABASE_URL": db_url, "MODEL_PATH": "does-not-exist.pt"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND, env=env, capture_output=True, text=True,
    )


def test_upgrade_head_then_downgrade_base():
    with tempfile.TemporaryDirectory() as tmp:
        db_url = f"sqlite+aiosqlite:///{Path(tmp) / 'chain.db'}"

        up = _alembic("upgrade", "head", db_url=db_url)
        assert up.returncode == 0, up.stderr

        down = _alembic("downgrade", "base", db_url=db_url)
        assert down.returncode == 0, down.stderr

        again = _alembic("upgrade", "head", db_url=db_url)
        assert again.returncode == 0, again.stderr
