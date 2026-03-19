import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    project_dir = Path(__file__).resolve().parent
    env_file = project_dir / ".env"
    load_dotenv(dotenv_path=env_file)

    port = (
        os.getenv("APP_PORT")
        or os.getenv("STREAMLIT_SERVER_PORT")
        or "8501"
    )

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(project_dir / "app.py"),
        "--server.port",
        str(port),
    ]

    print(f"Starting app on port {port} (from {env_file})")
    raise SystemExit(subprocess.call(cmd, cwd=str(project_dir)))


if __name__ == "__main__":
    main()
