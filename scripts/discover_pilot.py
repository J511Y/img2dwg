"""Read immediate children of Work-linked folders; never traverse or modify originals."""
from __future__ import annotations
import argparse, collections, hashlib, json, random, unicodedata
from pathlib import Path


def discover(index: Path, output: Path, wanted: int, max_folders: int) -> dict:
    """Find exact-stem pairs in a deterministic shuffled folder sample."""
    data = json.loads(index.read_text(encoding="utf-8-sig"))
    folders = list({unicodedata.normalize("NFC", f["path"]): f for f in data["folders"]}.values())
    folders.sort(key=lambda f: f["path"])
    random.Random(20261013).shuffle(folders)
    found, issues, inspected, extensions = [], [], 0, collections.Counter()
    output.mkdir(parents=True, exist_ok=True)
    for folder in folders[:max_folders]:
        inspected += 1
        try:
            files = [p for p in Path(folder["path"]).iterdir() if p.is_file()]
            dwgs = [p for p in files if unicodedata.normalize("NFC", p.name).casefold() == "변경전후.dwg"]
            refs = [p for p in files if unicodedata.normalize("NFC", p.stem) == "준공도면"]
            if dwgs and refs:
                refs.sort(key=lambda p: p.name)
                for p in refs:
                    extensions[p.suffix.lower()] += 1
                found.append({"case_key": hashlib.sha256(folder["path"].encode()).hexdigest()[:16],
                              "case_path": folder["path"], "dwg": str(dwgs[0]),
                              "references": [str(p) for p in refs], "job_no": folder.get("jobNo")})
        except OSError as exc:
            issues.append({"case_key": hashlib.sha256(folder["path"].encode()).hexdigest()[:16], "error": type(exc).__name__})
        if len(found) >= wanted:
            break
        if inspected % 100 == 0:
            print(json.dumps({"inspected": inspected, "candidates": len(found), "errors": len(issues)}), flush=True)
    report = {"schema": "img2dwg-discovery/v1", "index_count": data["count"], "seed": 20261013,
              "inspected_folders": inspected, "candidate_count": len(found), "reference_extensions": dict(extensions),
              "candidates": found, "errors": issues, "scope": "immediate children only; not a full inventory"}
    (output / "discovery.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["index_count", "inspected_folders", "candidate_count", "reference_extensions"]}), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wanted", type=int, default=60)
    parser.add_argument("--max-folders", type=int, default=1500)
    args = parser.parse_args()
    discover(args.index, args.output, args.wanted, args.max_folders)
