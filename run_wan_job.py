#!/usr/bin/env python3
"""Download/resume the Wan model inside a claimed Kelpie job, then render."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from huggingface_hub import snapshot_download


DEFAULT_REPO_ID = "Wan-AI/Wan2.2-TI2V-5B"
DEFAULT_MODEL_DIR = "/opt/models/Wan2.2-TI2V-5B"
READY_MARKER = ".ace-model-ready.json"


def log(message: str) -> None:
    print(f"[model] {message}", flush=True)


def disk_summary(path: Path) -> str:
    target = path if path.exists() else path.parent
    usage = shutil.disk_usage(target)
    gib = 1024**3
    return (
        f"disk total={usage.total / gib:.1f}GiB "
        f"used={usage.used / gib:.1f}GiB free={usage.free / gib:.1f}GiB"
    )


def ensure_model(repo_id: str, model_dir: Path, retries: int) -> None:
    marker = model_dir / READY_MARKER
    if marker.is_file():
        log(f"ready marker found; reusing {model_dir}")
        return

    model_dir.mkdir(parents=True, exist_ok=True)
    log(f"preparing repo={repo_id} destination={model_dir}")
    log(disk_summary(model_dir))

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            log(f"download/resume attempt {attempt}/{retries}")
            resolved_path = snapshot_download(
                repo_id=repo_id,
                local_dir=str(model_dir),
                token=os.environ.get("HF_TOKEN") or None,
            )
            marker.write_text(
                json.dumps(
                    {
                        "repo_id": repo_id,
                        "resolved_path": resolved_path,
                        "completed_unix": int(time.time()),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            log("download verified by huggingface_hub")
            log(disk_summary(model_dir))
            return
        except Exception as exc:  # noqa: BLE001 - retry all transfer failures
            last_error = exc
            log(f"attempt {attempt} failed: {type(exc).__name__}: {exc}")
            if attempt < retries:
                delay = min(30, 5 * attempt)
                log(f"retrying in {delay}s; partial files remain for resume")
                time.sleep(delay)

    raise RuntimeError(
        f"model download failed after {retries} attempts: {last_error}"
    )


def main() -> int:
    repo_id = os.environ.get("WAN_REPO_ID", DEFAULT_REPO_ID)
    model_dir = Path(os.environ.get("WAN_MODEL_DIR", DEFAULT_MODEL_DIR)).resolve()
    retries = int(os.environ.get("WAN_DOWNLOAD_RETRIES", "4"))
    if retries < 1 or retries > 10:
        raise ValueError("WAN_DOWNLOAD_RETRIES must be between 1 and 10")

    ensure_model(repo_id, model_dir, retries)

    worker_args = list(sys.argv[1:])
    if "--ckpt-dir-local" not in worker_args:
        worker_args.extend(["--ckpt-dir-local", str(model_dir)])

    command = [sys.executable, "/opt/wan_worker.py", *worker_args]
    log("model ready; starting Wan renderer")
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
