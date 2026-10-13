"""Guard against dimension loss, misleading empty passes and coordinate drift."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ezdxf,cv2,numpy as np
from PIL import Image
from build_pilot import dimension_snapshot,dimension_compare,render,register
from discover_pilot import discover
from audit_cad import audit_file


class PilotTests(unittest.TestCase):
    def test_dimension_loss_and_style_change(self):
        doc=ezdxf.new('R2018')
        dim=doc.modelspace().add_linear_dim(base=(0,4),p1=(0,0),p2=(10,0),dimstyle='Standard').dimension
        before=dimension_snapshot(dim)
        self.assertEqual(dimension_compare([before],[before])['status'],'pass')
        self.assertEqual(dimension_compare([before],[])['status'],'fail')
        doc.dimstyles.get('Standard').dxf.dimlfac=2
        self.assertEqual(dimension_compare([before],[dimension_snapshot(dim)])['status'],'fail')

    def test_no_dimensions_is_not_pass(self):
        self.assertEqual(dimension_compare([],[])['status'],'not_applicable_no_dimensions')

    def test_header_handseed_is_not_duplicate_entity(self):
        doc=ezdxf.new('R2018');entity=doc.modelspace().add_line((0,0),(10,0))
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'seed.dxf';doc.saveas(p);lines=p.read_text().splitlines()
            at=next(i for i,v in enumerate(lines) if v.strip()=='$HANDSEED');lines[at+2]=entity.dxf.handle;p.write_text('\n'.join(lines)+'\n')
            r=audit_file(p);self.assertEqual(r['duplicate_entity_handle_groups'],0);self.assertTrue(r['handseed_matches_existing_handle'])

    def test_dimstyle_arrow_name_is_not_entity_handle(self):
        doc=ezdxf.new('R12');doc.dimstyles.new('A',dxfattribs={'dimblk':'CLOSED'});doc.dimstyles.new('B',dxfattribs={'dimblk':'CLOSED'})
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'styles.dxf';doc.saveas(p);self.assertEqual(audit_file(p)['duplicate_entity_handle_groups'],0)

    def test_viewport_resolution_after_backend_finalize(self):
        doc=ezdxf.new('R2018');doc.modelspace().add_line((0,0),(10,20))
        class Box:
            min_x,min_y,max_x,max_y=-1,-1,11,21
            width,height=12,22
            def to_list(self):return [-1,-1,11,21]
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'render.png';r=render(doc,Box(),p)
            with Image.open(p) as im:self.assertEqual(im.size,(r['width'],r['height']))

    def test_registration_known_transform(self):
        rng=np.random.default_rng(42);cad=np.full((600,800,3),255,np.uint8)
        for _ in range(150):
            x,y=map(int,rng.integers([20,20],[740,550]));cv2.rectangle(cad,(x,y),(x+int(rng.integers(4,30)),y+int(rng.integers(4,25))),(0,0,0),2)
        h=np.float64([[.85,.06,32],[-.02,.88,42],[.0001,.00004,1]])
        ref=cv2.warpPerspective(cad,h,(800,600),borderValue=(255,255,255))
        with tempfile.TemporaryDirectory() as t:
            r=register(ref,cad,Path(t));self.assertEqual(r['status'],'automatic_candidate_review_required');self.assertLess(r['median_inlier_reprojection_px'],1);self.assertFalse(r['approved'])

    def test_discovery_exact_names_immediate_children_only(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);a=root/'a';b=root/'b';c=root/'c'
            for f in [a,b,c]:f.mkdir()
            for f in [a,b]: (f/'변경전후.dwg').write_bytes(b'fixture')
            (a/'준공도면.jpg').write_bytes(b'fixture');(b/'준공도면 (2).jpg').write_bytes(b'fixture')
            child=c/'nested';child.mkdir();(child/'변경전후.dwg').write_bytes(b'fixture');(child/'준공도면.jpg').write_bytes(b'fixture')
            index=root/'index.json';index.write_text(json.dumps({'count':3,'folders':[{'path':str(f)} for f in [a,b,c]]}),encoding='utf-8')
            r=discover(index,root/'out',60,100);self.assertEqual(r['candidate_count'],1)
            self.assertEqual((a/'변경전후.dwg').read_bytes(),b'fixture')


if __name__=='__main__':unittest.main()
