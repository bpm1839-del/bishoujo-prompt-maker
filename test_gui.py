"""Real Tk widgets with isolated v1.0/v1.1 JSON. Does not read user data."""
import copy, json, os, tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).parent

def main():
 with tempfile.TemporaryDirectory() as d:
  os.environ['BPM_DATA_DIR']=d
  import app
  from app import App
  app.DATA=Path(d)
  errors=[]
  def open_app():
   a=App();a.withdraw();a.report_callback_exception=lambda *args:errors.append(args);a.update();return a
  def row(a,en,target='positive'):return next(r for r in a.rows if r['en']==en and r['target']==target)
  def dialog(a):return next(w for w in a.winfo_children() if w.winfo_class()=='Toplevel')
  def fill(win,n,value):
   e=win.grid_slaves(row=n,column=1)[0]
   if e.winfo_class() in ('TCombobox','TSpinbox'):e.set(value)
   else:e.delete(0,'end');e.insert(0,value)
  key=('positive','キャラクター');negative=('negative','画質・生成設定')
  a=open_app();assert len(a.nb.tabs())==2 and len(a.views)==10
  assert len(a.rows)==612 and not a.selected
  for (target,tab),(tree,cb) in a.views.items():
   assert all(next(r for r in a.rows if r['id']==i)['target']==target for i in tree.get_children())
  nsfw={row(a,'nsfw')['id'],row(a,'nsfw','negative')['id']};a.selected=nsfw;a.refresh();a.update();assert 'nsfw' in a.warning.get('1.0','end')
  a.make();assert 'nsfw' in a.texts[0].get('1.0','end') and 'nsfw' in a.texts[1].get('1.0','end')
  # Both target weights, including an item also present in model defaults.
  p=row(a,'blue hair')['id'];n=row(a,'lowres','negative')['id'];a.selected={p,n}
  a.views[key][0].selection_set(p);a.update();a.weight_inputs[key].set('1.2');a.apply_weight(key)
  a.views[negative][0].selection_set(n);a.update();a.weight_inputs[negative].set('0.5');a.apply_weight(negative)
  a.make();a.update();assert '(blue hair:1.2)' in a.texts[0].get('1.0','end');assert '(lowres:0.5)' in a.texts[1].get('1.0','end')
  a.copy_text(a.texts[0]);assert 'blue hair' in a.clipboard_get()
  a.texts[0].insert('end',', custom test');a.update();assert a.dirty
  before=a.texts[0].get('1.0','end')
  with patch('app.messagebox.askyesno',return_value=False) as ask:a.make();assert a.texts[0].get('1.0','end')==before;ask.assert_called_once()
  assert a.save();a.favorite.set('新お気に入り');a.fav_save();a.weights[p]=1.5;a.fav_load();assert a.weights[p]==1.2 and a.weights[n]==0.5
  a.search.set('blue hair');a.update();assert p in a.views[key][0].get_children() and len(a.views[key][0].get_children())<10;a.search.set('')
  a.locks={p};a.roll();assert p in a.selected and a.weights[p]==1.2
  # Add to Negative directly, then change target via edit and duplicate.
  count=len(a.rows);a.edit(negative,'add');a.update();win=dialog(a)
  for index,value in [(1,'テストカテゴリ'),(2,'テスト項目'),(3,'custom_gui_tag'),(6,'1.3')]:fill(win,index,value)
  assert win.grid_slaves(row=4,column=1)[0].get()=='negative';win.grid_slaves(row=7,column=1)[0].invoke();a.update()
  custom=a.rows[-1]['id'];assert a.rows[-1]['weight']==1.3 and a.views[negative][0].exists(custom)
  a.views[negative][0].selection_set(custom);a.edit(negative,'edit');a.update();win=dialog(a);fill(win,4,'positive');win.grid_slaves(row=7,column=1)[0].invoke();a.update()
  moved=('positive','画質・生成設定');assert not a.views[negative][0].exists(custom) and a.views[moved][0].exists(custom)
  a.views[moved][0].selection_set(custom);a.edit(moved,'copy');a.update();win=dialog(a);fill(win,3,'custom_gui_copy');fill(win,2,'テスト複製');win.grid_slaves(row=7,column=1)[0].invoke();a.update();assert len(a.rows)==count+2
  ids=[r['id'] for r in a.rows if r['en'].startswith('custom_gui')];a.views[moved][0].selection_set(*ids)
  with patch('app.messagebox.askyesno',return_value=True):a.delete(moved)
  assert len(a.rows)==count
  a.destroy();b=open_app();assert b.weights[p]==1.2 and b.weights[n]==0.5;assert 'custom test' in b.texts[0].get('1.0','end');assert '新お気に入り' in b.favorites
  # Deleting a new built-in remains deleted on subsequent startup.
  new=row(b,'panties')['id'];b.views[('positive','衣装')][0].selection_set(new)
  with patch('app.messagebox.askyesno',return_value=True):b.delete(('positive','衣装'))
  b.destroy();b=open_app();assert new not in {r['id'] for r in b.rows}
  with patch('app.messagebox.askyesno',return_value=True):b.reset()
  assert len(b.rows)==612 and all(v==1.0 for v in b.weights.values());b.destroy()
  assert not errors,errors
 with tempfile.TemporaryDirectory() as d:
  # Actual v1.0 shapes: no weights, edited/deleted defaults, one user preset.
  app.DATA=Path(d);old=json.loads((ROOT/'tests/v10_defaults.json').read_text(encoding='utf-8-sig'));removed=old.pop(1)['id'];old[0]['ja']='旧編集';old.append(dict(old[0],id='user1',en='legacy custom'))
  state=dict(selected=[old[0]['id'],'user1'],locks=['user1'],model='Animagine XL 3.1',positive='manually edited positive',negative='manually edited negative',settings={'width':'1024'},random_categories=['髪色'])
  for name,data in [('presets.json',old),('session.json',state),('favorites.json',{'旧お気に入り':state})]:(Path(d)/name).write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
  original=(Path(d)/'presets.json').read_bytes();a=open_app()
  assert a.rows[0]['ja']=='旧編集' and removed not in {r['id'] for r in a.rows};assert a.selected==set(state['selected']);assert a.locks=={'user1'};assert all(v==1.0 for v in a.weights.values());assert a.settings['width'].get()=='1024'
  a.weights['user1']=1.4;a.favorite.set('旧お気に入り');a.fav_load();assert a.weights['user1']==1.0;assert a.texts[0].get('1.0','end-1c')==state['positive']
  assert a.save();assert (Path(d)/'presets.json.pre-v1.4.bak').read_bytes()==original
  a.destroy();a=open_app();assert 'user1' in a.selected;assert len(a.rows)==len(old)+33;a.destroy()
  assert not errors,errors
 print('GUI PASS: target tabs, weights, nsfw, clipboard, favorites, overwrite protection, CRUD, random locks, restart, reset, v1.0 migration and backups')
if __name__=='__main__':main()

