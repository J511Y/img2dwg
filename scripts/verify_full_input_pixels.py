"""Prove original-page serving normalization matches the frozen inference input.

This is a pixel audit, not a second model evaluation or a quality override.
Twenty originals are opened only after the candidate and evaluation are frozen.
"""
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageOps
from img2dwg.shared_inference import normalize


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--retention-only', action='store_true')
    a = p.parse_args()
    if a.retention_only:
        rows = [r for r in json.loads((a.root/'data/index.json').read_text())
                if r['cohort'] in ('original', 'additional')]
        assert len(rows) == 10
        prepared = a.root/'data'
        output = a.root/'raw-input-preflight'
    else:
        receipt = json.loads((a.root/'CPU-fresh/receipt.json').read_text())
        freeze = json.loads((a.root/'GPU/candidate-freeze.json').read_text())
        assert receipt['candidate_frozen_before_twenty']
        assert receipt['model_sha256'] == freeze['model_sha256']
        rows = json.loads((a.root/'CPU-fresh/index.json').read_text())
        assert len(rows) == 30
        prepared = a.root/'CPU-fresh/review-data'
        output = a.root/'raw-input-verification'
    if output.exists():
        raise FileExistsError('Preserve the first pixel audit: '+str(output))
    source = {r['sample_id']: r for r in
              map(json.loads, (a.dataset/'bundle/records.jsonl').read_text(encoding='utf-8').splitlines())}
    output.mkdir(parents=True)
    results = []
    for row in rows:
        key = row['sample_id']; original = source[key]
        path = a.dataset/'cases'/key/original['image_path']
        assert sha(path) == row['original_image_sha256'] == original['image_sha256']
        expected = prepared/key/'input.png'
        assert sha(expected) == row['input_sha256']
        with Image.open(path) as im:
            im.seek(original.get('primary_frame_index', 0))
            page = ImageOps.exif_transpose(im).convert('RGB')
        canvas, transform = normalize(page, 512)
        with Image.open(expected) as im:
            assert canvas.tobytes() == im.convert('RGB').tobytes(), 'Pixel mismatch: '+key
        # Actual source-page pixels, before letterboxing, for any authorized
        # later authenticated upload. No GT image is used here.
        upload = output/(key+'.png'); page.save(upload)
        results.append({'sample_id': key, 'original_sha256': sha(path),
                        'prepared_sha256': sha(expected), 'raw_page_png_sha256': sha(upload),
                        'primary_frame_index': original.get('primary_frame_index', 0),
                        'source_size_after_EXIF': list(page.size), 'pixel_exact': True,
                        'serving_transform': transform})
    result = {'schema': 'full-original-input-pixels/v1', 'cases': len(results),
              'all_pixel_exact': True, 'model_inference_repeated': False,
              'source_modified': False, 'rows': results}
    (output/'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'cases': len(results), 'all_pixel_exact': True, 'receipt': str(output/'receipt.json')}))


if __name__ == '__main__':
    main()
