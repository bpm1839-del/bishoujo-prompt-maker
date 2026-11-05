"""Isolated real Tk GUI checks for the accepted v1.4 changes."""
import copy,json,os,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).parent

def main():
 with tempfile.TemporaryDirectory() as d:
  os.environ['BPM_DATA_DIR']=d
  import app
  app.DATA=Path(d);a=app.App();errors=[];a.report_callback_exception=lambda *args:errors.append(args);a.update()
  def row(en):return next(r for r in a.rows if r['en']==en and r['target']=='positive')
  key=('positive','衣装');tree=a.views[key][0]
  coat=row('coat');shirt=row('shirt');oldcolor=row('black clothes')
  assert not tree.exists(oldcolor['id']);assert '服の色' not in a.views[key][1]['values'];assert all(r in a.rows for r in [coat,shirt,oldcolor])
  assert a.character_choices['年齢'][1]['values'][1]=='10代';assert a.character_choices['年齢'][0].get()=='指定なし'
  a.character_choices['年齢'][1].current(1);a.choose_character('年齢');assert row('teenage')['id'] in a.selected;a.undo_selection();assert row('teenage')['id'] not in a.selected
  a.selected={coat['id'],shirt['id']};a.refresh();a.set_texts('keep edited text','keep negative');a.update()
  a.edit_colors();a.update();win=next(w for w in a.winfo_children() if w.winfo_class()=='Toplevel')
  a.color_dialog_vars[(coat['id'],'coat')].set('黒');a.color_dialog_vars[(shirt['id'],'shirt')].set('赤')
  def descendants(w):
   for c in w.winfo_children():yield c;yield from descendants(c)
  apply=next(w for w in descendants(win) if w.winfo_class()=='TButton' and w.cget('text')=='適用');apply.invoke();a.update()
  assert a.clothing_colors[coat['id']]['coat']=='black';a.copy_preset(coat['id']);assert a.clipboard_get()=='black coat';a.make();a.update();assert 'black coat' in a.texts[0].get('1.0','end');assert 'red shirt' in a.texts[0].get('1.0','end')
  a.only_selected.set(True);a.refresh();assert set(tree.get_children())==a.selected
  tree.selection_set(coat['id']);a.toggle(key);assert not tree.exists(coat['id']);a.undo_selection();assert tree.exists(coat['id']) and a.clothing_colors[coat['id']]['coat']=='black';a.only_selected.set(False);a.refresh()
  # Legacy data remains accessible without appearing by default.
  a.show_legacy_colors.set(True);a.refresh();assert tree.exists(oldcolor['id']);a.show_legacy_colors.set(False);a.refresh()
  # Wallpaper actions preserve ratio, are undoable, and reuse existing placement tags.
  for name,plan in app.SIZES.items():
   if plan is None:continue
   a.wallpaper_size.set(name);a.choose_size();assert (int(a.settings['width'].get()),int(a.settings['height'].get()))==plan[2:];assert a.valid_settings()
  a.wallpaper_size.set('FHD 1920×1080');a.choose_size();a.choose_size(True);assert a.settings['width'].get()=='1920';a.undo_selection();assert a.settings['width'].get()=='1280'
  for placement in ('左寄せ','中央','右寄せ'):
   a.placement.set(placement);a.choose_placement();assert row(app.PLACEMENTS[placement])['id'] in a.selected
   assert sum(row(tag)['id'] in a.selected for tag in app.PLACEMENTS.values() if tag)==1
  a.set_texts('direct edit stays','negative stays');before=set(a.selected);a.clear();a.undo_selection();assert a.selected==before and a.texts[0].get('1.0','end-1c')=='direct edit stays'
  a.roll();a.undo_selection();assert a.selected==before
  # Snapshot and favorite include colors and final sizes, without rewriting text.
  a.favorite.set('壁紙セット');a.fav_save();snapshot=a.snapshot();a.clothing_colors={};a.wallpaper_size.set('指定なし');a.fav_load();assert a.clothing_colors==snapshot['clothing_colors'];assert a.wallpaper_size.get()==snapshot['wallpaper']['size'];assert a.save()
  a.nb.select(0);a.category_notebooks['positive'].select(1);a.update();tree.redraw_grid();a.update();assert any(l.winfo_ismapped() for l in tree._lines)
  for size in ('1260x820','900x620'):
   a.geometry(size);a.update();assert tree.winfo_height()>50;assert all(t.winfo_height()>25 for t in a.texts)
   item=coat['id'];tree.see(item);a.update();b=tree.bbox(item,'copy');assert b and b[0]+b[2]<=tree.winfo_width()
  assert a.style.lookup('TNotebook.Tab','background')
  a.destroy();assert not errors,errors
  a=app.App();a.withdraw();a.update();assert a.clothing_colors==snapshot['clothing_colors'];assert a.wallpaper_size.get()==snapshot['wallpaper']['size'];a.destroy()
 with tempfile.TemporaryDirectory() as d:
  app.DATA=Path(d);old=json.loads((ROOT/'tests/v13_defaults.json').read_text(encoding='utf-8-sig'));old.pop(0);old[0]['ja']='旧編集';custom=dict(old[0],id='custom14',ja='自分の項目',en='my tag');old.append(custom)
  legacycolor=next(r['id'] for r in old if r['en']=='black clothes');state=dict(selected=['custom14',legacycolor],locks=['custom14'],weights={'custom14':1.3},model='Animagine XL 3.1',positive='old manual',negative='negative',settings={'width':'1024','height':'1024'},random_categories=['髪色'])
  files={'presets.json':old,'catalog.json':{'version':12,'keep':'metadata'},'session.json':state,'favorites.json':{'旧お気に入り':state}}
  for name,data in files.items():(Path(d)/name).write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
  before={name:(Path(d)/name).read_bytes() for name in files};a=app.App();a.withdraw();a.update();assert len(a.rows)==len(old)+2;assert a.selected==set(state['selected']);assert a.clothing_colors=={};assert a.wallpaper_size.get()=='指定なし';assert all((Path(d)/name).read_bytes()==data for name,data in before.items())
  a.favorite.set('旧お気に入り');a.fav_load();assert legacycolor in a.selected and a.weights['custom14']==1.3;a.only_selected.set(True);a.refresh();assert a.views[('positive','衣装')][0].exists(legacycolor);assert a.save();assert (Path(d)/'presets.json.pre-v1.4.bak').read_bytes()==before['presets.json'];a.destroy()
 print('V1.4 GUI PASS: outfit colors/dialog/copy, legacy color preservation, selected-only, undo, teen option, wallpaper sizes/placement, favorites/restart, visible grid/pastel, default/minimum layout, v1.3 migration/no startup writes')
if __name__=='__main__':main()
