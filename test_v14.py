import copy,json,unittest
from pathlib import Path
from core import *
from features import *
ROOT=Path(__file__).parent
class V14Tests(unittest.TestCase):
 def setUp(self):self.rows=json.loads((ROOT/'defaults.json').read_text(encoding='utf-8'))
 def row(self,en):return next(r for r in self.rows if r['en']==en and r['target']=='positive')
 def test_preserve_v13_and_new_entries(self):
  old=json.loads((ROOT/'tests/v13_defaults.json').read_text(encoding='utf-8-sig'));byid={r['id']:r for r in self.rows}
  self.assertEqual(len(self.rows),612)
  for r in old:self.assertEqual(byid[r['id']],r)
  self.assertEqual(strict_group(self.row('teenage')),'年齢');self.assertEqual(self.row('all fours')['category'],'姿勢')
 def test_colors_coat_black_shirt_red(self):
  coat=self.row('coat');shirt=self.row('shirt');colors={coat['id']:{'coat':'black'},shirt['id']:{'shirt':'red'}}
  p,n=generate(self.rows,{coat['id'],shirt['id']},{},{},colors);self.assertEqual(p,'red shirt, black coat');self.assertFalse(n)
  self.assertFalse(conflicts(self.rows,{coat['id'],shirt['id']}))
 def test_colored_weight_copy(self):
  coat=self.row('coat');colors={coat['id']:{'coat':'black'}};self.assertEqual(preset_prompt(coat,1.2,colors),'(black coat:1.2)')
 def test_composite_per_piece(self):
  row=self.row('camisole, panties');colors={row['id']:{'camisole':'white','panties':'black'}}
  self.assertEqual(preset_prompt(row,1.2,colors),'(white camisole:1.2), (black panties:1.2)')
 def test_replace_embedded_color(self):
  row=self.row('white shirt');self.assertEqual(preset_prompt(row,1.0,{row['id']:{'white shirt':'red'}}),'red shirt')
 def test_none_no_mutation(self):
  rows=copy.deepcopy(self.rows);row=self.row('coat');self.assertEqual(preset_prompt(row,1.0,{row['id']:{'coat':''}}),'coat');colorize_rows(self.rows,{row['id']:{'coat':'black'}});self.assertEqual(self.rows,rows)
 def test_colors_only_positive_clothing(self):
  for row in self.rows:
   if row['target']=='negative' or row['tab']!='衣装' or row['category']=='服の色':self.assertFalse(garment_parts(row))
 def test_sizes_valid_and_ratios(self):
  for plan in SIZES.values():
   if plan is None:continue
   fw,fh,w,h=plan
   self.assertTrue(all(n%8==0 for n in plan));self.assertLessEqual(w*h,1024*1024);self.assertAlmostEqual(fw/fh,w/h,places=6)
 def test_hint(self):self.assertIn('1.5倍',wallpaper_hint('FHD 1920×1080',1280,720));self.assertIn('入力',wallpaper_hint('FHD 1920×1080','',0))
 def test_color_validation(self):
  for bad in ([],{'x':[]},{'x':{'coat':'unknown'}},{'x':{'coat':[]}}):
   with self.assertRaises(ValueError):validate_colors(bad)
 def test_migration_only_new14(self):
  old=json.loads((ROOT/'tests/v13_defaults.json').read_text(encoding='utf-8-sig'));old.pop(0);old[0]['ja']='edited';result=migrate_presets(old,self.rows,12);self.assertEqual(len(result),len(old)+2);self.assertEqual(result[0]['ja'],'edited')
 def test_teen_single_selection(self):
  adult=self.row('early 20s');teen=self.row('teenage');selected=set_selected(self.rows,{adult['id']},teen['id']);self.assertEqual(selected,{teen['id']});self.assertFalse(self.row('teenage')['randomizable'])
if __name__=='__main__':unittest.main()
