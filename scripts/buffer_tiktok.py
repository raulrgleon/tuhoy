#!/usr/bin/env python3
"""Send TuHoy's existing news queue only to the pinned TikTok channel via Buffer.
Run through the systemd unit; the API key is provided as a runtime credential.
"""
import argparse
import fcntl
import json
import os
import tempfile
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tiktok_posts as tt
import writer

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / 'data/buffer_tiktok.json'
CHANNEL = '6ad3a8ab778b240e2f3bbc64'
ORG = '6ad3a73659096eb0b758abc7'
FIELDS = 'id status schedulingType externalLink text'

def api(query, variables=None):
    key = (Path(os.environ['CREDENTIALS_DIRECTORY']) / 'buffer-api').read_text().strip()
    req = urllib.request.Request('https://api.buffer.com', data=json.dumps({'query':query,'variables':variables or {}}).encode(), headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if out.get('errors'):
        raise RuntimeError('Buffer GraphQL: '+ '; '.join(e.get('message','error') for e in out['errors']))
    return out['data']

def save(state):
    fd, name = tempfile.mkstemp(dir=STATE.parent, prefix='.buffer-tiktok-')
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd,'w') as f:
            json.dump(state,f,ensure_ascii=False,indent=2)
        os.replace(name,STATE)
    finally:
        if os.path.exists(name): os.unlink(name)

def video_asset(post_id):
    result=subprocess.run(['/home/raul/.local/share/tuhoy-video/runtime/bin/python',str(ROOT/'scripts/tiktok_video.py'),post_id],check=True,capture_output=True,text=True,timeout=600)
    return result.stdout.strip()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); p.add_argument('--reconcile-only', action='store_true'); p.add_argument('--dry-run', action='store_true'); p.add_argument('--post-id'); p.add_argument('--draft',action='store_true'); args=p.parse_args()
    # Idle runs must not consume the free plan's monthly API allowance.
    if not args.check:
        pre=tt.load(STATE, {'items':{}})
        recorded={h['id'] for h in tt.load(tt.TT_QUEUE,{'historial':[]})['historial']} | set(pre['items'])
        current=datetime.now(timezone.utc)
        pending=any(i['status'] not in ('sent','draft') for i in pre['items'].values())
        eligible=any(t['id'] not in recorded and (t['id']==args.post_id if args.post_id else timedelta(0)<=current-datetime.fromisoformat(t['hora'])<=timedelta(hours=2)) for t in tt.load(tt.X_QUEUE,{}).get('pendientes',[]))
        if not pending and not eligible:
            print('No eligible new news; no API requests'); return
    channel=api('query($id:ChannelId!){channel(input:{id:$id}){id name service isDisconnected isQueuePaused}}', {'id':CHANNEL})['channel']
    if channel['name']!='tuhoynoticias' or channel['service']!='tiktok' or channel['isDisconnected'] or channel['isQueuePaused']:
        raise RuntimeError('TikTok channel unavailable; no post sent')
    if args.check: print('TikTok connected; credential valid'); return
    state=tt.load(STATE, {'items':{}})
    # Reconcile pending jobs before submitting another; never resend an uncertain job.
    for item in state['items'].values():
        if item.get('buffer_id') and item['status'] not in ('sent','draft'):
            post=api('query($id:PostId!){post(input:{id:$id}){'+FIELDS+'}}',{'id':item['buffer_id']})['post']
            item['status']=post['status']; item['url']=post.get('externalLink'); save(state)
            print('Buffer status:',post['status'],post.get('externalLink') or '')
        if item['status'] not in ('sent','draft'):
            print('Pending or uncertain submission; no new post sent'); return
    if args.reconcile_only: return
    done={h['id'] for h in tt.load(tt.TT_QUEUE,{'historial':[]})['historial']} | set(state['items'])
    now=datetime.now(timezone.utc)
    queue=tt.load(tt.X_QUEUE,{}).get('pendientes',[])
    candidates=[x for x in queue if x['id'] not in done and (x['id']==args.post_id if args.post_id else timedelta(0)<=now-datetime.fromisoformat(x['hora'])<=timedelta(hours=2))]
    if not candidates: print('No eligible new news'); return
    t=sorted(candidates,key=lambda x:x['hora'])[0]
    if args.dry_run: print('Eligible news:',t['titulo']); return
    # Check Buffer history as well as local state, to avoid duplicates across retries.
    recent=api('query($org:OrganizationId!,$cid:ChannelId!){posts(first:100,input:{organizationId:$org,filter:{channelIds:[$cid]}}){edges{node{'+FIELDS+'}}}}',{'org':ORG,'cid':CHANNEL})['posts']['edges']
    if any(t['url'] in e['node']['text'] for e in recent):
        print('Already present in Buffer; no duplicate sent'); return
    video=video_asset(t['id'])
    if not video.startswith('https://tuhoy.com/content/media/') or not video.endswith('.mp4'):
        raise RuntimeError('Missing TuHoy HTTPS video; no post sent')
    payload={'channelId':CHANNEL,'text':tt.description_of(t),'assets':[{'video':{'url':video}}], 'metadata':{'tiktok':{'isAiGenerated':True}},'schedulingType':'automatic','mode':'shareNow','saveToDraft':args.draft}
    # Persist before network I/O. A lost response pauses publishing for reconciliation.
    state['items'][t['id']]={'status':'submitting','created_at':now.isoformat(),'url':t['url'],'format':'editorial-video-v1','video_url':video}; save(state)
    out=api('mutation($input:CreatePostInput!){createPost(input:$input){__typename ... on PostActionSuccess{post{'+FIELDS+'}} ... on MutationError{message}}}',{'input':payload})['createPost']
    if 'post' not in out:
        state['items'][t['id']]['status']='rejected'; save(state)
        raise RuntimeError(out.get('message','Buffer rejected post'))
    post=out['post']; state['items'][t['id']].update(buffer_id=post['id'],status=post['status'],url=post.get('externalLink')); save(state)
    print('Buffer accepted:',post['status'],'mode:',post['schedulingType'])

if __name__=='__main__':
    with (ROOT/'data/buffer_tiktok.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        main()
