"""Publish an explicitly authorized pilot checkpoint and pin the private Space."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--model', default='youjunhyeok/img2dwg-shared-components-v1')
    parser.add_argument('--space', default='youjunhyeok/img2dwg')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verification', type=Path)
    parser.add_argument('--experimental-authorized', action='store_true',
                        help='Latest explicit user request authorizes a five-case pilot; never marks quality passed')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.experimental_authorized:
        raise ValueError('This release is a five-case pilot, not a validated production model')
    root = Path(__file__).resolve().parents[1]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    hashes = {name: sha(args.checkpoint / name) for name in
              ('model.safetensors', 'config.json', 'library.json')}
    config = json.loads((args.checkpoint / 'config.json').read_text(encoding='utf-8'))
    original_receipt = json.loads((args.checkpoint / 'receipt.json').read_text(encoding='utf-8'))
    if hashes['model.safetensors'] != original_receipt['model_sha256']:
        raise ValueError('Training receipt checkpoint mismatch')
    if original_receipt['full_training_executed']:
        raise ValueError('Use a separately verified full-training release protocol')
    release = {'schema': 'img2dwg-pilot-release/v1', 'files': hashes,
        'model_sha256': hashes['model.safetensors'], 'trained_real_pairs': 5,
        'deployment_role': 'user-authorized-five-case-pilot',
        'quality_passed': False,
        'five_reproduction_quality_passed': original_receipt['five']['aggregate']['passed_cases'] == 5,
        'five_reproduction_metrics': original_receipt['five']['aggregate'], 'full_training_executed': False,
        'twenty_validation_passed': False, 'backbone': config['backbone'],
        'backbone_revision': config['backbone_revision'],
        'source_CAD_retrieval': False, 'training_library': 'small-local-prototypes;train-only',
        'axis_tolerance_mm': 1., 'numeric_dimensions_verified': False,
        'native_DWG_download_supported': False,
        'latest_user_authorization': 'model deployment and Space refresh after visual review acceptance'}
    if args.verification:
        verified = json.loads(args.verification.read_text(encoding='utf-8'))
        if verified['model_sha256'] != hashes['model.safetensors']:
            raise ValueError('Verification checkpoint mismatch')
        release['CPU_serving_five_metrics'] = verified['five']['aggregate']
        release['twenty_validation_metrics'] = verified['twenty']['aggregate'] if verified['twenty'] else None
        release['twenty_validation_status'] = 'failed' if verified['twenty'] and verified['twenty']['aggregate']['passed_cases'] < 20 else 'not-established'
    elif not args.dry_run:
        raise ValueError('A live pilot release requires a matching inference verification receipt')
    with tempfile.TemporaryDirectory(prefix='shared-release-') as temp:
        stage = Path(temp)
        model_stage = stage / 'model'
        model_stage.mkdir()
        for name in hashes:
            shutil.copy2(args.checkpoint / name, model_stage / name)
        (model_stage / 'release.json').write_text(json.dumps(release, indent=2), encoding='utf-8')
        (model_stage / 'README.md').write_text('''---
license: other
library_name: pytorch
tags:
- image-to-cad
- shared-node-components
base_model: facebook/dinov3-vitb16-pretrain-lvd1689m
---
# img2dwg shared-component pilot

Private corporate experiment, trained on five real as-built / before-state CAD pairs.
Frozen DINOv3 + image-conditioned shared-node and typed component decoder.
Outputs include native component parameters, node references, dimension values,
and a train-only library of small normalized local primitives. No whole-plan CAD
retrieval or source dataset is available to the inference app.

This is an explicitly user-authorized five-case reproduction pilot, not a
generalization-validated or dimension-complete production release. Full 1,028-case
training and successful separate 20-case validation are not claimed. Inspect
geometry, dimension references, scales and missing elements before CAD use.
Native wall/room/window business semantics and editable DWG export are incomplete.
Private use only; no license grant for the corporate training assets/prototypes.
Backbone license remains governed by its upstream model card.
''', encoding='utf-8')
        space_stage = stage / 'space'
        (space_stage / 'img2dwg').mkdir(parents=True)
        for name in ('app.py', 'requirements.txt', 'README.md'):
            shutil.copy2(root / 'spaces/img2dwg' / name, space_stage / name)
        for name in ('__init__.py', 'components.py', 'vector.py', 'structured.py',
                     'graph_decoder.py', 'graph_constraints.py', 'shared_inference.py'):
            shutil.copy2(root / 'img2dwg' / name, space_stage / 'img2dwg' / name)
        package = {p.relative_to(space_stage).as_posix(): sha(p) for p in space_stage.rglob('*') if p.is_file()}
        result = {**release, 'space': args.space, 'model_repo': args.model,
            'space_url': 'https://huggingface.co/spaces/' + args.space,
            'space_files': package, 'source_dataset_mounted': False,
            'status': 'package-checked'}
        if not args.dry_run:
            api = HfApi()
            if not api.space_info(args.space).private:
                raise ValueError('Inference Space must remain private')
            api.create_repo(args.model, private=True, exist_ok=True)
            if not api.model_info(args.model).private:
                raise ValueError('Corporate checkpoint repository must remain private')
            model_commit = api.upload_folder(repo_id=args.model, folder_path=model_stage,
                commit_message='Publish authorized five-case shared-node component pilot; generalization unverified')
            for key, value in {'MODEL_REPO': args.model, 'MODEL_REVISION': model_commit.oid,
                               'MODEL_SHA256': hashes['model.safetensors']}.items():
                api.add_space_variable(args.space, key=key, value=value)
            space_commit = api.upload_folder(repo_id=args.space, repo_type='space', folder_path=space_stage,
                commit_message='Serve pinned shared-component pilot with native CAD vectors and optional length editing')
            result.update(model_revision=model_commit.oid, space_revision=space_commit.oid,
                          status='uploaded-build-pending')
        args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({k: result[k] for k in ('status', 'space', 'model_repo', 'model_sha256')}))


if __name__ == '__main__':
    main()
