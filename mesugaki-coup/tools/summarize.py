"""raw sim JSON -> summary JSON for build_analysis.py
usage: summarize.py key=sim.json [key=sim.json ...] [whatif=old_summary.json] out.json
  key は build_analysis.py が参照する条件名（例 basic_p4, basic_p3456, fresh_p4, fresh_p3456, basic_p4_dud0）
ハズレが山に無いときは全カード平均を基準にする"""
import json, sys
import re, os
_idx=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','index.html'),encoding='utf-8').read()
names={m.group(1):m.group(2) for m in re.finditer(r"\{ id:'(t\d+)',\s*name:'([^']+)'", _idx)}; names['none']='ハズレ'
out={}
for arg in sys.argv[1:-1]:
    key,f=arg.split('=',1)
    if key=='whatif': out['whatif']=json.load(open(f))['whatif']; continue   # 前回の summary から what-if をそのまま引き継ぐ
    d=json.load(open(f)); st=d['st']; o=d['out']
    hasDud=st['none']['first']>0
    base=(st['none']['firstWin']/st['none']['first']) if hasDud else (sum(s['firstWin'] for s in st.values())/sum(s['first'] for s in st.values()))
    hbase=(st['none']['heldWin']/st['none']['held']) if hasDud else (sum(s['heldWin'] for s in st.values())/sum(s['held'] for s in st.values()))
    rows=[]
    for id,s in st.items():
        if s['held']==0: continue
        rows.append({'id':id,'name':names.get(id,id),'held':s['held'],'heldWin':s['heldWin'],'first':s['first'],'firstWin':s['firstWin'],'last':s['last'],'firstBy':s['firstBy'],'firstByWin':s['firstByWin'],'revive':s.get('revive',0),'reviveWin':s.get('reviveWin',0),'firstp':100*s['firstWin']/max(1,s['first']),'delta':100*(s['firstWin']/max(1,s['first'])-base)})
    rows.sort(key=lambda r:(r['id']=='none', -r['firstp']))
    out[key]={'rows':rows,'games':o['games'],'avgLog':o['turns']/o['games'],'winnerLostLife':o['winnerLostLife']/o['games'],'lifeLoss':o['lifeLossTotal']/o['games'],'hasDud':hasDud,'base':base,'heldBase':hbase,'deck':o.get('deck',[])}
json.dump(out, open(sys.argv[-1],'w'), ensure_ascii=False); print('summary ok', list(out))
