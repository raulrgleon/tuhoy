#!/usr/bin/env python3
"""Local editorial TikTok video: source photo in every scene, extractive text, TTS.
No generated news facts, external TTS service, or photo-less fallback.
"""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit
import urllib.request
import wave
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent.parent
RUNTIME=Path('/home/raul/.local/share/tuhoy-video/runtime/bin/python')
VOICE_VERSION='kokoro-em_alex-v1'
KOKORO_PY=Path('/home/raul/.local/share/tuhoy-kokoro-preview/bin/python')
CACHE=ROOT/'data/tiktok-media'

class Paragraphs(HTMLParser):
    def __init__(self): super().__init__(); self.active=False; self.current=[]; self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag=='p': self.active=True; self.current=[]
    def handle_data(self,data):
        if self.active:self.current.append(data)
    def handle_endtag(self,tag):
        if tag=='p' and self.active:
            self.items.append(' '.join(''.join(self.current).split())); self.active=False

def build_scenes(post):
    parser=Paragraphs(); parser.feed(post.get('html') or '')
    texts=[]
    # Keep complete source sentences and cap narration for a short video.
    for para in parser.items:
        if re.match(r'^(Fuentes?\b|Foto:|Crédito|https?://)',para,re.I): break
        for sent in re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])',para):
            words=sent.split()
            if 7<=len(words)<=35 and sent not in texts:
                texts.append(sent)
            if len(texts)==4: break
        if len(texts)==4: break
    if len(texts)<4: raise ValueError('Not enough complete source sentences; skip video')
    return [{'heading':post['title'] if i==0 else ['','LA HISTORIA','EN DETALLE','OTRA CLAVE'][i], 'text':t} for i,t in enumerate(texts)]

def safe_image(url):
    u=urlsplit(url)
    if u.scheme!='https' or u.hostname!='tuhoy.com' or not u.path.startswith('/content/images/'):
        raise ValueError('Only TuHoy HTTPS article images are allowed')
    req=urllib.request.Request(url,headers={'User-Agent':'TuHoyVideo/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        if urlsplit(r.url).hostname!='tuhoy.com':raise ValueError('Image redirect outside TuHoy')
        blob=r.read(20*1024*1024+1)
    if len(blob)>20*1024*1024:raise ValueError('Image exceeds 20 MB')
    return blob

def draw_text(d,text,x,y,font,width,color):
    lines=[];line=''
    for word in text.split():
        trial=(line+' '+word).strip()
        if d.textlength(trial,font=font)>width and line:lines.append(line);line=word
        else:line=trial
    if line:lines.append(line)
    for line in lines:
        d.text((x,y),line,font=font,fill=color);y+=font.size+12
    return y

def render(post,outdir):
    from PIL import Image,ImageDraw,ImageFont,ImageOps
    scenes=build_scenes(post)
    image=Image.open(io.BytesIO(safe_image(post.get('feature_image') or ''))).convert('RGB')
    outdir.mkdir(parents=True,exist_ok=True)
    cream='#F4F0E7'; ink='#191B19'; red='#B22D25'
    serif='/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'
    sans='/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
    bold='/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
    def font(size,face=bold): return ImageFont.truetype(face,size)
    date=datetime.fromisoformat(post['published_at'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Chicago')).strftime('%d/%m/%Y')
    subprocess.run([str(KOKORO_PY),str(ROOT/'scripts/kokoro_voice.py')],input=json.dumps({'texts':[s['text'] for s in scenes],'output':str(outdir)}),text=True,check=True,timeout=240)
    clips=[]; audios=[]; duration=0
    for i,scene in enumerate(scenes):
        wav=outdir/f'voice-{i}.wav'
        with wave.open(str(wav)) as f: dt=f.getnframes()/f.getframerate()
        if not 1<dt<30:raise ValueError('Narration scene outside limits')
        duration+=dt;audios.append(wav)
        # Break narration at word boundaries; captions are exact, not invented summaries.
        chunks=[];buf=[]
        for word in scene['text'].split():
            if len(' '.join(buf+[word]))>100 and buf:chunks.append(' '.join(buf));buf=[]
            buf.append(word)
        if buf:chunks.append(' '.join(buf))
        total=sum(len(c.split()) for c in chunks)
        for j,caption in enumerate(chunks):
            im=Image.new('RGB',(1080,1920),cream); d=ImageDraw.Draw(im)
            d.text((78,66),'TuHoy',font=font(68,serif),fill=ink);d.text((785,96),date,font=font(27,sans),fill=ink)
            d.line((78,166,1000,166),fill=ink,width=3)
            # Each scene includes the real article image, with modest framing variation.
            im.paste(ImageOps.fit(image,(924,520),centering=(0.5,0.35+i*0.1)),(78,210))
            credit=html.unescape(re.sub('<[^>]+>','',post.get('feature_image_caption') or 'Imagen del artículo'))
            d.text((78,750),credit[:80],font=font(22,sans),fill='#555951')
            d.text((78,812),f'{i+1:02} / NOTICIAS EN ESPAÑOL',font=font(27),fill=red)
            title_size=70
            while title_size>=40:
                scratch=ImageDraw.Draw(Image.new('RGB',(1080,1920)))
                end=draw_text(scratch,scene['heading'],78,875,font(title_size,serif),880,ink)
                if end<=1188:break
                title_size-=2
            if end>1188:raise ValueError('Headline cannot fit safely')
            draw_text(d,scene['heading'],78,875,font(title_size,serif),880,ink)
            d.rounded_rectangle((60,1240,1000,1630),radius=20,fill=ink)
            end=draw_text(d,caption,90,1285,font(47),830,cream)
            if end>1605:raise ValueError('Caption cannot fit safely')
            for k in range(4):d.rounded_rectangle((78+k*231,1688,78+k*231+205,1695),radius=3,fill=red if k<=i else '#D0CCC3')
            d.text((78,1745),'CONTEXTO Y FUENTES EN TUHOY.COM',font=font(25),fill='#555951')
            d.text((78,1790),'Voz sintética · resumen del artículo',font=font(24,sans),fill='#555951')
            d.text((930,1785),f'{i+1}/4',font=font(29),fill=red)
            frame=outdir/f'scene-{i}-{j}.png';im.save(frame)
            clips.append((frame,dt*len(caption.split())/total))
    if not 8<duration<110:raise ValueError('Video duration outside limits')
    listing=outdir/'frames.txt';listing.write_text(''.join(f"file '{p}'\nduration {dt:.6f}\n" for p,dt in clips)+f"file '{clips[-1][0]}'\n")
    alist=outdir/'audio.txt';alist.write_text(''.join(f"file '{p}'\n" for p in audios))
    subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(alist),'-c:a','pcm_s16le',str(outdir/'audio.wav')],check=True,timeout=60)
    video=outdir/'video.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-threads','2','-f','concat','-safe','0','-i',str(listing),'-i',str(outdir/'audio.wav'),'-c:v','libx264','-threads','2','-preset','fast','-crf','23','-r','30','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(video)],check=True,timeout=300)
    if video.stat().st_size>20*1024*1024:raise ValueError('Video exceeds 20 MB')
    (outdir/'manifest.json').write_text(json.dumps({'source':post['url'],'scenes':scenes,'duration':duration,'images_per_scene':True,'voice':VOICE_VERSION},ensure_ascii=False,indent=2))
    return video

def ghost_media_root():
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                if b'url=https://tuhoy.com' in (p/'environ').read_bytes().split(b'\0'):
                    target=p/'root/var/lib/ghost/content/media'
                    if target.is_dir():return target
            except (PermissionError,FileNotFoundError,ProcessLookupError):pass
    raise RuntimeError('Ghost media volume unavailable; no post sent')

def create_asset(post_id):
    if not re.fullmatch('[a-f0-9]{24}',post_id):raise ValueError('Invalid Ghost post id')
    # Reuse only a fully exported video; model/render failures never fall back to a photo.
    import daily_edition as daily
    import writer
    env=writer.load_env();g=daily.Ghost(env['GHOST_URL'],env['GHOST_ADMIN_API_KEY'])
    status,data=g.get(f'/posts/{post_id}/?formats=html&include=tags&fields=id,title,html,feature_image,feature_image_caption,published_at,url,status')
    if status!=200 or not data.get('posts') or data['posts'][0]['status']!='published':raise RuntimeError('Published article unavailable')
    post=data['posts'][0]; digest=hashlib.sha256(json.dumps({'post':post,'voice':VOICE_VERSION},sort_keys=True).encode()).hexdigest()[:12]
    output=CACHE/(post_id+'-'+digest)
    if not (output/'manifest.json').exists() or not (output/'video.mp4').exists():render(post,output)
    part=datetime.now(ZoneInfo('America/Chicago')).strftime('%Y/%m')
    name=f'tuhoy-{post_id}-{digest}.mp4';dest=ghost_media_root()/part/name;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():
        temp=dest.with_suffix('.tmp');shutil.copyfile(output/'video.mp4',temp);os.chmod(temp,0o644);os.replace(temp,dest)
    url=f'https://tuhoy.com/content/media/{part}/{name}'
    req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':daily.BROWSER})
    with urllib.request.urlopen(req,timeout=30) as r:
        if r.status!=200:raise RuntimeError('Public video unavailable')
    return url

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('post_id');args=ap.parse_args();print(create_asset(args.post_id))
