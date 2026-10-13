"""Extract private before-state CAD pairs and audit dimensions and registration."""
from __future__ import annotations
import argparse, collections, hashlib, json, math, shutil, subprocess, sys, time, traceback
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps
import ezdxf
from ezdxf.addons import odafc
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.config import BackgroundPolicy, ColorPolicy, Configuration
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def digest(path: Path) -> str:
    """Hash source/output bytes without modifying a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dimension_snapshot(entity) -> dict:
    """Capture measured geometry, displayed overrides and effective style parameters."""
    attrs = entity.dxf
    row = {"type": int(attrs.dimtype), "text": attrs.get("text", ""), "style": attrs.dimstyle}
    for key in ["defpoint", "defpoint2", "defpoint3", "defpoint4", "defpoint5", "text_midpoint"]:
        v = attrs.get(key)
        if v is not None:
            row[key] = [round(float(x), 6) for x in v]
    try:
        value = entity.get_measurement()
        row["measurement"] = round(float(value), 6) if isinstance(value, (int, float)) else [round(float(x), 6) for x in value]
    except Exception as exc:
        row["measurement_error"] = type(exc).__name__
    override = entity.override()
    row["display_style"] = {k: override.get(k) for k in ["dimlfac", "dimscale", "dimtxt", "dimdec", "dimpost", "dimalt", "dimrnd"]}
    return row


def dimension_compare(expected: list[dict], actual: list[dict]) -> dict:
    """Multiset comparison prevents duplicate dimensions from inflating preservation."""
    def signature(row):
        return json.dumps(row, ensure_ascii=False, sort_keys=True)
    a, b = collections.Counter(map(signature, expected)), collections.Counter(map(signature, actual))
    missing, added = list((a-b).elements()), list((b-a).elements())
    return {"expected_count": len(expected), "actual_count": len(actual),
            "missing_or_changed": len(missing), "added_or_changed": len(added),
            "status": "not_applicable_no_dimensions" if not expected else ("pass" if not missing and not added else "fail"),
            "expected": expected, "actual": actual}


def render(doc, rect, path: Path, long_side: int = 1600) -> dict:
    """Render CAD with an exact viewport, preserving pixel-to-CAD coordinates."""
    ratio = rect.width / rect.height
    width = long_side if ratio >= 1 else max(1, round(long_side * ratio))
    height = max(1, round(long_side / ratio)) if ratio >= 1 else long_side
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    config = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK)
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=config).draw_layout(doc.modelspace(), finalize=True)
    # MatplotlibBackend.finalize adjusts the figure; reset AFTER drawing.
    fig.set_size_inches(width / 100, height / 100, forward=True)
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(rect.min_x, rect.max_x)
    ax.set_ylim(rect.min_y, rect.max_y)
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    fig.savefig(path, dpi=100, facecolor="white", pad_inches=0)
    plt.close(fig)
    return {"width": width, "height": height, "cad_bbox": rect.to_list(), "y_axis": "CAD-up/pixel-down"}


def register(reference: np.ndarray, cad: np.ndarray, folder: Path) -> dict:
    """Estimate CAD-render to observed-image homography; always require human review."""
    scale = min(1.0, 1800 / max(reference.shape[:2]))
    ref = cv2.resize(reference, None, fx=scale, fy=scale)
    cg, rg = cv2.cvtColor(cad, cv2.COLOR_BGR2GRAY), cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(nfeatures=8000)
    candidates = []
    for mode in ["gray", "edges"]:
        a,b = (cg,rg) if mode == "gray" else (cv2.Canny(cg, 60, 150), cv2.Canny(rg, 60, 150))
        ka, da = sift.detectAndCompute(a, None)
        kb, db = sift.detectAndCompute(b, None)
        if da is None or db is None or len(db) < 2:
            continue
        pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(da, db, k=2)
        good = [x[0] for x in pairs if len(x)==2 and x[0].distance < .72*x[1].distance]
        if len(good) < 8:
            continue
        src = np.float32([ka[m.queryIdx].pt for m in good]).reshape(-1,1,2)
        dst = np.float32([kb[m.trainIdx].pt for m in good]).reshape(-1,1,2)
        h, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
        if h is None or mask is None:
            continue
        chosen = mask.ravel().astype(bool)
        if int(chosen.sum()) < 4:
            continue
        residual = np.linalg.norm(cv2.perspectiveTransform(src, h).reshape(-1,2) - dst.reshape(-1,2), axis=1)
        hull = cv2.convexHull(src[chosen].reshape(-1,2))
        coverage = float(cv2.contourArea(hull)/(cad.shape[0]*cad.shape[1]))
        corners = np.float32([[0,0],[cad.shape[1],0],[cad.shape[1],cad.shape[0]],[0,cad.shape[0]]]).reshape(-1,1,2)
        mapped = cv2.perspectiveTransform(corners,h).reshape(-1,2)
        mapped_area = abs(cv2.contourArea(mapped)) / (ref.shape[0]*ref.shape[1])
        valid = bool(chosen.sum() >= 20 and chosen.mean() >= .35 and coverage >= .15 and .005 < mapped_area < 1.5
                     and cv2.isContourConvex(mapped.astype(np.float32)) and np.isfinite(mapped).all())
        candidates.append((valid, int(chosen.sum()), coverage, h, src, dst, chosen, residual, good, ka, kb, mode, mapped_area))
    if not candidates:
        return {"status": "no_reliable_matches", "approved": False, "model": "homography", "source_resize_scale": scale}
    v,n,c,h,src,dst,chosen,res,good,ka,kb,mode,area = max(candidates, key=lambda x:(x[0],x[1],x[2]))
    result = {"status": "automatic_candidate_review_required" if v else "weak_or_degenerate_review_required", "approved": False,
              "matches":len(good), "inliers":n, "inlier_ratio":float(chosen.mean()), "cad_inlier_hull_coverage":c,
              "median_inlier_reprojection_px":float(np.median(res[chosen])), "mapped_area_fraction":area,
              "homography_cad_render_to_resized_reference":h.tolist(), "source_resize_scale":scale, "feature_mode":mode,
              "limits":"feature reprojection is not mm accuracy or proof of correct before-state correspondence"}
    marked = cv2.drawMatches(cad, ka, ref, kb, good, None, matchesMask=chosen.astype(int).tolist(),flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    cv2.imwrite(str(folder/'matches.jpg'), marked)
    if v:
        aligned = cv2.warpPerspective(ref, np.linalg.inv(h),(cad.shape[1],cad.shape[0]),borderValue=(255,255,255))
        cv2.imwrite(str(folder/'aligned-reference.jpg'),aligned)
        ae = cv2.Canny(cv2.cvtColor(aligned,cv2.COLOR_BGR2GRAY),60,150)>0
        ce = cv2.Canny(cg,60,150)>0
        overlay=np.full_like(cad,255);overlay[ae]=(255,160,0);overlay[ce]=(0,80,255);overlay[ae&ce]=(30,30,30)
        cv2.imwrite(str(folder/'alignment-overlay.png'),overlay)
    return result


def worker(candidate: dict, folder: Path, source_module: Path, converter: Path) -> dict:
    """Process only local copies, audit export/reopen, then rehash originals."""
    sys.dont_write_bytecode = True
    sys.path.insert(0,str(source_module.parent.parent.parent))
    from data_pipeline.dwg_crop import pipeline as crop
    crop.configure_odafc(converter)
    crop.configure_matplotlib_fonts()
    folder.mkdir(parents=True,exist_ok=True)
    originals=[Path(candidate['dwg']),*[Path(x) for x in candidate['references']]]
    sources=[{"path":str(p),"sha256_before":digest(p),"size":p.stat().st_size,"mtime_ns":p.stat().st_mtime_ns} for p in originals]
    refpath=originals[1]
    report={"schema":"img2dwg-pilot-sample/v1","sample_id":folder.name,"case_key":candidate['case_key'],
            "review_status":"pending","sources":sources,"reference_ambiguity":len(candidate['references'])>1,
            "status":"running","source_detector_sha256":digest(source_module)}
    try:
        shutil.copy2(originals[0],folder/'source.dwg')
        for p in originals[1:]:
            shutil.copy2(p,folder/('original-reference'+p.suffix.lower()))
        with Image.open(refpath) as im:
            raw=ImageOps.exif_transpose(im).convert('RGB'); report['input_size']=list(raw.size)
            raw.thumbnail((2000,2000));raw.save(folder/'reference.jpg',quality=92)
        doc=odafc.readfile(folder/'source.dwg',audit=False)
        full=crop.layout_rect(doc.modelspace())
        rect,confidence,reason,anchors=crop.detect_before_crop(doc.modelspace(),full)
        report['crop']={"bbox":rect.to_list(),"confidence":confidence,"reason":reason,"anchors":anchors,
                        "semantic_before_approved":False,"fallback":"left_half_fallback" in reason}
        if rect.width<=0 or rect.height<=0 or 'fixed_template_inner_frame' not in reason:
            raise ValueError('fixed_inner_frame_not_detected')
        report['source_units']=doc.header.get('$INSUNITS',0)
        doc.saveas(folder/'source.dxf')
        selected=rect.inflate(max(rect.width,rect.height)*.015)
        dimensions=[dimension_snapshot(e) for e in doc.modelspace().query('DIMENSION') if (r:=crop.entity_rect(e)) and r.intersects(selected)]
        report['render']=render(doc,rect,folder/'before-source-render.png')
        report['source_entity_count']=len(doc.modelspace())
        report['cropped_entity_count']=crop.write_cropped_dxf(doc,rect,folder/'before.dxf')
        cropped=ezdxf.readfile(folder/'before.dxf')
        report['dxf_dimensions']=dimension_compare(dimensions,[dimension_snapshot(e) for e in cropped.modelspace().query('DIMENSION')])
        odafc.export_dwg(cropped,folder/'before.dwg',version='R2018',audit=False,replace=False)
        reopened=odafc.readfile(folder/'before.dwg',audit=False)
        reopened.saveas(folder/'reopened.dxf')
        report['dwg_dimensions']=dimension_compare(dimensions,[dimension_snapshot(e) for e in reopened.modelspace().query('DIMENSION')])
        report['dwg_units']=reopened.header.get('$INSUNITS',0)
        report['units_preserved']=report['dwg_units']==report['source_units']
        report['dwg_reopened_entity_count']=len(reopened.modelspace())
        report['entity_types']=dict(collections.Counter(e.dxftype() for e in reopened.modelspace()))
        render(reopened,rect,folder/'cad-render.png')
        before=cv2.imread(str(folder/'before-source-render.png'));after=cv2.imread(str(folder/'cad-render.png'))
        report['roundtrip_render_mae']=float(np.abs(before.astype(float)-after.astype(float)).mean()) if before.shape==after.shape else None
        report['registration']=register(cv2.imread(str(folder/'reference.jpg')),after,folder)
        report['status']='extracted_review_pending'
    except Exception as exc:
        report['status']='failed';report['error_type']=type(exc).__name__;report['error']=str(exc)
        (folder/'error.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        for s in sources:
            p=Path(s['path']);s['sha256_after']=digest(p);s['unchanged']=s['sha256_before']==s['sha256_after'] and s['size']==p.stat().st_size and s['mtime_ns']==p.stat().st_mtime_ns
        report['originals_unchanged']=all(s['unchanged'] for s in sources)
        report['artifact_hashes']={p.name:digest(p) for p in folder.iterdir() if p.is_file() and p.name not in ['report.json','error.log']}
        (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def batch(args) -> None:
    """Run isolated sequential conversions with deadlines and resumable receipts."""
    data=json.loads((args.output/'discovery.json').read_text(encoding='utf-8'))
    results=[];successes=0
    for number,candidate in enumerate(data['candidates'][:args.max_attempts],1):
        folder=args.output/'samples'/f'S{number:03d}'
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'candidate.json').write_text(json.dumps(candidate,ensure_ascii=False),encoding='utf-8')
        if not (folder/'report.json').exists():
            cmd=[sys.executable,__file__,'--worker',str(folder),'--source-module',str(args.source_module),'--converter',str(args.converter)]
            try:
                with (folder/'worker.log').open('w',encoding='utf-8') as log:
                    subprocess.run(cmd,stdout=log,stderr=log,timeout=100,check=False)
            except subprocess.TimeoutExpired:
                (folder/'report.json').write_text(json.dumps({'sample_id':folder.name,'status':'failed','error_type':'WorkerTimeout','originals_unchanged':None}),encoding='utf-8')
        if (folder/'report.json').exists():
            r=json.loads((folder/'report.json').read_text());results.append(r)
            successes+=r['status']=='extracted_review_pending'
            print(json.dumps({'sample':folder.name,'status':r['status'],'extracted':successes,'dimensions':r.get('dwg_dimensions',{}).get('status'),'alignment':r.get('registration',{}).get('status')}),flush=True)
        else:
            results.append({'sample_id':folder.name,'status':'failed','error_type':'WorkerFailedWithoutReceipt','originals_unchanged':None})
        (args.output/'batch-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        if successes>=args.target:
            break


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path)
    p.add_argument('--worker',type=Path)
    p.add_argument('--source-module',type=Path,required=True)
    p.add_argument('--converter',type=Path,required=True)
    p.add_argument('--target',type=int,default=40)
    p.add_argument('--max-attempts',type=int,default=50)
    args=p.parse_args()
    if args.worker:
        worker(json.loads((args.worker/'candidate.json').read_text(encoding='utf-8')),args.worker,args.source_module,args.converter)
    else:
        batch(args)
