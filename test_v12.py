"""v1.2 single-selection, exact additions, and staged migration tests."""
import copy,json,random,tempfile,unittest
from pathlib import Path
from core import *
ROOT=Path(__file__).parent
class V12Tests(unittest.TestCase):
 def setUp(self):
  self.rows=validate(json.loads((ROOT/'defaults.json').read_text(encoding='utf-8')))
  self.v11=json.loads((ROOT/'tests/v11_defaults.json').read_text(encoding='utf-8-sig'))
 def row(self,tag):return next(r for r in self.rows if r['en']==tag and r['target']=='positive')
 def test_exact_character_groups(self):
  expected={'年齢':['early 20s','late 20s','30s','teenage'],'身長':['petite','average height','tall woman'],'体型':['slim body','average body','curvy body'],'バストサイズ':['small breasts','medium breasts','large breasts']}
  for group,tags in expected.items():
   self.assertEqual([r['en'] for r in self.rows if strict_group(r)==group],tags)
   for tag in tags:self.assertEqual(self.row(tag)['category'],group)
 def test_last_chosen_wins_and_none(self):
  selected=set()
  for group in STRICT_GROUPS:
   ids=[r['id'] for r in self.rows if strict_group(r)==group]
   for i in ids:
    selected=set_selected(self.rows,selected,i)
    self.assertEqual(set(ids)&selected,{i})
   selected=set_selected(self.rows,selected,ids[-1],False);self.assertFalse(set(ids)&selected)
  self.assertFalse(selected)
 def test_independent_groups(self):
  selected=set()
  for group in STRICT_GROUPS:
   row=next(r for r in self.rows if strict_group(r)==group);selected=set_selected(self.rows,selected,row['id'])
  self.assertEqual(len(selected),4);self.assertFalse(conflicts(self.rows,selected))
 def test_load_normalization_and_locked_priority(self):
  ids=[r['id'] for r in self.rows if strict_group(r)=='年齢']
  self.assertEqual(normalize_selection(self.rows,set(ids)),{ids[0]})
  self.assertEqual(normalize_selection(self.rows,set(ids),{ids[2]}),{ids[2]})
 def test_normalize_before_generation(self):
  ids={r['id'] for r in self.rows if strict_group(r)=='年齢'}
  positive,negative=generate(self.rows,ids,{})
  self.assertEqual(positive,'early 20s');self.assertFalse(negative)
 def test_random_normalizes_conflicting_locks(self):
  ids={r['id'] for r in self.rows if strict_group(r)=='年齢'}
  cats=[('キャラクター',g) for g in STRICT_GROUPS]
  for n in range(100):
   selected=randomize(self.rows,ids,ids,cats,random.Random(n))
   for g in STRICT_GROUPS:self.assertEqual(sum(r['id'] in selected and strict_group(r)==g for r in self.rows),1)
 def test_gradient_exact_tags_and_weight(self):
  for color in ('pink','purple'):
   row=self.row(f'black hair, {color} hair tips, gradient hair')
   self.assertEqual(row['category'],'髪色')
   hairstyle=self.row('ponytail')
   selected={row['id'],hairstyle['id']}
   self.assertFalse(conflicts(self.rows,selected))
   p,n=generate(self.rows,selected,{}, {row['id']:1.2})
   for tag in ('black hair',f'{color} hair tips','gradient hair'):self.assertIn(f'({tag}:1.2)',p)
   self.assertIn('ponytail',p);self.assertFalse(n)
 def test_all_new_clothes_multiselect(self):
  tags=['sheer camisole','sheer lace camisole','floral lace camisole','lace panties','floral lace panties','frilled panties','micro miniskirt','pleated micro miniskirt','tight micro miniskirt']
  selected=set()
  for tag in tags:selected=set_selected(self.rows,selected,self.row(tag)['id'])
  self.assertEqual(len(selected),9)
  p,n=generate(self.rows,selected,{})
  self.assertEqual(set(split_tags(p)),set(tags));self.assertFalse(n)
 def test_anime_style_distinct_weighted(self):
  row=self.row('anime style');coloring=self.row('anime coloring');self.assertNotEqual(row['id'],coloring['id'])
  p,n=generate(self.rows,{row['id'],coloring['id']},{},{row['id']:1.2});self.assertIn('(anime style:1.2)',p);self.assertIn('anime coloring',p);self.assertFalse(n)
 def test_migration_from11_only24(self):
  edited=copy.deepcopy(self.v11);removed=edited.pop(0)['id'];edited[0]['ja']='edited';removed11=next(r for r in edited if r['id'].startswith('builtin_v11_'));edited.remove(removed11)
  result=migrate_presets(edited,self.rows,11)
  self.assertEqual(len(result),len(edited)+26)
  self.assertNotIn(removed,{r['id'] for r in result});self.assertNotIn(removed11['id'],{r['id'] for r in result})
  self.assertEqual(result[0]['ja'],'edited');self.assertEqual(result,migrate_presets(result,self.rows,11))
 def test_migration12_keeps_deleted_new_items(self):
  result=migrate_presets(self.rows[:-1],self.rows,14);self.assertEqual(result,self.rows[:-1])
 def test_user_equivalent_keeps_id_and_group_rule(self):
  custom=dict(self.v11[0],id='user_age',en='30s',ja='自分の30代',group='')
  result=migrate_presets(self.v11+[custom],self.rows,11)
  self.assertEqual(sum(r['en']=='30s' for r in result),1)
  equivalent=next(r for r in result if r['en']=='30s');self.assertEqual(equivalent['id'],'user_age');self.assertEqual(strict_group(equivalent),'年齢')
 def test_same_name_same_category_not_added(self):
  new=self.row('anime style');custom=dict(new,id='user_style',en='my style')
  result=migrate_presets(self.v11+[custom],self.rows,11)
  self.assertNotIn(new['id'],{r['id'] for r in result});self.assertIn('user_style',{r['id'] for r in result})
if __name__=='__main__':unittest.main()
