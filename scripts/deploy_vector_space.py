"""Publish the explicitly labelled diagnostic baseline to the private Space.

Trained-model deployment is withdrawn. This script cannot present the current
observed-line app as a successful trained-model release.
"""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--space', default='youjunhyeok/img2dwg')
    parser.add_argument('--output', type=Path, default=Path('outputs/vector-recovery-2026-10-13/deployment.json'))
    parser.add_argument('--dry-run', action='store_true', help='Check the package without changing Hugging Face')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='baseline-space-') as temporary:
        stage = Path(temporary)
        for name in ('app.py', 'requirements.txt', 'README.md'):
            shutil.copy2(root / 'spaces/img2dwg' / name, stage / name)
        (stage / 'img2dwg').mkdir()
        for name in ('__init__.py', 'model.py', 'vector.py', 'inference.py', 'grounding.py'):
            shutil.copy2(root / 'img2dwg' / name, stage / 'img2dwg' / name)
        output = {
            'space': args.space,
            'space_url': f'https://huggingface.co/spaces/{args.space}',
            'inference_mode': 'observed-line-detection-baseline',
            'model_restoration': False,
            'model_sha256': None,
            'files': {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in stage.rglob('*') if p.is_file()},
            'source_dataset_mounted': False,
            'status': 'package-checked',
        }
        if not args.dry_run:
            api = HfApi()
            if not api.space_info(args.space).private:
                raise ValueError('This project uses a private inference Space')
            commit = api.upload_folder(
                repo_id=args.space, repo_type='space', folder_path=stage,
                commit_message='Keep rejected model withdrawn; serve labelled observed-line diagnostic baseline',
            )
            output.update(space_commit=commit.oid, status='uploaded-build-pending')
        args.output.write_text(json.dumps(output, indent=2), encoding='utf-8')
        print(json.dumps(output))


if __name__ == '__main__':
    main()
