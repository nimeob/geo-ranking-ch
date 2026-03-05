#!/usr/bin/env python3
import json,subprocess,os,sys,re
repo='nimeob/geo-ranking-ch'
# get token
token = subprocess.check_output(['./scripts/gh_app_token.sh']).decode().strip()
os.environ['GH_TOKEN']=token
# list issues
p = subprocess.run(['gh','issue','list','--repo',repo,'--state','open','--json','number,title,labels'],capture_output=True,text=True)
if p.returncode!=0:
    print('ERROR: gh issue list failed')
    print(p.stderr)
    sys.exit(1)
issues=json.loads(p.stdout)
checked_total=len(issues)
labeled=[]
for it in issues:
    if it.get('labels'):
        continue
    num=it['number']; title=it['title']
    # priority
    if re.search(r'P0',title,flags=re.I): pri='priority:P0'
    elif re.search(r'P1',title,flags=re.I): pri='priority:P1'
    elif re.search(r'P2',title,flags=re.I): pri='priority:P2'
    elif re.search(r'P3',title,flags=re.I): pri='priority:P3'
    else: pri='priority:P2'
    # type
    if re.search(r'\b(bug|fehler)\b',title,flags=re.I): typ='bug'
    elif re.search(r'\b(docs|doku|readme)\b',title,flags=re.I): typ='documentation'
    elif re.search(r'\b(test|e2e|smoke)\b',title,flags=re.I): typ='testing'
    else: typ='enhancement'
    # area
    area=''
    if re.search(r'\b(UI|Frontend|React|Svelte|CSS|UX)\b',title,flags=re.I): area='area:ui'
    elif re.search(r'\b(API|Backend|Endpoint|Service|Route)\b',title,flags=re.I): area='area:api'
    labels=['backlog','status:todo',pri,typ]
    if area: labels.append(area)
    # call gh edit
    cmd=['gh','issue','edit',str(num),'--repo',repo,'--add-label']+labels
    # run
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode==0:
        labeled.append(num)
        print(f'Labeled #{num}: {labels}')
    else:
        print(f'Failed to label #{num}:',r.stderr)
print('SUMMARY')
print('checked_total:',checked_total)
print('labeled_count:',len(labeled))
print('labeled_issues:',labeled)
