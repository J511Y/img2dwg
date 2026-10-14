"""Authenticated live upload/download check of a pinned private Space."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import ezdxf
from huggingface_hub import HfApi, get_token, hf_hub_download
from gradio_client import Client, handle_file


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--deployment', type=Path, required=True)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    deployment = json.loads(args.deployment.read_text())
    api = HfApi()
    info = api.space_info(deployment['space'])
    if not info.private or info.runtime.stage != 'RUNNING':
        raise RuntimeError('Pinned private Space is not running yet: ' + str(info.runtime.stage))
    if info.runtime.raw.get('sha') != deployment['space_revision']:
        raise RuntimeError('Live runtime still runs a different revision')
    checkpoint = hf_hub_download(deployment['model_repo'], 'model.safetensors',
                                 revision=deployment['model_revision'])
    assert digest(checkpoint) == deployment['model_sha256']
    client = Client(deployment['space'], hf_token=get_token(), download_files=str(args.output / 'downloads'))
    rows = []
    for rounding in (False, True):
        # Real uploaded original pixels; no sample identity or target CAD input.
        image = handle_file(str(args.image.resolve()))
        result = client.predict({'background': image, 'layers': [], 'composite': image}, rounding, api_name='/infer')
        assert len(result) == 7
        folder = args.output / ('rounded' if rounding else 'raw')
        folder.mkdir(exist_ok=True)
        (folder / 'viewer.html').write_text(result[0], encoding='utf-8')
        (folder / 'status.md').write_text(result[1], encoding='utf-8')
        for value, name in zip(result[2:], ('prediction.svg', 'prediction.dxf', 'shared-graph.json', 'receipt.json', 'raw.svg')):
            shutil.copy2(value, folder / name)
        receipt = json.loads((folder / 'receipt.json').read_text())
        assert receipt['model_sha256'] == deployment['model_sha256']
        assert receipt['model_revision'] == deployment['model_revision']
        assert receipt['source_CAD_or_dataset_access'] is False
        svg = (folder / 'prediction.svg').read_text(encoding='utf-8')
        assert '<image' not in svg and 'data:image/' not in svg and '<path' in svg
        doc = ezdxf.readfile(folder / 'prediction.dxf')
        audit = doc.audit()
        assert not audit.has_errors and doc.header['$INSUNITS'] == 4
        assert not len(doc.modelspace().query('IMAGE'))
        assert len(doc.modelspace().query('DIMENSION')) > 0
        assert len(doc.modelspace().query('INSERT')) > 0
        rows.append({'rounding': rounding, 'native_blocks': len(doc.modelspace().query('INSERT')),
            'native_dimensions': len(doc.modelspace().query('DIMENSION')),
            'audit_errors': len(audit.errors), 'elapsed_seconds': receipt['elapsed_seconds'],
            'model_sha256': receipt['model_sha256'], 'constraint_receipt': receipt['constraints'],
            'files': {p.name: digest(p) for p in folder.iterdir() if p.is_file()}})
        print(json.dumps({k: rows[-1][k] for k in ('rounding', 'native_blocks', 'native_dimensions', 'elapsed_seconds')}), flush=True)
    before = json.loads((args.output / 'raw/shared-graph.json').read_text())
    after = json.loads((args.output / 'rounded/shared-graph.json').read_text())
    assert before['nodes_mm'] == after['nodes_mm']
    assert [c for c in before['components'] if c['kind'] == 'dimension'] == [c for c in after['components'] if c['kind'] == 'dimension']
    result = {'status': 'authenticated-upload-download-passed', 'space_revision': info.runtime.raw['sha'],
        'model_revision': deployment['model_revision'], 'model_sha256': deployment['model_sha256'],
        'input_sha256': digest(args.image), 'image_to_model_to_vector': True,
        'rows': rows, 'full_training_quality_claim': False, 'native_DWG_download': False}
    (args.output / 'live-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(result['status'])


if __name__ == '__main__':
    main()
