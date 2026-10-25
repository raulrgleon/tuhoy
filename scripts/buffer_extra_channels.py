#!/usr/bin/env python3
"""TuHoy Threads and YouTube workers. Only explicitly pinned channels can publish."""
import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import buffer_tiktok as buffer
import tiktok_posts as tt
from editorial_controls import edition_lock

ROOT=Path(__file__).resolve().parent.parent
CONFIG=ROOT/'data/buffer-extra-channels.json'
PLATFORMS=('threads','youtube')

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.extra-')
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(data,stream,ensure_ascii=False)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def due(queue,items,enabled_at,now):
    start=datetime.fromisoformat(enabled_at)
    return sorted([x for x in queue if x['id'] not in items and start<=datetime.fromisoformat(x['hora'])<=now and now-datetime.fromisoformat(x['hora'])<=timedelta(hours=2)],key=lambda x:x['hora'])

def validate_channel(channel,platform):
    name=re.sub(r'[^a-z0-9]','',channel.get('name','').lower())
    identity_ok = channel.get('serviceId')=='UCPvMwculzE04EAjeSPpilVw' if platform=='youtube' else name=='tuhoynoticias'
    if channel.get('service')!=platform or not identity_ok or channel.get('isDisconnected') or channel.get('isQueuePaused') or channel.get('isLocked'):
        raise RuntimeError('Wrong or unavailable TuHoy channel; publishing stopped')

def payload(platform,channel,item,video=None):
    url=item['url']
    if not url.startswith('https://tuhoy.com/'):
        raise ValueError('Only TuHoy articles can be published')
    title=(item.get('titulo') or '').strip()
    if not title:raise ValueError('Missing headline')
    data={'channelId':channel,'text':title[:350]+'\n\n'+url,'schedulingType':'automatic','mode':'shareNow'}
    if platform=='threads':
        data['metadata']={'threads':{'linkAttachment':{'url':url}}}
    elif platform=='youtube':
        if not video or not video.startswith('https://tuhoy.com/content/media/') or not video.endswith('.mp4'):
            raise ValueError('Missing TuHoy video')
        data['text']=tt.description_of(item)
        data['assets']=[{'video':{'url':video}}]
        data['metadata']={'youtube':{'title':tt.clip_utf16(title,90),'categoryId':'25','privacy':'public','madeForKids':False,'notifySubscribers':False,'isAiGenerated':True}}
    else:raise ValueError('Unsupported destination')
    return data

def run(platform,dry_run=False):
    config=tt.load(CONFIG,{}).get(platform)
    if not config or not config.get('enabled'):
        print(platform+': awaiting verified channel connection; no API call');return
    path=ROOT/('data/buffer-'+platform+'.json')
    with edition_lock(ROOT/('data/buffer-'+platform+'.lock')) as acquired:
        if not acquired:return
        state=tt.load(path,{'items':{}});items=state['items'];now=datetime.now(timezone.utc)
        pending=[x for x in items.values() if x.get('status')!='sent']
        candidates=due(tt.load(tt.X_QUEUE,{}).get('pendientes',[]),items,config['enabled_at'],now)
        if dry_run:
            print(platform+': eligible='+str(len(candidates))+', unresolved='+str(len(pending)));return
        if not pending and not candidates:return
        channel=buffer.api('query($id:ChannelId!){channel(input:{id:$id}){id name serviceId service isDisconnected isQueuePaused isLocked}}',{'id':config['id']})['channel']
        validate_channel(channel,platform)
        for item in pending:
            if not item.get('buffer_id'):
                print(platform+': uncertain post isolated; other news may continue');continue
            post=buffer.api('query($id:PostId!){post(input:{id:$id}){id status externalLink}}',{'id':item['buffer_id']})['post']
            item['status']='sent' if post.get('status')=='sent' and post.get('externalLink') else post.get('status','unknown')
            item['external_link']=post.get('externalLink');save(path,state)
            # This recorded item cannot block unrelated fresh articles.
        if not candidates:return
        if sum(datetime.fromisoformat(x['created_at'])>now-timedelta(hours=24) for x in items.values())>=10:return
        item=candidates[0]
        recent=buffer.api('query($org:OrganizationId!,$cid:ChannelId!){posts(first:100,input:{organizationId:$org,filter:{channelIds:[$cid]}}){edges{node{id text status externalLink}}}}',{'org':buffer.ORG,'cid':config['id']})['posts']['edges']
        found=next((x['node'] for x in recent if item['url'] in x['node'].get('text','')),None)
        if found:
            items[item['id']]={'status':'sent' if found['status']=='sent' and found.get('externalLink') else found['status'],'buffer_id':found['id'],'url':item['url'],'created_at':now.isoformat()};save(path,state);return
        video=buffer.video_asset(item['id']) if platform=='youtube' else None
        data=payload(platform,config['id'],item,video)
        items[item['id']]={'status':'submitting','url':item['url'],'created_at':now.isoformat()};save(path,state)
        result=buffer.api('mutation($input:CreatePostInput!){createPost(input:$input){__typename ... on PostActionSuccess{post{id status externalLink}} ... on MutationError{message}}}',{'input':data})['createPost']
        if not result.get('post'):
            print(platform+': submission rejected or uncertain; no automatic retry');return
        post=result['post'];record=items[item['id']];record['buffer_id']=post['id'];record['external_link']=post.get('externalLink');record['status']='sent' if post.get('status')=='sent' and post.get('externalLink') else post.get('status','unknown');save(path,state)
        print(platform+': accepted by Buffer; status='+record['status'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--platform',choices=PLATFORMS,required=True);p.add_argument('--dry-run',action='store_true');a=p.parse_args();run(a.platform,a.dry_run)
