"""Offline character/color recognition. Input/output are local JSON files."""
import argparse,json,re,io
from pathlib import Path
import cv2,numpy as np
from PIL import Image
import ddddocr

def recognize(image_path, prompt):
    match=re.search(r'大写\s*([A-Z])',prompt)
    if not match:
        return {'status':'unsupported','reason':'Only explicit uppercase character targets supported'}
    target=match.group(1)
    ranges={'灰':[(0,0,35),(179,70,205)],'红':[(0,80,50),(12,255,255)],
            '黄':[(15,70,60),(40,255,255)],'绿':[(35,60,40),(90,255,255)],
            '蓝':[(90,65,40),(135,255,255)]}
    color=next((c for c in ranges if c+'色' in prompt),None)
    if color is None:return {'status':'unsupported','reason':'Unsupported color'}
    rgb=np.array(Image.open(image_path).convert('RGB'));hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    lo,hi=ranges[color];mask=cv2.inRange(hsv,np.array(lo),np.array(hi))
    if color=='红':mask|=cv2.inRange(hsv,np.array([170,80,50]),np.array([179,255,255]))
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask)
    engines=[ddddocr.DdddOcr(show_ad=False),ddddocr.DdddOcr(show_ad=False,beta=True)]
    candidates=[]
    for i in range(1,count):
        x,y,w,h,area=[int(v) for v in stats[i]]
        if area<40 or w<6 or h<12 or w>rgb.shape[1]*.65 or h>rgb.shape[0]*.95:continue
        crop=np.full((h+12,w+12,3),255,dtype=np.uint8)
        crop[6:h+6,6:w+6][labels[y:y+h,x:x+w]==i]=0
        im=Image.fromarray(crop).resize(((w+12)*3,(h+12)*3))
        buf=io.BytesIO();im.save(buf,format='PNG')
        readings=[e.classification(buf.getvalue()) for e in engines]
        candidates.append({'box':[x,y,w,h],'readings':readings,'agreed':all(r.upper()==target for r in readings) and target in readings})
    hits=[c for c in candidates if c['agreed']]
    result={'status':'ready' if len(hits)==1 else 'ambiguous','target':target,'color':color,
            'size':[rgb.shape[1],rgb.shape[0]],'candidates':candidates}
    if len(hits)==1:
        x,y,w,h=hits[0]['box'];result['point']=[x+w/2,y+h/2]
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('prompt');p.add_argument('output');a=p.parse_args()
    Path(a.output).write_text(json.dumps(recognize(a.image,a.prompt),ensure_ascii=False,indent=2))
