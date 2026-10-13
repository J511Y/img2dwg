"""Distinguish component definitions, active instances, and dimension pictures."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ezdxf
from analyze_cad_components import analyze,digest


class ComponentInventoryTests(unittest.TestCase):
    def test_dimension_picture_is_not_extra_modelspace_lines(self):
        doc=ezdxf.new('R2018');msp=doc.modelspace();msp.add_line((0,0),(10,0))
        dim=msp.add_linear_dim(base=(0,4),p1=(0,0),p2=(10,0));dim.render()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fixture.dxf';doc.saveas(path);before=digest(path);r=analyze(path)
            self.assertEqual(r['entity_types'],{'LINE':1,'DIMENSION':1})
            self.assertEqual(len(r['dimensions']),1)
            self.assertTrue(r['dimensions'][0]['picture_block_exists'])
            self.assertEqual(before,digest(path))

    def test_unused_definition_is_not_an_active_component(self):
        doc=ezdxf.new('R2018');child=doc.blocks.new('CHILD');child.add_circle((0,0),2)
        parent=doc.blocks.new('PARENT');parent.add_blockref('CHILD',(0,0))
        unused=doc.blocks.new('UNUSED');unused.add_line((0,0),(4,0))
        doc.modelspace().add_blockref('PARENT',(10,20),dxfattribs={'rotation':90,'xscale':2,'yscale':2})
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fixture.dxf';doc.saveas(path);r=analyze(path)
            blocks={b['name']:b for b in r['blocks']}
            self.assertTrue(blocks['CHILD']['reachable_by_insert_or_dimension'])
            self.assertFalse(blocks['UNUSED']['reachable_by_insert_or_dimension'])
            self.assertEqual(blocks['PARENT']['direct_modelspace_insert_count'],1)
            self.assertEqual(len(r['inserts']),1)
            self.assertEqual(r['inserts'][0]['scale'],[2,2,1])


if __name__=='__main__':unittest.main()
