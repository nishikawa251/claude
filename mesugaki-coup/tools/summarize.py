"""raw sim JSON (4p, 3-6p[, dud0]) -> summary JSON for build_analysis.py
usage: summarize.py sim_4p.json sim_3456.json [sim_4p_dud0.json] out.json
ハズレが山に無いときは全カード平均を基準にする"""
import json, sys
names={'t1':'おしおき返し','t2':'山札のぞき','t3':'ダサすぎ返し','t4':'まるみえ','t5':'総入れ替え','t6':'みかじめ','t7':'まわして','t8':'値上げ','t9':'♥コレクター','t10':'ルール改変','t11':'みちづれのキス','t12':'仕返し','t13':'山分け','t14':'値下げ','t15':'遺言','t16':'着替え','t17':'トリガーチェック','none':'ハズレ'}
out={}
files=[('sim_4p_dud5',sys.argv[1]),('sim_235_dud5',sys.argv[2])]+([('sim_4p_dud0',sys.argv[3])] if len(sys.argv)>4 else [])
for key,f in files:
    d=json.load(open(f)); st=d['st']; o=d['out']
    hasDud=st['none']['first']>0
    base=(st['none']['firstWin']/st['none']['first']) if hasDud else (sum(s['firstWin'] for s in st.values())/sum(s['first'] for s in st.values()))
    hbase=(st['none']['heldWin']/st['none']['held']) if hasDud else (sum(s['heldWin'] for s in st.values())/sum(s['held'] for s in st.values()))
    rows=[]
    for id,s in st.items():
        if s['held']==0: continue
        rows.append({'id':id,'name':names[id],'held':s['held'],'heldWin':s['heldWin'],'first':s['first'],'firstWin':s['firstWin'],'last':s['last'],'firstBy':s['firstBy'],'firstByWin':s['firstByWin'],'revive':s.get('revive',0),'reviveWin':s.get('reviveWin',0),'firstp':100*s['firstWin']/max(1,s['first']),'delta':(100*(s['firstWin']/max(1,s['first'])-base) if base else None)})
    rows.sort(key=lambda r:(r['id']=='none', -r['firstp']))
    out[key]={'rows':rows,'games':o['games'],'avgLog':o['turns']/o['games'],'winnerLostLife':o['winnerLostLife']/o['games'],'lifeLoss':o['lifeLossTotal']/o['games'],'hasDud':hasDud,'base':base,'heldBase':hbase}
json.dump(out, open(sys.argv[-1],'w'), ensure_ascii=False); print('summary ok')
