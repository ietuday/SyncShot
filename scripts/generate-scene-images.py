#!/usr/bin/env python3
"""Generate optional AI illustrations from the Phase 9.1 scene plan.

Dry-run by default. Explicit --execute plus OPENAI_API_KEY required for API calls.
"""
import argparse
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

MAX_SCENES = 500
MAX_PROMPT = 4000
API_ENDPOINT = "https://api.openai.com/v1/images/generations"


def load_plan(path: Path, limit: int) -> list[dict]:
    if not 1 <= limit <= MAX_SCENES:
        raise ValueError(f"--limit must be 1..{MAX_SCENES}")
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("scene plan exceeds 4 MiB")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("expected scene-plan version 1")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("scene plan contains no scenes")
    if len(scenes) > 10000:
        raise ValueError("scene plan exceeds 10000 scenes")
    result = []
    for index, scene in enumerate(scenes[:limit], 1):
        if not isinstance(scene, dict) or scene.get("index") != index:
            raise ValueError(f"scene {index} has invalid index")
        prompt = scene.get("visual_prompt")
        if not isinstance(prompt, str) or not 0 < len(prompt.strip()) <= MAX_PROMPT:
            raise ValueError(f"scene {index} has invalid prompt")
        result.append({"index": index, "prompt": prompt.strip(),
                       "start": scene.get("start"), "end": scene.get("end")})
    return result


def request_image(prompt: str, api_key: str, model: str = "gpt-image-1") -> bytes:
    payload = json.dumps({"model": model, "prompt": prompt, "size": "1024x1024",
                          "n": 1}).encode("utf-8")
    request = urllib.request.Request(
        API_ENDPOINT, data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.load(response)
    try:
        return base64.b64decode(data["data"][0]["b64_json"], validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError("image provider returned no valid base64 image") from exc


def generate(scenes: list[dict], directory: Path, execute: bool,
             api_key: str | None = None, provider=request_image) -> list[dict]:
    # Never overwrite existing files; outputs are deterministic scene indexes.
    items = []
    if execute and not api_key:
        raise ValueError("OPENAI_API_KEY is required for --execute")
    if execute:
        directory.mkdir(parents=True, exist_ok=True)
    for scene in scenes:
        target = directory / f"scene-{scene['index']:04d}.png"
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"refusing to overwrite {target}")
        item = {"index": scene["index"], "output": str(target),
                "start": scene["start"], "end": scene["end"], "prompt": scene["prompt"]}
        if execute:
            content = provider(scene["prompt"], api_key)
            if not isinstance(content, bytes) or not content.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("provider returned invalid PNG image")
            # Use exclusive creation so competing jobs cannot overwrite a scene.
            try:
                with target.open("xb") as output:
                    output.write(content)
            except Exception:
                target.unlink(missing_ok=True)
                raise
        items.append(item)
    return items


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5,
                        help="number of scenes to prepare; max 500 (default: 5)")
    parser.add_argument("--execute", action="store_true",
                        help="call paid image generation API; dry-run otherwise")
    args = parser.parse_args(argv)
    try:
        scenes = load_plan(args.plan, args.limit)
        items = generate(scenes, args.output_dir, args.execute,
                         os.environ.get("OPENAI_API_KEY"))
    except (OSError, ValueError, urllib.error.URLError) as error:
        parser.exit(1, f"Scene image generation failed: {error}\n")
    print(json.dumps({"mode": "execute" if args.execute else "preview",
                      "scenes": items}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
