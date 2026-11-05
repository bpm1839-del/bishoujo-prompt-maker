"""Outfit-specific colors and wallpaper plans, without changing preset records."""
import copy,re
from core import split_tags
COLORS={'指定なし':'','白':'white','黒':'black','赤':'red','青':'blue','緑':'green','黄色':'yellow','紫':'purple','ピンク':'pink','茶色':'brown','灰色':'grey','ベージュ':'beige','紺':'navy blue','水色':'light blue','アイボリー':'ivory','オレンジ':'orange','金色':'gold','銀色':'silver'}
COLOR_NAMES={v:k for k,v in COLORS.items()}
SIZES={
 '指定なし':None,
 '正方形 1024×1024':(1024,1024,1024,1024),
 'FHD 1920×1080':(1920,1080,1280,720),
 'WQHD 2560×1440':(2560,1440,1280,720),
 '4K 3840×2160':(3840,2160,1280,720),
 'ウルトラワイド 2560×1080':(2560,1080,1536,648),
 'ウルトラワイド 3440×1440':(3440,1440,1376,576),
 'スマホ縦長 1080×1920':(1080,1920,720,1280),
}
PLACEMENTS={'指定なし':'','左寄せ':'subject on left','中央':'centered composition','右寄せ':'subject on right'}
def garment_parts(row):
 if row['target']!='positive' or row['tab']!='衣装' or row['category']=='服の色':return []
 return [t for t in split_tags(row['en']) if not t.startswith('<')]
def validate_colors(data):
 if not isinstance(data,dict):raise ValueError('衣装の色データが不正です')
 for key,parts in data.items():
  if not isinstance(key,str) or not isinstance(parts,dict) or any(not isinstance(t,str) or not isinstance(c,str) or c not in COLOR_NAMES for t,c in parts.items()):raise ValueError('衣装の色データが不正です')
 return data
def color_tag(tag,color):
 if not color:return tag
 match=re.fullmatch(r'\((.*):([0-9.]+)\)',tag)
 if match:return '('+color_tag(match.group(1),color)+':'+match.group(2)+')'
 for existing in sorted((c for c in COLOR_NAMES if c),key=len,reverse=True):
  if tag.casefold().startswith(existing+' '):tag=tag[len(existing)+1:];break
 return color+' '+tag
def colorize_rows(rows,colors):
 result=[]
 for row in rows:
  mapping=colors.get(row['id'],{});parts=garment_parts(row)
  if mapping and parts:
   r=copy.deepcopy(row);r['en']=', '.join(color_tag(t,mapping.get(t,'')) for t in split_tags(row['en']))
   names=[COLOR_NAMES[mapping[t]] for t in parts if mapping.get(t,'') in COLOR_NAMES and mapping.get(t,'')]
   if names:r['ja']=row['ja']+'（'+' / '.join(names)+'）'
   result.append(r)
  else:result.append(row)
 return result

def wallpaper_hint(size,width,height):
 plan=SIZES.get(size)
 if plan is None:return '任意の幅・高さをForgeへ手動設定できます。'
 tw,th,_,_=plan
 try:
  w,h=int(width),int(height)
  if w<=0 or h<=0:raise ValueError()
  fx,fy=tw/w,th/h
 except (ValueError,TypeError):return f'完成サイズ {tw}×{th} ／ 幅・高さを入力してください'
 scale=f'{fx:.3g}倍' if abs(fx-fy)<.001 else f'横{fx:.3g}倍・縦{fy:.3g}倍'
 return f'生成 {w}×{h} → 完成 {tw}×{th} ／ {scale}\nForgeで拡大・仕上げ（サイズ設定は手動）'
