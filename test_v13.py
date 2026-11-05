import copy,json,unittest
from pathlib import Path
from core import preset_prompt,generate
from prompt_help import *
ROOT=Path(__file__).parent
class V13Tests(unittest.TestCase):
 def setUp(self):
  self.rows=json.loads((ROOT/'defaults.json').read_text(encoding='utf-8-sig'))
  self.index=TranslationIndex(self.rows,{'semi-realistic':'セミリアル','detailed eyes':'繊細な瞳'})
 def row(self,en,target='positive'):return next(r for r in self.rows if r['en']==en and r['target']==target)
 def translate(self,text,needle,target='positive'):
  spans=prompt_spans(text);tag=tag_at(spans,text.index(needle));self.assertIsNotNone(tag);return self.index.lookup(tag,target)
 def test_copy_every_preset_matches_generation(self):
  for row in self.rows:
   for w in (0.5,1.0,1.2,1.5):
    result=preset_prompt(row,w);generated=generate([row],{row['id']},{},{row['id']:w})
    self.assertEqual(result,generated[0 if row['target']=='positive' else 1]);self.assertFalse(result.startswith(','));self.assertFalse(result.endswith(','));self.assertNotIn('\n',result)
 def test_copy_no_input_mutation(self):
  row=self.row('soft lighting');old=copy.deepcopy(row);self.assertEqual(preset_prompt(row,1.2),'(soft lighting:1.2)');self.assertEqual(row,old)
 def test_copy_combination(self):
  row=self.row('black hair, pink hair tips, gradient hair');self.assertEqual(preset_prompt(row,1.2),'(black hair:1.2), (pink hair tips:1.2), (gradient hair:1.2)')
 def test_default_translation(self):self.assertEqual(self.translate('masterpiece, soft lighting','soft'),self.row('soft lighting')['ja'])
 def test_negative_translation(self):self.assertEqual(self.translate('lowres, worst quality','lowres','negative'),self.row('lowres','negative')['ja'])
 def test_numeric_weight(self):self.assertEqual(self.translate('(semi-realistic:1.2)','semi'),'セミリアル（強調度1.2）')
 def test_nested_weights(self):self.assertEqual(self.translate('((soft lighting:1.2):1.1)','soft'),'柔らかい光（強調度1.32）')
 def test_comma_in_group(self):
  text='(masterpiece, soft lighting:1.2), detailed eyes'
  self.assertEqual(self.translate(text,'soft'),'柔らかい光（強調度1.2）');self.assertEqual(self.translate(text,'detailed'),'繊細な瞳')
  self.assertIsNone(tag_at(prompt_spans(text),text.index(',')))
 def test_newlines(self):
  text='masterpiece,\n(soft lighting:1.2)\ndetailed eyes';self.assertEqual(len(prompt_spans(text)),3);self.assertEqual(self.translate(text,'soft'),'柔らかい光（強調度1.2）')
 def test_unknown(self):self.assertEqual(self.translate('new_unknown_xyz','unknown'),'日本語訳未登録')
 def test_unbalanced(self):
  text='(unfinished, soft lighting, [broken';self.assertEqual(self.translate(text,'soft'),'柔らかい光');self.assertEqual(len(prompt_spans(text)),3)
 def test_escaped_punctuation(self):
  text=r'foo\,bar, name \(series\), (soft lighting:1.2)';spans=prompt_spans(text);self.assertEqual(len(spans),3);self.assertEqual(spans[0].text,r'foo\,bar');self.assertEqual(self.translate(text,'soft'),'柔らかい光（強調度1.2）')
  self.assertFalse(prompt_spans(r'(foo\:1.2)')[0].weighted)
 def test_schedule_and_lora_unknown(self):
  for text in ('[a:b:0.5]','<lora:test:0.8>'):self.assertEqual(self.translate(text,text),'日本語訳未登録')
 def test_duplicate_priority_and_extra_fallback(self):
  row=self.row('soft lighting');rows=[dict(row,id='a',ja='先頭'),dict(row,id='b',ja='後ろ'),dict(row,id='n',target='negative',ja='Negative名')]
  index=TranslationIndex(rows,{'soft lighting':'辞書訳'})
  tag=prompt_spans('soft lighting')[0];self.assertEqual(index.lookup(tag,'positive'),'先頭');self.assertEqual(index.lookup(tag,'negative'),'Negative名')
 def test_exact_beats_composite_fragment(self):
  self.assertEqual(self.translate('black hair','black'),self.row('black hair')['ja'])
  self.assertIn('複合プリセットの一部',self.translate('pink hair tips','pink'))
 def test_edit_rebuild_translation(self):
  rows=copy.deepcopy(self.rows);row=next(r for r in rows if r['en']=='soft lighting');row['ja']='新しい日本語';self.index.rebuild(rows);self.assertEqual(self.translate('soft lighting','soft'),'新しい日本語')
 def test_deep_nesting_does_not_crash(self):self.assertTrue(prompt_spans('('*1000+'soft lighting'+')'*1000))
 def test_long_prompt_positions(self):
  text=('masterpiece, '*2000)+'(soft lighting:1.2)';spans=prompt_spans(text);tag=tag_at(spans,text.index('soft'));self.assertEqual(tag.text,'soft lighting')
 def test_popup_clamp(self):
  for x,y in ((0,0),(1919,1079),(-200,500),(500,2000)):
   px,py=popup_position(x,y,320,100,(0,0,1920,1080));self.assertTrue(0<=px<=1600 and 0<=py<=980)
 def test_dictionary_validation(self):
  for bad in ([],{'tag':1},{'':'x'}):
   with self.assertRaises(ValueError):validate_translations(bad)
if __name__=='__main__':unittest.main()
