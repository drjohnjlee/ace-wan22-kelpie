#!/usr/bin/env python3
"""Wan 2.2 TI2V command wrapper used by Kelpie jobs."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import requests


WAN_REPO_DIR = "/opt/Wan2.2"
OUT_DIR = "/opt/outputs"
ASSETS_DIR = "/opt/assets"


def prepare_image(args: argparse.Namespace, assets_dir: str) -> str | None:
    assets_path = Path(assets_dir).resolve()

    if args.image_b64:
        data_part = args.image_b64
        if data_part.startswith("data:") and ";base64," in data_part:
            data_part = data_part.split(";base64,", 1)[1]
        try:
            raw = base64.b64decode(data_part, validate=True)
            out_path = assets_path / f"inline_{args.id}.png"
            out_path.write_bytes(raw)
            print(f"[worker] prepared base64 image -> {out_path}", flush=True)
            return str(out_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[worker][warn] invalid image-b64: {exc}", flush=True)

    if args.image_url:
        try:
            with requests.get(args.image_url, timeout=(15, 120), stream=True) as response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                suffix = ".jpg"
                if "png" in content_type:
                    suffix = ".png"
                elif "webp" in content_type:
                    suffix = ".webp"
                elif args.image_url.lower().endswith((".png", ".webp", ".jpg", ".jpeg")):
                    suffix = os.path.splitext(args.image_url)[1]
                out_path = assets_path / f"download_{args.id}{suffix}"
                with out_path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)
            print(f"[worker] downloaded image -> {out_path}", flush=True)
            return str(out_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[worker][warn] image-url download failed: {exc}", flush=True)

    if args.image_path:
        source = Path(args.image_path).resolve()
        if not source.is_file():
            print(f"[worker][warn] image-path is not a file: {source}", flush=True)
            return None
        out_path = assets_path / f"local_{args.id}{source.suffix or '.png'}"
        shutil.copy2(source, out_path)
        print(f"[worker] copied image -> {out_path}", flush=True)
        return str(out_path)

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", default=None)
    parser.add_argument("--size", default="1280*704")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--image-path", dest="image_path", default="")
    parser.add_argument("--image-url", dest="image_url", default=None)
    parser.add_argument("--image-b64", dest="image_b64", default=None)
    parser.add_argument("--frame-num", dest="frame_num", type=int, default=121)
    parser.add_argument("--sample-steps", dest="sample_steps", type=int, default=50)
    parser.add_argument("--base-seed", dest="base_seed", type=int, default=None)
    parser.add_argument("--sample-solver", choices=["unipc", "dpm++"], default=None)
    parser.add_argument("--sample-shift", dest="sample_shift", type=float, default=None)
    parser.add_argument("--sample-guide-scale", dest="sample_guide_scale", type=float, default=None)
    parser.add_argument("--ckpt-dir-local", default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output-filename", default=None)
    parser.add_argument("--extra-args-json", default="{}")
    return parser.parse_args()


DEFAULT_MODEL_DIR = "/opt/models/Wan2.2-TI2V-5B"


def main() -> int:
    args = parse_args()
    args.id = args.id or str(uuid.uuid4())
    print(
        f"[worker] start id={args.id} size={args.size} "
        f"frames={args.frame_num} steps={args.sample_steps}",
        flush=True,
    )

    for directory in (OUT_DIR, ASSETS_DIR):
        Path(directory).mkdir(parents=True, exist_ok=True)

    image_path = prepare_image(args, ASSETS_DIR)
    base_name = os.path.splitext(args.output_filename or args.id)[0]
    save_file = os.path.join(OUT_DIR, f"{base_name}.mp4")

    command = [
        sys.executable,
        f"{WAN_REPO_DIR}/generate.py",
        "--task",
        "ti2v-5B",
        "--size",
        args.size,
        "--ckpt_dir",
        args.ckpt_dir_local,
        "--frame_num",
        str(args.frame_num),
        "--sample_steps",
        str(args.sample_steps),
        "--save_file",
        save_file,
        "--offload_model",
        "True",
        "--t5_cpu",
        "--prompt",
        args.prompt,
    ]
    if args.base_seed is not None:
        command.extend(["--base_seed", str(args.base_seed)])
    if args.sample_solver:
        command.extend(["--sample_solver", args.sample_solver])
    if args.sample_shift is not None:
        command.extend(["--sample_shift", str(args.sample_shift)])
    if args.sample_guide_scale is not None:
        command.extend(["--sample_guide_scale", str(args.sample_guide_scale)])
    if image_path:
        command.extend(["--image", image_path])

    extra = json.loads(args.extra_args_json)
    if not isinstance(extra, dict):
        raise ValueError("--extra-args-json must contain a JSON object")
    for key, value in extra.items():
        if not key.replace("_", "").isalnum():
            raise ValueError(f"invalid extra argument name: {key!r}")
        flag = f"--{key}"
        if isinstance(value, bool):
            if value:
                command.append(flag)
        else:
            command.extend([flag, str(value)])

    print(f"[worker] output={save_file}", flush=True)
    result = subprocess.run(command, check=False)
    output_exists = os.path.isfile(save_file)
    if result.returncode == 0 and output_exists:
        print(f"[worker] success output={save_file}", flush=True)
        return 0

    print(
        f"[worker][error] render failed rc={result.returncode} "
        f"output_exists={output_exists}",
        flush=True,
    )
    return result.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
