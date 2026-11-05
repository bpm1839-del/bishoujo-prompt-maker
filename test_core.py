import copy, json, random, tempfile, unittest
from pathlib import Path
from core import *
ROOT=Path(__file__).parent
class CoreTests(unittest.TestCase):
 def setUp(self):
  self.rows=validate(json.loads((ROOT/'defaults.json').read_text(encoding='utf-8-sig')))
  self.old=json.loads((ROOT/'tests/v10_defaults.json').read_text(encoding='utf-8-sig'))
 def find(self,en,target='positive'):return next(r['id'] for r in self.rows if r['en']==en and r['target']==target)
 def test_catalog_and_579_preserved(self):
  self.assertEqual(len(self.rows),612)
  self.assertEqual(len(self.rows),len({(r['target'],r['en']) for r in self.rows}))
  byid={r['id']:r for r in self.rows}
  self.assertEqual(len(self.old),579)
  previous=json.loads((ROOT/'tests/v11_defaults.json').read_text(encoding='utf-8-sig'))
  self.assertEqual(len(previous),586)
  for old in previous:
   for k,v in old.items():self.assertEqual(byid[old['id']][k],v)
  for old in self.old:
   for k,v in old.items():self.assertEqual(byid[old['id']][k],v)
   self.assertEqual(byid[old['id']]['weight'],1.0)
 def test_nsfw_both_targets(self):
  selected={self.find('nsfw'),self.find('nsfw','negative')}
  self.assertTrue(any('nsfw' in w for w in conflicts(self.rows,selected)))
  self.assertEqual(generate(self.rows,selected,{}),('nsfw','nsfw'))
 def test_clothes(self):
  for tag in ('panties','camisole','lace-trimmed panties','lace-trimmed camisole','silk camisole','camisole, panties'):self.assertTrue(self.find(tag))
 def test_conflicts(self):self.assertTrue(conflicts(self.rows,{self.find('red hair'),self.find('blue hair')}))
 def test_random_lock_and_axes(self):
  locks={self.find('red hair')};cats=list(dict.fromkeys((r['tab'],r['category']) for r in self.rows))
  for n in range(50):
   selected=randomize(self.rows,locks,locks,cats,random.Random(n));self.assertTrue(locks<=selected);self.assertFalse(conflicts(self.rows,selected));self.assertNotIn(self.find('nsfw'),selected)
 def test_random_locked_absence(self):
  i=self.find('red hair');self.assertNotIn(i,randomize(self.rows,set(),{i},[('キャラクター','髪色')],random.Random(0)))
 def test_generation(self):
  p,n=generate(self.rows,{self.find('blue hair'),self.find('lowres','negative')},{'prefix':'1girl, blue hair','suffix':'best quality','negative':'lowres'})
  self.assertEqual(p.count('blue hair'),1);self.assertEqual(n,'lowres');self.assertNotIn('lowres',p)
 def test_weight_range_and_steps(self):
  for value in WEIGHT_VALUES:self.assertEqual(weight_value(str(value)),value)
  for value in (0.4,1.6,1.25,'bad',None,float('nan'),float('inf'),True):
   with self.assertRaises(ValueError):weight_value(value)
 def test_weight_positive_negative(self):
  p=self.find('blue hair');n=self.find('lowres','negative')
  self.assertEqual(generate(self.rows,{p,n},{},{p:1.2,n:0.5}),('(blue hair:1.2)','(lowres:0.5)'))
 def test_weight_model_default_override(self):
  p=self.find('masterpiece');n=self.find('lowres','negative')
  self.assertEqual(generate(self.rows,{p,n},{'suffix':'masterpiece','negative':'lowres'},{p:1.5,n:1.1}),('(masterpiece:1.5)','(lowres:1.1)'))
 def test_combination_weight_and_dedup(self):
  i=self.find('camisole, panties');p,n=generate(self.rows,{i},{},{i:1.2});self.assertEqual(p,'(camisole:1.2), (panties:1.2)')
  p,n=generate(self.rows,{i,self.find('panties')},{},{i:1.2});self.assertEqual(p.count('panties'),1)
 def test_manual_weight_compatibility(self):
  rows=[dict(self.rows[0],en='(anime style:1.2)',weight=1.0)]
  self.assertEqual(generate(rows,{rows[0]['id']},{})[0],'(anime style:1.2)')
  self.assertEqual(split_tags('(blue hair, long hair:1.2), solo'),['(blue hair, long hair:1.2)','solo'])
 def test_multiple(self):self.assertEqual(generate(self.rows,{self.find('2girls')},{'prefix':'1girl, solo'})[0],'2girls')
 def test_legacy_defaults_weights(self):
  rows=validate(copy.deepcopy(self.old));self.assertTrue(all(r['weight']==1.0 for r in rows))
 def test_migration_user_edit_delete_preserved(self):
  old=copy.deepcopy(self.old);removed=old.pop(1)['id'];old[0]['ja']='ユーザー編集';old.append(dict(old[0],id='user123',en='my tag'))
  migrated=migrate_presets(old,self.rows)
  self.assertEqual(len(migrated),len(old)+33);self.assertNotIn(removed,{r['id'] for r in migrated});self.assertEqual(migrated[0]['ja'],'ユーザー編集');self.assertIn('user123',{r['id'] for r in migrated})
  self.assertEqual(migrated,migrate_presets(migrated,self.rows))
 def test_migration_existing_user_equivalent(self):
  old=copy.deepcopy(self.old);old.append(dict(old[0],id='my_panties',en='panties'))
  migrated=migrate_presets(old,self.rows);self.assertEqual(sum(r['en']=='panties' for r in migrated),1);self.assertIn('my_panties',{r['id'] for r in migrated})
 def test_persistence(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'data.json';atomic_save(path,{'日本語':self.rows});self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['日本語'],self.rows);atomic_save(path,[]);self.assertEqual(json.loads(path.read_text()),[])
 def test_invalid(self):
  for rows in ([{}],self.rows+[self.rows[0]],[dict(self.rows[0],weight=1.25)]):
   with self.assertRaises(ValueError):validate(rows)
if __name__=='__main__':unittest.main()
