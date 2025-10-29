#!/usr/bin/env python3
"""
Download models listed in a JSON manifest into ComfyUI models directory.

Usage:
  python scripts/download_models.py \
    --config models_download.json \
    [--root /workspace/ComfyUI/models] \
    [--categories checkpoints,vae,loras] \
    [--concurrency 4] \
    [--force]

Environment:
  HUGGINGFACE_TOKEN: optional token for authenticated downloads
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Iterable, Optional, Tuple

import requests

CATEGORY_DIRS = {
    "checkpoints": "checkpoints",
    "vae": "vae",
    "loras": "loras",
    "unet": "unet",
    "clip": "clip",
    "clip_vision": "clip_vision",
    "text_encoders": "text_encoders",
    "diffusion_models": "diffusion_models",
    "controlnet": "controlnet",
}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path, headers: Optional[Dict[str, str]] = None, timeout: int = 3600) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, headers=headers, timeout=timeout) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        initial_start = time.time()
        last_progress = initial_start
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                # Lightweight progress to stdout every ~5s
                now = time.time()
                if total and (now - last_progress) > 5:
                    pct = downloaded * 100.0 / total
                    sys.stdout.write(f"\r⬇️  {dest.name}: {pct:.1f}% ({downloaded/1e6:.1f}/{total/1e6:.1f} MB)")
                    sys.stdout.flush()
                    last_progress = now
    tmp.rename(dest)
    sys.stdout.write(f"\r✅ {dest.name}: 100%\n")


def build_headers(url: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    token = os.getenv("HUGGINGFACE_TOKEN")
    if token and ("huggingface.co" in url):
        headers["Authorization"] = f"Bearer {token}"
    return headers


def process_entry(root: Path, entry: Dict[str, Any], force: bool, timeout: int) -> Tuple[str, bool, Optional[str]]:
    category = entry.get("category")
    filename = entry.get("filename")
    url = entry.get("url")
    checksum = entry.get("sha256")
    requires_auth = bool(entry.get("requires_auth", False))

    if not category or not filename or not url:
        return (filename or "<unknown>", False, "invalid entry")

    subdir = CATEGORY_DIRS.get(category, category)
    dest = root / subdir / filename

    if dest.exists() and not force:
        if checksum:
            try:
                if sha256_file(dest) == checksum:
                    return (filename, True, None)
                else:
                    # Mismatch: force redownload
                    dest.unlink(missing_ok=True)
            except Exception as e:
                return (filename, False, f"checksum error: {e}")
        else:
            return (filename, True, None)

    try:
        headers = build_headers(url)
        if requires_auth and "Authorization" not in headers:
            return (filename, False, "requires auth: set HUGGINGFACE_TOKEN")
        download_file(url, dest, headers=headers, timeout=timeout)
        if checksum:
            actual = sha256_file(dest)
            if actual != checksum:
                dest.unlink(missing_ok=True)
                return (filename, False, "checksum mismatch after download")
        return (filename, True, None)
    except Exception as e:
        return (filename, False, str(e))


def load_manifest(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def filter_models(models: Iterable[Dict[str, Any]], categories: Optional[Iterable[str]]) -> Iterable[Dict[str, Any]]:
    if not categories:
        yield from models
        return
    allowed = {c.strip() for c in categories}
    for m in models:
        if m.get("category") in allowed:
            yield m


def main() -> int:
    ap = argparse.ArgumentParser(description="Download models into ComfyUI models directory")
    ap.add_argument("--config", required=True, help="Path to models manifest JSON")
    ap.add_argument("--root", default=None, help="Override models root directory")
    ap.add_argument("--categories", default=None, help="Comma-separated category filter")
    ap.add_argument("--concurrency", type=int, default=None, help="Max parallel downloads")
    ap.add_argument("--timeout", type=int, default=None, help="Per-request timeout (seconds)")
    ap.add_argument("--force", action="store_true", help="Force re-download even if file exists")
    args = ap.parse_args()

    manifest = load_manifest(Path(args.config))
    root = Path(args.root) if args.root else Path(manifest.get("models_root", "/workspace/ComfyUI/models"))
    concurrency = args.concurrency if args.concurrency else int(manifest.get("concurrency", 4))
    timeout = args.timeout if args.timeout else int(manifest.get("timeout_seconds", 3600))

    cats = None
    if args.categories:
        cats = [c.strip() for c in args.categories.split(",") if c.strip()]

    models = list(filter_models(manifest.get("models", []), cats))
    if not models:
        print("No models to process.")
        return 0

    print(f"Models root: {root}")
    print(f"Total models: {len(models)} | Concurrency: {concurrency}")

    results: list[Tuple[str, bool, Optional[str]]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [ex.submit(process_entry, root, m, args.force, timeout) for m in models]
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())

    ok = sum(1 for _, success, _ in results if success)
    failed = [(name, err) for name, success, err in results if not success]

    print(f"✅ Success: {ok} / {len(models)}")
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for name, err in failed[:20]:
            print(f" - {name}: {err}")
        if len(failed) > 20:
            print(f" ... and {len(failed) - 20} more")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
