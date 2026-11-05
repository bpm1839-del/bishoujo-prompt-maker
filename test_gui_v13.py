"""V1.3 copy cells, passive tooltips, and v1.2 data compatibility."""
import json,os,tempfile
from pathlib import Path
ROOT=Path(__file__).parent

def main():
 with tempfile.TemporaryDirectory() as d:
  os.environ['BPM_DATA_DIR']=d
  import app
  app.DATA=Path(d)
  errors=[]
  a=app.App();a.report_callback_exception=lambda *args:errors.append(args);a.update()
  for tip in a.tooltips:tip.delay=0
  def row(en,target='positive'):return next(r for r in a.rows if r['en']==en and r['target']==target)
  def click_copy(key,item_id):
   tree=a.views[key][0];a.nb.select(0 if key[0]=='positive' else 1);a.category_notebooks[key[0]].select(app.TABS.index(key[1]));a.update();tree.see(item_id);a.update()
   x,y,w,h=tree.bbox(item_id,'copy');assert x+w<=tree.winfo_width(),(x,w,tree.winfo_width())
   tree.event_generate('<Button-1>',x=x+w//2,y=y+h//2);tree.event_generate('<ButtonRelease-1>',x=x+w//2,y=y+h//2);a.update()
  def tooltip_message(index,needle):
   tip=a.tooltips[index];text=tip.text;pos=text.search(needle,'1.0');assert pos,needle;text.see(pos);a.update();bounds=text.bbox(pos);assert bounds
   x,y,w,h=bounds;text.event_generate('<Motion>',x=x+max(1,w//2),y=y+h//2);a.update()
   # Moving from one already visible token has a 70ms transition delay.
   if tip.job is not None:
    import tkinter as tk
    completed=tk.BooleanVar(master=a,value=False);a.after(110,lambda:completed.set(True));a.wait_variable(completed);a.update()
   assert tip.popup is not None,needle
   return next(iter(tip.popup.children.values())).cget('text')
  # All displayed rows always carry a copy cell; row height is unchanged.
  from tkinter import ttk
  for key,(tree,cb) in a.views.items():
   assert tree['columns'][-1]=='copy';assert tree.column('copy','stretch')==0
   for i in tree.get_children():assert tree.item(i,'values')[-1]=='コピー'
  def buttons(parent):
   result=[]
   for w in parent.winfo_children():
    if isinstance(w,ttk.Button):result.append(w)
    result+=buttons(w)
   return result
  assert len([b for b in buttons(a) if b.cget('text')=='コピー'])==2  # Existing full-text buttons only.
  a.set_texts('existing generated positive','existing generated negative');a.update()
  p=row('soft lighting');n=row('lowres','negative');key=('positive',p['tab']);tree=a.views[key][0]
  another=next(r['id'] for r in a.rows if r['tab']==key[1] and r['target']=='positive' and r['id']!=p['id'])
  tree.selection_set(another);tree.focus(another);a.selected={another};a.locks={another};a.refresh();a.update()
  a.weights[p['id']]=1.2
  before=(set(a.selected),set(a.locks),tree.selection(),tree.focus(),[t.get('1.0','end-1c') for t in a.texts],a.dirty)
  click_copy(key,p['id']);assert a.clipboard_get()=='(soft lighting:1.2)'
  assert before==(set(a.selected),set(a.locks),tree.selection(),tree.focus(),[t.get('1.0','end-1c') for t in a.texts],a.dirty)
  a.weights[p['id']]=1.0;a.selected.add(p['id']);a.refresh();click_copy(key,p['id']);assert a.clipboard_get()=='soft lighting'
  a.search.set('soft lighting');a.update();assert tree.get_children()==(p['id'],);click_copy(key,p['id']);assert a.clipboard_get()=='soft lighting';a.search.set('')
  a.weights[n['id']]=0.5;click_copy(('negative',n['tab']),n['id']);assert a.clipboard_get()=='(lowres:0.5)'
  gradient=row('black hair, pink hair tips, gradient hair');a.weights[gradient['id']]=1.2;click_copy(('positive','キャラクター'),gradient['id']);assert a.clipboard_get()=='(black hair:1.2), (pink hair tips:1.2), (gradient hair:1.2)'
  # Copy column stays inside the list at the existing minimum window size.
  a.geometry('900x620');a.update();click_copy(('positive','キャラクター'),gradient['id']);a.geometry('1260x820');a.update()
  a.set_texts('masterpiece, (semi-realistic:1.2), soft lighting, unknown_xyz,\n😀, ((soft lighting:1.2):1.1)','(lowres:0.5), soft lighting');a.update()
  content=[t.get('1.0','end-1c') for t in a.texts]
  focus=a.focus_get()
  assert tooltip_message(0,'semi-realistic')=='セミリアル（強調度1.2）'
  assert a.focus_get()==focus
  assert tooltip_message(0,'soft lighting')==p['ja']
  assert tooltip_message(0,'unknown_xyz')=='日本語訳未登録'
  assert tooltip_message(1,'lowres')==n['ja']+'（強調度0.5）'
  # Moving outside a token removes the popup; weighted tags after emoji map correctly.
  tip=a.tooltips[0];tip.text.event_generate('<Leave>');a.update();assert tip.popup is None
  tip.text.mark_set('insert','end-1c');tip.text.insert('insert',', (detailed eyes:1.2)');a.update()
  assert tooltip_message(0,'detailed eyes')=='繊細な瞳（強調度1.2）';assert a.dirty
  # Editing hides any stale popup; normal selection, copy, paste and deletion still work.
  text=a.texts[0];text.insert('end',', edit_check');a.update();assert tip.popup is None
  text.tag_add('sel','1.0','1.11');text.event_generate('<<Copy>>');a.update();assert a.clipboard_get()=='masterpiece'
  text.tag_remove('sel','1.0','end');text.mark_set('insert','end-1c');a.clipboard_clear();a.clipboard_append(', pasted_tag');text.event_generate('<<Paste>>');a.update();assert 'pasted_tag' in text.get('1.0','end')
  end=text.index('end-1c');text.delete(f'{end}-10c',end);a.update()
  a.copy_text(text);assert a.clipboard_get()==text.get('1.0','end-1c')
  # Dictionary refresh follows normal preset CRUD updates.
  a.rows=[dict(r,ja='変更した光') if r['id']==p['id'] else r for r in a.rows];a.refresh();a.set_texts('soft lighting','');a.update();assert tooltip_message(0,'soft lighting')=='変更した光'
  # Long popup near bottom-right is wrapped and bounded without taking focus.
  tip.hide();tip.show('長い日本語訳'*600,a.winfo_screenwidth()-1,a.winfo_screenheight()-1);a.update()
  pop=tip.popup;assert pop.winfo_rootx()>=0 and pop.winfo_rooty()>=0;assert pop.winfo_rootx()+pop.winfo_width()<=a.winfo_screenwidth();assert pop.winfo_rooty()+pop.winfo_height()<=a.winfo_screenheight()
  tip.hide();a.destroy();assert not errors,errors
 with tempfile.TemporaryDirectory() as d:
  app.DATA=Path(d)
  old=json.loads((ROOT/'defaults.json').read_text(encoding='utf-8-sig'));removed=next(r for r in old if r['en']=='anime style');deleted=removed['id'];old.remove(removed);old[0]['ja']='Ver1.2ユーザー編集';custom=dict(old[0],id='user13',en='my custom',ja='独自タグ',weight=1.4);old.append(custom)
  state=dict(schema_version=2,selected=[custom['id']],locks=[custom['id']],weights={custom['id']:1.3},model='Custom',positive='manually edited v12 positive',negative='manual v12 negative',settings={'width':'1024','height':'1024','steps':'28','cfg':'7','seed':'123','sampler':'Euler a'},random_categories=['髪色'])
  files={'presets.json':old,'session.json':state,'favorites.json':{'旧お気に入り':state},'models.json':{'Custom':{'prefix':'1girl','suffix':'custom suffix','negative':'custom negative'}},'catalog.json':{'version':12,'keep':'metadata'},'translations.json':{'my custom':'追加辞書訳'}}
  for name,value in files.items():(Path(d)/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
  before={name:(Path(d)/name).read_bytes() for name in files}
  a=app.App();a.withdraw();a.update();assert a.rows[0]['ja']=='Ver1.2ユーザー編集';assert deleted not in {r['id'] for r in a.rows};assert a.selected=={custom['id']} and a.weights[custom['id']]==1.3;assert a.locks=={custom['id']};assert a.model.get()=='Custom';assert a.settings['seed'].get()=='123'
  assert all((Path(d)/name).read_bytes()==data for name,data in before.items())
  a.copy_preset(custom['id']);assert a.clipboard_get()=='(my custom:1.3)';a.favorite.set('旧お気に入り');a.fav_load();assert a.texts[0].get('1.0','end-1c')==state['positive'];assert a.weights[custom['id']]==1.3
  assert a.save();assert (Path(d)/'presets.json.pre-v1.4.bak').read_bytes()==before['presets.json'];assert json.loads((Path(d)/'catalog.json').read_text(encoding='utf-8'))==dict(files['catalog.json'],version=14);a.destroy()
 print('V1.3 GUI PASS: all-row copy cells, actual click, unchanged selection/check/focus/text, both targets, search, weights/combinations, minimum layout, tooltips, unknown tags, emoji, editing/full copy/paste, dictionary refresh, popup bounds, v1.2 data compatibility/no startup writes')
if __name__=='__main__':main()

