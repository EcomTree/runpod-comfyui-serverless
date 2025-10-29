#!/usr/bin/env python3
"""
Verify links in the models manifest.

Usage:
  python scripts/verify_links.py --config models_download.json [--concurrency 16]

Skips HEAD check for entries marked requires_auth when no token is provided.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from typing import Dict, Any, Tuple

import requests


def check_url(entry: Dict[str, Any]) -> Tuple[str, bool, int, str]:
    name = entry.get("filename") or entry.get("name") or "<unknown>"
    url = entry.get("url")
    requires_auth = bool(entry.get("requires_auth", False))
    if not url:
        return (name, False, 0, "missing url")

    headers = {}
    token = os.getenv("HUGGINGFACE_TOKEN")
    if requires_auth and token and ("huggingface.co" in url):
        headers["Authorization"] = f"Bearer {token}"
    elif requires_auth and ("huggingface.co" in url):
        return (name, False, 401, "requires auth")

    try:
        r = requests.head(url, allow_redirects=True, headers=headers, timeout=30)
        return (name, r.ok, r.status_code, "ok" if r.ok else r.reason)
    except requests.RequestException as e:
        return (name, False, 0, str(e))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--concurrency", type=int, default=16)
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    models = manifest.get("models", [])
    print(f"Verifying {len(models)} links...")

    ok = 0
    fail = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        for name, success, status, msg in ex.map(check_url, models):
            status_str = status if status else "-"
            if success:
                ok += 1
                print(f"✅ {name}: {status_str}")
            else:
                fail += 1
                print(f"❌ {name}: {status_str} ({msg})")

    print(f"Done. OK={ok}, FAIL={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
