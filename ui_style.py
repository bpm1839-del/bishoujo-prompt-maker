"""Small pastel theme and a normal ttk.Treeview with real grid-line overlays."""
import tkinter as tk
from tkinter import ttk

def apply_theme(root):
 style=ttk.Style(root);style.theme_use('clam')
 root.configure(background='#fff8f5')
 style.configure('.',background='#fff8f5',foreground='#403642',font=('Yu Gothic UI',9))
 style.configure('TButton',padding=(7,4),background='#eee5f5',bordercolor='#d8c9dd')
 style.map('TButton',background=[('active','#ead4e2'),('pressed','#dec4d8')])
 style.configure('TNotebook',background='#fff8f5',borderwidth=0)
 style.configure('TNotebook.Tab',padding=(7,4),background='#f2eaf0')
 style.map('TNotebook.Tab',background=[('selected','#efd3e0')],foreground=[('selected','#51384c')])
 style.configure('Treeview',background='#fffdfb',fieldbackground='#fffdfb',foreground='#403642',rowheight=24,bordercolor='#d8c9dd')
 style.configure('Treeview.Heading',background='#efe6f2',padding=(3,3),bordercolor='#d8c9dd')
 style.map('Treeview',background=[('selected','#dfc8e9')],foreground=[('selected','#332638')])
 style.configure('TLabelframe',bordercolor='#ddcede');style.configure('TLabelframe.Label',foreground='#74566f')
 return style

class GridTreeview(ttk.Treeview):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self._grid_job=None;self._lines=[]
  self.tag_configure('even',background='#fffdfb');self.tag_configure('odd',background='#fff3f7')
  for event in ('<Configure>','<Expose>','<MouseWheel>','<ButtonRelease-1>','<KeyRelease>'):
   self.bind(event,lambda e:self.redraw_grid(),add='+')
 def redraw_grid(self):
  if self._grid_job is None:self._grid_job=self.after_idle(self._draw_grid)
 def _draw_grid(self):
  self._grid_job=None
  if not self.winfo_ismapped():return
  w,h=self.winfo_width(),self.winfo_height();boxes=[];seen=set()
  for y in range(0,h,8):
   item=self.identify_row(y)
   if item and item not in seen:
    seen.add(item);box=self.bbox(item)
    if box:boxes.append((item,box))
  segments=[]
  if boxes:
   first,box=boxes[0];top=max(0,box[1]);bottom=min(h,boxes[-1][1][1]+boxes[-1][1][3])
   for col in self['columns'][:-1]:
    b=self.bbox(first,col)
    if b and 0<b[0]+b[2]<w:segments.append((b[0]+b[2]-1,top,1,max(1,bottom-top)))
   for _,b in boxes:
    if 0<b[1]+b[3]<h:segments.append((1,b[1]+b[3]-1,max(1,w-2),1))
  while len(self._lines)<len(segments):self._lines.append(tk.Frame(self,background='#e2d5df',borderwidth=0,takefocus=False))
  for line,(x,y,width,height) in zip(self._lines,segments):line.place(x=x,y=y,width=width,height=height);line.lift()
  for line in self._lines[len(segments):]:line.place_forget()
 def yview(self,*args):
  value=super().yview(*args)
  if args:self.redraw_grid()
  return value
 def yview_moveto(self,*args):
  super().yview_moveto(*args);self.redraw_grid()
 def yview_scroll(self,*args):
  super().yview_scroll(*args);self.redraw_grid()
 def see(self,*args):
  super().see(*args);self.redraw_grid()
 def destroy(self):
  if self._grid_job is not None:
   try:self.after_cancel(self._grid_job)
   except tk.TclError:pass
   self._grid_job=None
  super().destroy()
