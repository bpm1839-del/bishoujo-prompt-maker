"""Additional v1.2 real-widget and v1.1 migration checks, isolated storage."""
import copy,json,os,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).parent

def main():
 with tempfile.TemporaryDirectory() as d:
  os.environ['BPM_DATA_DIR']=d
  import app
  from core import STRICT_GROUPS,strict_group
  app.DATA=Path(d);errors=[]
  def open_app():
   a=app.App();a.withdraw();a.report_callback_exception=lambda *args:errors.append(args);a.update();return a
  def row(a,en):return next(r for r in a.rows if r['en']==en and r['target']=='positive')
  def dialog(a):return next(w for w in a.winfo_children() if w.winfo_class()=='Toplevel')
  a=open_app();key=('positive','キャラクター');tree=a.views[key][0]
  assert all(var.get()=='指定なし' for var,box in a.character_choices.values())
  assert a.geometry().split('+')[0]=='1260x820'
  # All four independent selectors: selecting replaces, clearing does not touch the other groups.
  for group in STRICT_GROUPS:
   var,box=a.character_choices[group]
   for index in (1,2,3):
    box.current(index);box.event_generate('<<ComboboxSelected>>');a.update()
    assert sum(r['id'] in a.selected and strict_group(r)==group for r in a.rows)==1
   assert var.get()!='指定なし'
  assert len(a.selected)==4
  for group in STRICT_GROUPS:
   box=a.character_choices[group][1];box.current(0);a.choose_character(group)
  assert not a.selected
  # Keyboard toggles and bulk selection also obey exclusivity.
  ids=[r['id'] for r in a.rows if strict_group(r)=='年齢']
  tree.selection_set(ids[0]);a.toggle(key);tree.selection_set(ids[1]);a.toggle(key);assert set(ids)&a.selected=={ids[1]}
  a.cats[key].set('年齢');a.refresh();a.bulk(key,True);assert len(set(ids)&a.selected)==1
  a.bulk(key,False);assert not set(ids)&a.selected;a.cats[key].set('すべて');a.refresh()
  # Real click on the checkbox column (visible Tk window only during this check).
  a.deiconify();a.update()
  for i in ids[:2]:
   tree.see(i);a.update();bounds=tree.bbox(i,'s');assert bounds
   x,y,w,h=bounds;tree.event_generate('<Button-1>',x=x+5,y=y+h//2);a.update()
  assert set(ids)&a.selected=={ids[1]}
  a.withdraw()
  # New composite hair preset and distinct hairstyle with a single per-preset weight.
  gradient=row(a,'black hair, purple hair tips, gradient hair')['id'];style=row(a,'anime style')['id']
  a.search.set('黒から紫');a.update();assert tree.get_children()==(gradient,);a.search.set('')
  tree.selection_set(gradient);a.update();a.weight_inputs[key].set('1.3');a.apply_weight(key)
  a.selected={gradient,row(a,'ponytail')['id'],style};a.weights[style]=1.2
  for tag in ['sheer camisole','sheer lace camisole','floral lace camisole','lace panties','floral lace panties','frilled panties','micro miniskirt','pleated micro miniskirt','tight micro miniskirt']:a.selected.add(row(a,tag)['id'])
  a.make();p=a.texts[0].get('1.0','end');n=a.texts[1].get('1.0','end');assert '(anime style:1.2)' in p
  for tag in ['black hair','purple hair tips','gradient hair']:assert f'({tag}:1.3)' in p and tag not in n
  assert 'floral lace panties' in p and 'floral lace panties' not in n
  a.favorite.set('Ver1.2セット');a.fav_save();assert a.save();a.destroy()
  a=open_app();assert a.weights[gradient]==1.3 and a.weights[style]==1.2;a.favorite.set('Ver1.2セット');a.fav_load();assert style in a.selected and a.weights[style]==1.2
  # Duplicate Japanese name in same category is rejected, rather than overwriting.
  stylekey=('positive','画質・生成設定');a.views[stylekey][0].selection_set(style);a.edit(stylekey,'copy');a.update();win=dialog(a);entry=win.grid_slaves(row=3,column=1)[0];entry.delete(0,'end');entry.insert(0,'different anime tag')
  count=len(a.rows)
  with patch('app.messagebox.showerror') as error:win.grid_slaves(row=7,column=1)[0].invoke();error.assert_called_once()
  assert len(a.rows)==count;win.destroy();a.destroy();assert not errors,errors
 with tempfile.TemporaryDirectory() as d:
  app.DATA=Path(d)
  old=json.loads((ROOT/'tests/v11_defaults.json').read_text(encoding='utf-8-sig'))
  deleted=next(r for r in old if r['en']=='camisole, panties');old.remove(deleted);old[0]['ja']='既存の編集を維持'
  custom=dict(old[0],id='user_v11',ja='独自スタイル',en='custom style',weight=1.4);old.append(custom)
  state=dict(schema_version=2,selected=[old[0]['id'],custom['id']],locks=[custom['id']],model='カスタムモデル',positive='edited v11 positive',negative='edited v11 negative',settings={'width':'1024','height':'1024','cfg':'6.5','steps':'32','seed':'123','sampler':'Euler a'},weights={custom['id']:1.3},random_categories=['髪色'])
  files={'presets.json':old,'catalog.json':{'version':11,'keep':'metadata'},'session.json':state,'favorites.json':{'v11お気に入り':state},'models.json':{'カスタムモデル':{'prefix':'1girl','suffix':'custom suffix','negative':'custom negative'}}}
  for name,value in files.items():(Path(d)/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
  before={name:(Path(d)/name).read_bytes() for name in files}
  a=open_app();assert len(a.rows)==len(old)+26;assert a.rows[0]['ja']=='既存の編集を維持';assert deleted['id'] not in {r['id'] for r in a.rows};assert a.weights[custom['id']]==1.3
  assert a.selected==set(state['selected']) and a.locks==set(state['locks']);assert a.model.get()=='カスタムモデル';assert a.settings['seed'].get()=='123'
  assert a.texts[0].get('1.0','end-1c')==state['positive']
  # Opening v1.2 must not modify or initialize any v1.1 JSON.
  assert all((Path(d)/name).read_bytes()==data for name,data in before.items())
  a.favorite.set('v11お気に入り');a.fav_load();assert a.weights[custom['id']]==1.3
  assert a.save()
  for name in ('presets.json','session.json','models.json','catalog.json'):assert (Path(d)/(name+'.pre-v1.4.bak')).read_bytes()==before[name]
  marker=json.loads((Path(d)/'catalog.json').read_text(encoding='utf-8'));assert marker=={'version':14,'keep':'metadata'}
  new=row(a,'anime style')['id'];stylekey=('positive','画質・生成設定');a.views[stylekey][0].selection_set(new)
  with patch('app.messagebox.askyesno',return_value=True):a.delete(stylekey)
  a.destroy();a=open_app();assert new not in {r['id'] for r in a.rows};assert custom['id'] in a.selected;a.destroy();assert not errors,errors
 print('V1.2 GUI PASS: four exclusive groups, unspecified, dropdowns/click/Space/bulk, gradients, all clothes, anime weight, favorites/restart, duplicate names, v1.1 migration without startup writes, backups and deletion persistence')
if __name__=='__main__':main()
