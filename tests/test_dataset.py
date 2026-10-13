"""Dataset guarantees: case authority, immutable copies, native roots, split identity."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ezdxf
from PIL import Image
from prepare_dataset import collect_one,digest,geometry_group,native_components
from package_dataset import group_records
from build_pilot import dimension_snapshot,dimension_compare


class DatasetTests(unittest.TestCase):
    def test_materialized_style_defaults_equal_but_real_scale_changes_fail(self):
        doc=ezdxf.new('R2018');dim=doc.modelspace().add_linear_dim(base=(0,4),p1=(0,0),p2=(10,0)).dimension
        style=doc.dimstyles.get(dim.dxf.dimstyle)
        for key in ['dimlfac','dimalt','dimrnd']:style.dxf.discard(key)
        expected=dimension_snapshot(dim)
        style.dxf.dimlfac=1;style.dxf.dimalt=0;style.dxf.dimrnd=0
        self.assertEqual(dimension_compare([expected],[dimension_snapshot(dim)])['status'],'pass')
        style.dxf.dimlfac=2
        self.assertEqual(dimension_compare([expected],[dimension_snapshot(dim)])['status'],'fail')

    def test_collection_uses_same_case_without_feature_match_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'original';source.mkdir();cad=source/'변경전후.dwg';cad.write_bytes(b'AC1032-fixture')
            image=source/'준공도면.jpg';Image.new('RGB',(32,48),'white').save(image)
            before=[digest(cad),digest(image)];candidate={'case_key':'fixture','dwg':str(cad),'references':[str(image)]}
            r=collect_one(candidate,root/'run');self.assertEqual(r['status'],'collected');self.assertTrue(r['originals_unchanged'])
            self.assertEqual(r['pair_authority'],'user-confirmed-same-work-request-folder');self.assertEqual(before,[digest(cad),digest(image)])
            self.assertEqual(collect_one(candidate,root/'run')['exact_pair_sha256'],r['exact_pair_sha256'])

    def test_mirror_geometry_group_and_split_identity(self):
        a=ezdxf.new();b=ezdxf.new()
        segments=[((0,0),(10,0)),((10,0),(10,20)),((10,20),(5,20))]
        for start,end in segments:
            a.modelspace().add_line(start,end);b.modelspace().add_line((100-start[0],200+start[1]),(100-end[0],200+end[1]))
        self.assertEqual(geometry_group(a),geometry_group(b))
        records=[{'sample_id':'A','image_sha256':'same-image','dwg_sha256':'one','geometry_group_sha256':'g1'},
                 {'sample_id':'B','image_sha256':'same-image','dwg_sha256':'two','geometry_group_sha256':'g2'},
                 {'sample_id':'C','image_sha256':'other','dwg_sha256':'two','geometry_group_sha256':'g3'}]
        grouped=group_records(records);self.assertEqual(len({x['group_id'] for x in grouped}),1);self.assertEqual(len({x['split'] for x in grouped}),1)

    def test_native_dimension_remains_one_component_with_picture_dependency(self):
        doc=ezdxf.new('R2018');msp=doc.modelspace();d=msp.add_linear_dim(base=(0,4),p1=(0,0),p2=(10,0));d.render()
        def to_json(v):
            if hasattr(v,'x'):return list(v)
            if isinstance(v,dict):return {k:to_json(x) for k,x in v.items()}
            if isinstance(v,(tuple,list)):return [to_json(x) for x in v]
            return v
        ir=native_components(doc,lambda e:{},to_json);self.assertEqual(len(ir['entities']),1);self.assertEqual(len(ir['native_components']),1)
        self.assertEqual(ir['native_components'][0]['type'],'native_dimension');self.assertEqual(ir['native_components'][0]['parameters']['measurement'],10)
        self.assertTrue(ir['block_definitions']);self.assertTrue(ir['entities'][0]['raw_dxf_tags']);json.dumps(ir,allow_nan=False)


if __name__=='__main__':unittest.main()
