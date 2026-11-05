import copy, json, os, sys, uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from core import TABS, WEIGHT_VALUES, atomic_save, validate, validate_weights, weight_value, migrate_presets, conflicts, randomize, generate, STRICT_GROUPS, strict_group, normalize_selection, set_selected, preset_prompt
from prompt_help import TranslationIndex, validate_translations
from tooltips import PromptTooltip
from features import COLORS, COLOR_NAMES, SIZES, PLACEMENTS, garment_parts, validate_colors, colorize_rows, wallpaper_hint
from ui_style import apply_theme, GridTreeview
ASSETS=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
DATA=Path(os.environ.get('BPM_DATA_DIR',str(Path(os.environ.get('LOCALAPPDATA',Path.home()))/'BishoujoPromptMaker')))
class App(tk.Tk):
 def __init__(self):
  super().__init__(); self.title('美少女プロンプトメーカー Ver.1.4');self.geometry('1260x820');self.minsize(900,620)
  self.style=apply_theme(self)
  self.defaults=validate(json.loads((ASSETS/'defaults.json').read_text(encoding='utf-8-sig')))
  self.rows=self.load('presets.json',copy.deepcopy(self.defaults),validate)
  catalog=self.load('catalog.json',{},lambda d:d if isinstance(d,dict) and type(d.get('version',0)) is int else {})
  self.catalog=catalog
  if catalog.get('version',0)<14:self.rows=migrate_presets(self.rows,self.defaults,catalog.get('version',0))
  self.models=self.load('models.json',json.loads((ASSETS/'models.json').read_text(encoding='utf-8-sig')),self.validate_models)
  self.favorites=self.load('favorites.json',{},self.validate_favorites)
  self.state=self.load('session.json',{},self.validate_session);self.selected=set(self.state.get('selected',[]));self.locks=set(self.state.get('locks',[])); self.dirty=False;self.ready=False
  self.selected=normalize_selection(self.rows,self.selected,self.locks)
  self.clothing_colors=validate_colors(copy.deepcopy(self.state.get('clothing_colors',{})))
  wall=self.state.get('wallpaper',{})
  self.wallpaper_size=tk.StringVar(value=wall.get('size','指定なし'));self.placement=tk.StringVar(value=wall.get('placement','指定なし'))
  self.only_selected=tk.BooleanVar(value=False);self.show_legacy_colors=tk.BooleanVar(value=False);self.undo_stack=[];self._last_selection_state=None
  bundled=validate_translations(json.loads((ASSETS/'translations.json').read_text(encoding='utf-8-sig')))
  extras=self.load('translations.json',{},validate_translations)
  self.translator=TranslationIndex(self.rows,dict(bundled,**extras));self.translation_source=self.rows;self.tooltips=[]
  self.weights={r['id']:self.state.get('weights',{}).get(r['id'],r['weight']) for r in self.rows}
  self.model=tk.StringVar(value=self.state.get('model',next(iter(self.models))))
  if self.model.get() not in self.models:self.model.set(next(iter(self.models)))
  self.search=tk.StringVar();self.favorite=tk.StringVar();self.status=tk.StringVar();self.views={};self.cats={};self.random_cats={};self.random_frames={}
  bar=ttk.Frame(self,padding=8);bar.pack(fill='x');ttk.Label(bar,text='モデル').pack(side='left');ttk.Combobox(bar,textvariable=self.model,values=list(self.models),state='readonly',width=26).pack(side='left',padx=5)
  for label,fn in [('プロンプト生成',self.make),('ランダム選択',self.roll),('選択クリア',self.clear),('ひとつ戻る',self.undo_selection),('作業を保存',self.save)]:ttk.Button(bar,text=label,command=fn).pack(side='left',padx=3)
  pane=ttk.Panedwindow(self,orient='horizontal');pane.pack(fill='both',expand=True,padx=8);left=ttk.Frame(pane);right=ttk.Frame(pane);pane.add(left,weight=3);pane.add(right,weight=2)
  searchbar=ttk.Frame(left);searchbar.pack(fill='x');ttk.Label(searchbar,text='全タブ検索（日/英）').pack(side='left');ttk.Entry(searchbar,textvariable=self.search).pack(side='left',fill='x',expand=True)
  ttk.Checkbutton(searchbar,text='選択中だけ',variable=self.only_selected,command=self.refresh).pack(side='left',padx=4)
  self.nb=ttk.Notebook(left);self.nb.pack(fill='both',expand=True)
  self.category_notebooks={};self.weight_inputs={};self.character_choices={};self.character_choice_rows={}
  default_random={'髪色','髪の長さ','髪型','瞳色','表情','基本服','姿勢','画角','場所','光'}
  for target in ('positive','negative'):
   target_page=ttk.Frame(self.nb);self.nb.add(target_page,text=target.title())
   category_nb=ttk.Notebook(target_page);category_nb.pack(fill='both',expand=True);self.category_notebooks[target]=category_nb
   for tab in TABS:
    key=(target,tab)
    page=ttk.Frame(category_nb);category_nb.add(page,text=tab);top=ttk.Frame(page);top.pack(fill='x');cat=tk.StringVar(value='すべて');self.cats[key]=cat
    cb=ttk.Combobox(top,textvariable=cat,state='readonly',width=20);cb.pack(side='left');cb.bind('<<ComboboxSelected>>',lambda e:self.refresh())
    ttk.Button(top,text='表示項目を選択',command=lambda t=key:self.bulk(t,True)).pack(side='left');ttk.Button(top,text='表示の選択解除',command=lambda t=key:self.bulk(t,False)).pack(side='left')
    if key==('positive','衣装'):
     colorbar=ttk.Frame(page);colorbar.pack(fill='x');ttk.Button(colorbar,text='選んだ衣装の色…',command=self.edit_colors).pack(side='left');ttk.Checkbutton(colorbar,text='旧色タグを表示',variable=self.show_legacy_colors,command=self.refresh).pack(side='left',padx=5)
    if key==('positive','キャラクター'):
     choices=ttk.LabelFrame(page,text='キャラクター設定（各1種類／指定なし可）');choices.pack(fill='x')
     for n,group in enumerate(STRICT_GROUPS):
      ttk.Label(choices,text=group).grid(row=n//2,column=(n%2)*2,sticky='w',padx=4)
      cv=tk.StringVar(value='指定なし');box=ttk.Combobox(choices,textvariable=cv,values=['指定なし'],state='readonly',width=15)
      box.grid(row=n//2,column=(n%2)*2+1,sticky='ew',padx=4,pady=2);box.bind('<<ComboboxSelected>>',lambda e,g=group:self.choose_character(g));self.character_choices[group]=(cv,box)
     choices.columnconfigure(1,weight=1);choices.columnconfigure(3,weight=1)
    frame=ttk.Frame(page);frame.pack(fill='both',expand=True);tree=GridTreeview(frame,columns=('s','l','ja','w','en','copy'),show='headings',selectmode='extended')
    for col,label,w in [('s','選択',40),('l','固定',40),('ja','日本語',160),('w','強調度',55),('en','English tag',180),('copy','コピー',50)]:tree.heading(col,text=label);tree.column(col,width=w,stretch=col in ('ja','en'))
    tree.column('ja',minwidth=90);tree.column('en',minwidth=70);tree.column('copy',minwidth=50,anchor='center')
    tree.bind('<ButtonRelease-1>',lambda e,t=tree:'break' if t.identify_column(e.x)=='#6' else None)
    tree.bind('<Double-Button-1>',lambda e,t=key:self.click(e,t))
    scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
    tree.bind('<Button-1>',lambda e,t=key:self.click(e,t));tree.bind('<space>',lambda e,t=key:self.toggle(t));self.views[key]=(tree,cb)
    weightbar=ttk.Frame(page);weightbar.pack(fill='x');wv=tk.StringVar(value='1.0');self.weight_inputs[key]=wv
    ttk.Label(weightbar,text='選択行の強調度').pack(side='left');ttk.Spinbox(weightbar,textvariable=wv,values=[f'{v:.1f}' for v in WEIGHT_VALUES],state='readonly',width=5,wrap=False).pack(side='left',padx=4)
    ttk.Button(weightbar,text='強調度を適用',command=lambda t=key:self.apply_weight(t)).pack(side='left')
    tree.bind('<<TreeviewSelect>>',lambda e,t=key:self.show_weight(t))
    buttons=ttk.Frame(page);buttons.pack(fill='x')
    for label,fn in [('追加',lambda t=key:self.edit(t,'add')),('編集',lambda t=key:self.edit(t,'edit')),('複製',lambda t=key:self.edit(t,'copy')),('削除',lambda t=key:self.delete(t)),('固定切替',lambda t=key:self.lock(t))]:ttk.Button(buttons,text=label,command=fn).pack(side='left')
    if target=='positive':
     lf=ttk.LabelFrame(page,text='ランダム対象カテゴリ（各1個・固定項目は保持）');lf.pack(fill='x');self.random_frames[tab]=lf
     for n,c in enumerate(dict.fromkeys(r['category'] for r in self.rows if r['tab']==tab and r['target']=='positive' and r['category']!='服の色')):
      v=tk.BooleanVar(value=c in self.state.get('random_categories',list(default_random)));self.random_cats[(tab,c)]=v;ttk.Checkbutton(lf,text=c,variable=v).grid(row=n//4,column=n%4,sticky='w')
    else:ttk.Label(page,text='Negativeはランダム抽選の対象外です。').pack(anchor='w')
  ttk.Label(left,text='選択欄クリック／Spaceで切替。固定欄クリックでランダム変更を防止。').pack(anchor='w')
  ttk.Button(left,text='全プリセットを初期化',command=self.reset).pack(anchor='w')
  self.texts=[]
  for label in ['Positive（生成後に直接編集できます）','Negative（生成後に直接編集できます）']:
   ttk.Label(right,text=label).pack(anchor='w');text=tk.Text(right,height=10,wrap='word',undo=True,background='#fffdfb',foreground='#403642',selectbackground='#e6ccdf',insertbackground='#69475e');text.pack(fill='both',expand=True);text.bind('<<Modified>>',self.modified);self.texts.append(text)
   ttk.Button(right,text='コピー',command=lambda t=text:self.copy_text(t)).pack(anchor='e')
  self.tooltips=[PromptTooltip(t,self.translator,target) for t,target in zip(self.texts,('positive','negative'))]
  sett=ttk.LabelFrame(right,text='Forgeへ手動で設定');sett.pack(fill='x');self.settings={}
  for i,(key,label,default) in enumerate([('width','幅',832),('height','高さ',1216),('steps','Steps',28),('cfg','CFG',7),('seed','Seed',-1),('sampler','Sampler','Euler a')]):
   ttk.Label(sett,text=label).grid(row=i//2,column=(i%2)*2);v=tk.StringVar(value=str(self.state.get('settings',{}).get(key,default)));self.settings[key]=v;ttk.Entry(sett,textvariable=v,width=14).grid(row=i//2,column=(i%2)*2+1,sticky='ew')
  wallframe=ttk.LabelFrame(right,text='壁紙・完成サイズ');wallframe.pack(fill='x')
  ttk.Label(wallframe,text='完成サイズ').grid(row=0,column=0,sticky='w');sizebox=ttk.Combobox(wallframe,textvariable=self.wallpaper_size,values=list(SIZES),state='readonly',width=29);sizebox.grid(row=0,column=1,sticky='ew');sizebox.bind('<<ComboboxSelected>>',lambda e:self.choose_size())
  actions=ttk.Frame(wallframe);actions.grid(row=1,column=0,columnspan=2,sticky='ew');ttk.Button(actions,text='推奨生成サイズ',command=self.choose_size).pack(side='left');ttk.Button(actions,text='完成サイズを直接設定',command=lambda:self.choose_size(True)).pack(side='left')
  ttk.Label(wallframe,text='人物の配置').grid(row=2,column=0,sticky='w');placebox=ttk.Combobox(wallframe,textvariable=self.placement,values=list(PLACEMENTS),state='readonly',width=12);placebox.grid(row=2,column=1,sticky='w');placebox.bind('<<ComboboxSelected>>',lambda e:self.choose_placement())
  self.size_hint=tk.StringVar();ttk.Label(wallframe,textvariable=self.size_hint,wraplength=350).grid(row=3,column=0,columnspan=2,sticky='w');wallframe.columnconfigure(1,weight=1)
  for k in ('width','height'):self.settings[k].trace_add('write',lambda *args:self.update_size_hint())
  self.update_size_hint()
  fav=ttk.LabelFrame(right,text='組み合わせのお気に入り（直接編集も保存）');fav.pack(fill='x');self.favbox=ttk.Combobox(fav,textvariable=self.favorite,values=list(self.favorites));self.favbox.pack(fill='x')
  for label,fn in [('保存',self.fav_save),('読込',self.fav_load),('削除',self.fav_delete)]:ttk.Button(fav,text=label,command=fn).pack(side='left')
  self.warning=tk.Text(right,height=4,wrap='word',foreground='#a04422',state='disabled');self.warning.pack(fill='x');ttk.Label(self,textvariable=self.status,padding=6).pack(fill='x')
  self.search.trace_add('write',lambda *a:self.refresh());self.refresh();self.set_texts(self.state.get('positive',''),self.state.get('negative',''));self.ready=True;self.protocol('WM_DELETE_WINDOW',self.close)
 @staticmethod
 def validate_models(d):
  if not isinstance(d,dict) or not d or any(not isinstance(v,dict) or any(not isinstance(v.get(k,''),str) for k in ('prefix','suffix','negative')) for v in d.values()):raise ValueError('モデル形式が不正です')
  return d
 @staticmethod
 def validate_session(d):
  if not isinstance(d,dict) or any(not isinstance(d.get(k,[]),list) or any(not isinstance(i,str) for i in d.get(k,[])) for k in ('selected','locks','random_categories')) or not isinstance(d.get('settings',{}),dict) or any(not isinstance(d.get(k,''),str) for k in ('model','positive','negative')):raise ValueError('保存内容が不正です')
  if 'weights' in d:d['weights']=validate_weights(d['weights'])
  validate_colors(d.get('clothing_colors',{}))
  wall=d.get('wallpaper',{})
  if not isinstance(wall,dict) or wall.get('size','指定なし') not in SIZES or wall.get('placement','指定なし') not in PLACEMENTS:raise ValueError('壁紙設定が不正です')
  return d
 @classmethod
 def validate_favorites(cls,d):
  if not isinstance(d,dict):raise ValueError('お気に入り形式が不正です')
  for v in d.values():
   cls.validate_session(v)
   if any(k not in v for k in ('selected','locks','model','positive','negative')):raise ValueError('お気に入りの必須項目がありません')
  return d
 def load(self,name,default,validator):
  path=DATA/name
  if not path.exists():return default
  try:return validator(json.loads(path.read_text(encoding='utf-8-sig')))
  except (ValueError,OSError,TypeError) as e:
   messagebox.showwarning('保存データを読めません',f'{path}\n{e}\n初期値で起動します。元ファイルは .broken として退避します。')
   try:
    import shutil
    shutil.copy2(path,path.with_name(path.name+'.'+uuid.uuid4().hex[:8]+'.broken'))
   except OSError:pass
   return default
 def persist(self,name,value):
  try:
   path=DATA/name
   backup=path.with_name(path.name+'.pre-v1.4.bak')
   if path.exists() and not backup.exists():
    import shutil
    shutil.copy2(path,backup)
   atomic_save(path,value)
   if name=='presets.json':
    marker=DATA/'catalog.json';marker_backup=DATA/'catalog.json.pre-v1.4.bak'
    if marker.exists() and not marker_backup.exists():
     import shutil
     shutil.copy2(marker,marker_backup)
    self.catalog=dict(self.catalog,version=14);atomic_save(marker,self.catalog)
   return True
  except OSError as e:messagebox.showerror('保存できません',str(e));return False
 def refresh(self):
  display_rows=colorize_rows(self.rows,self.clothing_colors);display_by_id={r['id']:r for r in display_rows}
  color_key=json.dumps(self.clothing_colors,sort_keys=True,ensure_ascii=False)
  if self.translation_source is not self.rows or getattr(self,'_translation_color_key',None)!=color_key:
   self.translator.rebuild(display_rows+self.rows);self.translation_source=self.rows;self._translation_color_key=color_key
   for tip in self.tooltips:tip.invalidate()
  for key,(tree,cb) in self.views.items():
   target,tab=key
   focus=tree.selection();tree.delete(*tree.get_children());cats=list(dict.fromkeys(r['category'] for r in self.rows if r['tab']==tab and r['target']==target and (r['category']!='服の色' or self.show_legacy_colors.get())));cb['values']=['すべて']+cats
   if self.cats[key].get() not in ['すべて']+cats:self.cats[key].set('すべて')
   if target=='positive':
    for c in cats:
     if c=='服の色':continue
     if (tab,c) not in self.random_cats:
      n=sum(1 for t,k in self.random_cats if t==tab);v=tk.BooleanVar(value=False);self.random_cats[(tab,c)]=v;ttk.Checkbutton(self.random_frames[tab],text=c,variable=v).grid(row=n//4,column=n%4,sticky='w')
   q=self.search.get().casefold()
   count=0
   for r in self.rows:
    dr=display_by_id[r['id']]
    legacy=r['category']=='服の色' and r['target']=='positive'
    if legacy and not self.show_legacy_colors.get() and not (self.only_selected.get() and r['id'] in self.selected):continue
    if self.only_selected.get() and r['id'] not in self.selected:continue
    if r['tab']==tab and r['target']==target and (self.cats[key].get() in ('すべて',r['category'])) and q in (dr['ja']+' '+dr['en']+' '+r['category']).casefold():
     tree.insert('', 'end',iid=r['id'],values=('✓' if r['id'] in self.selected else '', '🔒' if r['id'] in self.locks else '',dr['ja'],f"{self.weights.get(r['id'],r['weight']):.1f}",dr['en'],'コピー'),tags=('even' if count%2==0 else 'odd',));count+=1
   tree.redraw_grid()
   for i in focus:
    if tree.exists(i):tree.selection_add(i)
  self.refresh_character_choices()
  self.sync_placement();self.update_size_hint()
  self._last_selection_state=self.selection_state()
  warnings=conflicts(display_rows,self.selected);self.warning.configure(state='normal');self.warning.delete('1.0','end');self.warning.insert('1.0','矛盾候補（組合せによっては意図的に使用可）\n'+'\n'.join(warnings) if warnings else '矛盾候補はありません');self.warning.configure(state='disabled');self.status.set(f'プリセット {len(self.rows)}件 ／ 選択 {len(self.selected)}件 ／ 保存先 {DATA}')
 def refresh_character_choices(self):
  for group,(var,box) in self.character_choices.items():
   rows=[r for r in self.rows if strict_group(r)==group]
   if group=='年齢':rows.sort(key=lambda r:r['en']!='teenage')
   self.character_choice_rows[group]=rows
   box['values']=['指定なし']+[r['ja'] for r in rows]
   index=next((i+1 for i,r in enumerate(rows) if r['id'] in self.selected),0);box.current(index)
 def choose_character(self,group):
  self.remember()
  index=self.character_choices[group][1].current();rows=self.character_choice_rows[group]
  self.selected.difference_update(r['id'] for r in self.rows if strict_group(r)==group)
  if 0<index<=len(rows):self.selected=set_selected(self.rows,self.selected,rows[index-1]['id'])
  self.refresh()
 def show_weight(self,key):
  ids=self.views[key][0].selection()
  if ids:self.weight_inputs[key].set(f"{self.weights.get(ids[0],1.0):.1f}")
 def apply_weight(self,key):
  ids=self.views[key][0].selection()
  if not ids:messagebox.showinfo('項目選択','強調度を変更する項目名を選んでください');return
  try:value=weight_value(self.weight_inputs[key].get())
  except ValueError as e:messagebox.showerror('強調度',str(e));return
  self.remember()
  for i in ids:self.weights[i]=value
  self.refresh()
 def click(self,e,tab):
  tree=self.views[tab][0];i=tree.identify_row(e.y);col=tree.identify_column(e.x)
  if i and col=='#6':
   self.copy_preset(i);return 'break'
  if i and col in ('#1','#2'):
   self.remember()
   if col=='#1':self.selected=set_selected(self.rows,self.selected,i,i not in self.selected)
   else:self.locks.symmetric_difference_update([i])
   self.refresh();return 'break'
 def copy_preset(self,item_id):
  row=next((r for r in self.rows if r['id']==item_id),None)
  if row is None:return
  value=preset_prompt(row,self.weights.get(item_id,row['weight']),self.clothing_colors)
  self.clipboard_clear();self.clipboard_append(value);self.status.set('英語タグをコピーしました：'+row['ja'])
 def toggle(self,tab):
  self.remember()
  for i in self.views[tab][0].selection():self.selected=set_selected(self.rows,self.selected,i,i not in self.selected)
  self.refresh();return 'break'
 def bulk(self,tab,on):
  self.remember()
  ids=self.views[tab][0].get_children()
  for i in ids:self.selected=set_selected(self.rows,self.selected,i,on)
  self.refresh()
 def lock(self,tab):
  self.remember()
  for i in self.views[tab][0].selection():self.locks.symmetric_difference_update([i])
  self.refresh()
 def clear(self):self.remember();self.selected.clear();self.refresh()
 def roll(self):self.remember();self.selected=randomize(self.rows,self.selected,self.locks,[k for k,v in self.random_cats.items() if v.get()]);self.refresh()
 def modified(self,e):
  if e.widget.edit_modified():
   for tip in self.tooltips:
    if tip.text is e.widget:tip.invalidate()
   if self.ready:self.dirty=True
   e.widget.edit_modified(False)
 def set_texts(self,p,n):
  for tip in self.tooltips:tip.invalidate()
  self.ready=False
  for t,s in zip(self.texts,(p,n)):t.delete('1.0','end');t.insert('1.0',s);t.edit_modified(False);t.edit_reset()
  self.dirty=False;self.ready=True
 def confirm(self):return not self.dirty or messagebox.askyesno('直接編集の上書き確認','未保存の直接編集があります。上書きしますか？\n「作業を保存」で保存できます。')
 def valid_settings(self):
  try:
   w=int(self.settings['width'].get());h=int(self.settings['height'].get());s=int(self.settings['steps'].get());c=float(self.settings['cfg'].get());seed=int(self.settings['seed'].get())
   if not (64<=w<=8192 and 64<=h<=8192 and w%8==h%8==0 and 1<=s<=200 and 0<c<=30 and -1<=seed<=4294967295):raise ValueError()
   if not self.settings['sampler'].get().strip():raise ValueError()
  except ValueError:messagebox.showerror('生成設定','幅・高さは64〜8192の8の倍数、Stepsは1〜200、CFGは0超〜30、Seedは-1〜4294967295で入力してください。');return False
  return True
 def make(self):
  if self.valid_settings() and self.confirm():self.set_texts(*generate(self.rows,self.selected,self.models[self.model.get()],self.weights,self.clothing_colors))
 def copy_text(self,t):self.clipboard_clear();self.clipboard_append(t.get('1.0','end-1c'));self.status.set('クリップボードへコピーしました')
 def snapshot(self):return dict(schema_version=3,clothing_colors=copy.deepcopy(self.clothing_colors),wallpaper={'size':self.wallpaper_size.get(),'placement':self.placement.get()},weights=dict(self.weights),selected=sorted(self.selected),locks=sorted(self.locks),model=self.model.get(),positive=self.texts[0].get('1.0','end-1c'),negative=self.texts[1].get('1.0','end-1c'),settings={k:v.get() for k,v in self.settings.items()},random_categories=[c for (t,c),v in self.random_cats.items() if v.get()])
 def save(self):
  if not self.valid_settings():return False
  if self.persist('session.json',self.snapshot()) and self.persist('presets.json',self.rows) and self.persist('models.json',self.models):self.dirty=False;self.status.set('作業を保存しました');return True
  return False
 def fav_save(self):
  name=self.favorite.get().strip()
  if not name:messagebox.showinfo('名前','お気に入りの名前を入力してください');return
  if name in self.favorites and not messagebox.askyesno('上書き',name+' を上書きしますか？'):return
  if not self.valid_settings():return
  updated=dict(self.favorites);updated[name]=self.snapshot()
  if self.persist('favorites.json',updated):self.favorites=updated;self.favbox['values']=list(updated);self.dirty=False
 def fav_load(self):
  s=self.favorites.get(self.favorite.get())
  if s is None or not self.confirm():return
  self.remember()
  self.clothing_colors=copy.deepcopy(s.get('clothing_colors',{}));wall=s.get('wallpaper',{});self.wallpaper_size.set(wall.get('size','指定なし'));self.placement.set(wall.get('placement','指定なし'))
  self.selected=set(s['selected']) & {r['id'] for r in self.rows};self.locks=set(s['locks']) & {r['id'] for r in self.rows};self.model.set(s['model'] if s['model'] in self.models else next(iter(self.models)))
  self.selected=normalize_selection(self.rows,self.selected,self.locks)
  self.weights={r['id']:s.get('weights',{}).get(r['id'],1.0) for r in self.rows}
  for k,v in self.settings.items():v.set(s.get('settings',{}).get(k,v.get()))
  for (t,c),v in self.random_cats.items():v.set(c in s.get('random_categories',[]))
  self.selected=normalize_selection(self.rows,self.selected,self.locks)
  self.set_texts(s['positive'],s['negative']);self.refresh()
 def fav_delete(self):
  name=self.favorite.get()
  if name in self.favorites and messagebox.askyesno('削除',name+' を削除しますか？'):
   updated=dict(self.favorites);del updated[name]
   if self.persist('favorites.json',updated):self.favorites=updated;self.favbox['values']=list(updated);self.favorite.set('')
 def edit(self,tab,mode):
  ids=self.views[tab][0].selection()
  if mode!='add' and len(ids)!=1:messagebox.showinfo('項目選択','一覧から1項目を選んでください');return
  old=next((r for r in self.rows if ids and r['id']==ids[0]),None)
  item=copy.deepcopy(old) if mode!='add' else dict(id='',tab=tab[1],category='カスタム',ja='',en='',target=tab[0],group='',weight=1.0)
  item['weight']=self.weights.get(item['id'],item.get('weight',1.0))
  win=tk.Toplevel(self);win.title({'add':'追加','edit':'編集','copy':'複製'}[mode]);win.transient(self);win.grab_set();fields={}
  for n,(k,label) in enumerate([('tab','タブ'),('category','カテゴリ'),('ja','日本語名'),('en','英語タグ（カンマ可）'),('target','出力先'),('group','排他グループ（任意）'),('weight','強調度（0.5〜1.5）')]):
   ttk.Label(win,text=label).grid(row=n,column=0,sticky='w',padx=8,pady=5);v=tk.StringVar(value=item[k]);fields[k]=v
   if k in ('tab','target'):w=ttk.Combobox(win,textvariable=v,values=TABS if k=='tab' else ['positive','negative'],state='readonly',width=40)
   elif k=='weight':w=ttk.Spinbox(win,textvariable=v,values=[f'{n:.1f}' for n in WEIGHT_VALUES],state='readonly',width=40)
   else:w=ttk.Entry(win,textvariable=v,width=43)
   w.grid(row=n,column=1,padx=8,pady=5)
  def commit():
   r=copy.deepcopy(item);r.update({k:v.get().strip() for k,v in fields.items()});r['id']=item['id'] if mode=='edit' else 'u'+uuid.uuid4().hex
   try:r['weight']=weight_value(r['weight'])
   except ValueError as e:messagebox.showerror('強調度',str(e),parent=win);return
   if any(not r[k] for k in ('category','ja','en')):messagebox.showerror('入力不足','カテゴリ・日本語名・英語タグを入力してください',parent=win);return
   if any(x['id']!=r['id'] and x['target']==r['target'] and (x['en'].strip().casefold()==r['en'].casefold() or (x['tab']==r['tab'] and x['category']==r['category'] and x['ja'].strip().casefold()==r['ja'].casefold())) for x in self.rows):messagebox.showerror('重複','同じ出力先の英語タグ、または同じタブ・カテゴリ内の日本語名が登録済みです',parent=win);return
   updated=[r if x['id']==r['id'] else x for x in self.rows] if mode=='edit' else self.rows+[r]
   if self.persist('presets.json',updated):self.rows=updated;self.weights[r['id']]=r['weight'];self.selected=normalize_selection(self.rows,self.selected,self.locks);self.refresh();win.destroy()
  ttk.Button(win,text='保存',command=commit).grid(row=7,column=1,pady=10)
 def delete(self,tab):
  ids=set(self.views[tab][0].selection())
  if ids and messagebox.askyesno('削除',f'{len(ids)}件を削除しますか？'):
   updated=[r for r in self.rows if r['id'] not in ids]
   if self.persist('presets.json',updated):self.rows=updated;self.selected-=ids;self.locks-=ids;self.weights={i:w for i,w in self.weights.items() if i not in ids};self.refresh()
 def reset(self):
  if messagebox.askyesno('初期化','追加・編集した全プリセットを初期状態へ戻しますか？\nお気に入りと直接編集プロンプトは残ります。'):
   if self.persist('presets.json',self.defaults):self.rows=copy.deepcopy(self.defaults);self.clothing_colors={};self.weights={r['id']:1.0 for r in self.rows};self.selected &= {r['id'] for r in self.rows};self.locks &= {r['id'] for r in self.rows};self.refresh()
 def selection_state(self):
  return dict(selected=sorted(self.selected),locks=sorted(self.locks),weights=dict(self.weights),colors=copy.deepcopy(self.clothing_colors),wallpaper={'size':self.wallpaper_size.get(),'placement':self.placement.get()},settings={k:v.get() for k,v in self.settings.items()})
 def remember(self,state=None):
  state=copy.deepcopy(state if state is not None else self.selection_state())
  if not self.undo_stack or self.undo_stack[-1]!=state:self.undo_stack.append(state)
  self.undo_stack=self.undo_stack[-30:]
 def undo_selection(self):
  if not self.undo_stack:self.status.set('戻せる操作がありません');return
  s=self.undo_stack.pop();known={r['id'] for r in self.rows};self.selected=normalize_selection(self.rows,set(s['selected'])&known);self.locks=set(s['locks'])&known;self.weights={r['id']:s['weights'].get(r['id'],r['weight']) for r in self.rows};self.clothing_colors=s['colors']
  self.wallpaper_size.set(s['wallpaper']['size']);self.placement.set(s['wallpaper']['placement'])
  for k,v in self.settings.items():v.set(s['settings'].get(k,v.get()))
  self.refresh();self.status.set('直前の選択操作を戻しました（生成済み本文はそのまま）')
 def update_size_hint(self):
  if hasattr(self,'size_hint'):self.size_hint.set(wallpaper_hint(self.wallpaper_size.get(),self.settings['width'].get(),self.settings['height'].get()))
 def choose_size(self,direct=False):
  plan=SIZES.get(self.wallpaper_size.get())
  before=self.selection_state()
  if self._last_selection_state:before['wallpaper']['size']=self._last_selection_state['wallpaper']['size']
  self.remember(before)
  if plan is None:self.refresh();return
  w,h=plan[:2] if direct else plan[2:];self.settings['width'].set(str(w));self.settings['height'].set(str(h));self.refresh()
 def sync_placement(self):
  choices=[name for name,tag in PLACEMENTS.items() if tag and any(r['id'] in self.selected and r['target']=='positive' and r['en']==tag for r in self.rows)]
  self.placement.set(choices[0] if len(choices)==1 else '指定なし')
 def choose_placement(self):
  before=self.selection_state()
  if self._last_selection_state:before['wallpaper']['placement']=self._last_selection_state['wallpaper']['placement']
  self.remember(before);choice=self.placement.get();tag=PLACEMENTS[choice]
  self.selected.difference_update(r['id'] for r in self.rows if r['target']=='positive' and r['en'] in PLACEMENTS.values())
  row=next((r for r in self.rows if r['target']=='positive' and r['en']==tag),None)
  if row:self.selected.add(row['id'])
  self.refresh()
  if tag and row is None:self.status.set('対応する配置プリセットが削除されています。プリセット追加から登録できます：'+tag)
 def edit_colors(self):
  rows=[r for r in self.rows if r['id'] in self.selected and garment_parts(r)]
  if not rows:messagebox.showinfo('衣装の色','衣装をチェックしてから、このボタンを押してください');return
  win=tk.Toplevel(self);win.title('衣装ごとの色');win.geometry('540x440');win.transient(self);win.grab_set()
  ttk.Label(win,text='衣装ごとに指定します。チェックを外しても色設定は保持します。',wraplength=510).pack(fill='x',padx=10,pady=6)
  frame=ttk.Frame(win);frame.pack(fill='both',expand=True,padx=8);canvas=tk.Canvas(frame,highlightthickness=0,background='#fff8f5');scroll=ttk.Scrollbar(frame,orient='vertical',command=canvas.yview);canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True);body=ttk.Frame(canvas);window=canvas.create_window(0,0,window=body,anchor='nw')
  body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
  self.color_dialog_vars={}
  n=0
  for r in rows:
   for atom in garment_parts(r):
    label=r['ja'] if len(garment_parts(r))==1 else r['ja']+' / '+atom
    ttk.Label(body,text=label,wraplength=330).grid(row=n,column=0,sticky='w',padx=5,pady=5);v=tk.StringVar(value=COLOR_NAMES.get(self.clothing_colors.get(r['id'],{}).get(atom,''),'指定なし'));self.color_dialog_vars[(r['id'],atom)]=v
    ttk.Combobox(body,textvariable=v,values=list(COLORS),state='readonly',width=13).grid(row=n,column=1,padx=5,pady=5);n+=1
  body.columnconfigure(0,weight=1)
  def commit():
   self.remember()
   for (i,atom),var in self.color_dialog_vars.items():self.clothing_colors.setdefault(i,{})[atom]=COLORS[var.get()]
   self.refresh();win.destroy()
  controls=ttk.Frame(win);controls.pack(fill='x',padx=8,pady=8);ttk.Button(controls,text='適用',command=commit).pack(side='right');ttk.Button(controls,text='キャンセル',command=win.destroy).pack(side='right',padx=5)
 def destroy(self):
  for tip in getattr(self,'tooltips',[]):tip.hide()
  super().destroy()
 def close(self):
  answer=messagebox.askyesnocancel('終了','現在の選択・直接編集・生成設定を保存して終了しますか？')
  if answer is None:return
  if answer and not self.save():return
  self.destroy()
if __name__=='__main__':App().mainloop()
