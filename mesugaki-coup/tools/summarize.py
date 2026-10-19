"""raw sim JSON (4p, 2-5p, dud0) -> summary JSON for build_analysis.py"""
import json, sys
names={'t1':'おしおき返し','t2':'山札のぞき','t3':'ダサすぎ返し','t4':'まるみえ','t5':'総入れ替え','t6':'みかじめ','t7':'まわして','t8':'値上げ','t9':'♥コレクター','t10':'ルール改変','t11':'みちづれのキス','t12':'仕返し','t13':'山分け','t14':'値下げ','t15':'遺言','t16':'着替え','none':'ハズレ'}
out={}
for key,f in [('sim_4p_dud5',sys.argv[1]),('sim_235_dud5',sys.argv[2]),('sim_4p_dud0',sys.argv[3])]:
    d=json.load(open(f)); st=d['st']; o=d['out']
    base=st['none']['firstWin']/st['none']['first'] if st['none']['first'] else None
    rows=[]
    for id,s in st.items():
        if s['held']==0: continue
        rows.append({'id':id,'name':names[id],'held':s['held'],'heldWin':s['heldWin'],'first':s['first'],'firstWin':s['firstWin'],'last':s['last'],'firstBy':s['firstBy'],'firstByWin':s['firstByWin'],'revive':s.get('revive',0),'reviveWin':s.get('reviveWin',0),'firstp':100*s['firstWin']/max(1,s['first']),'delta':(100*(s['firstWin']/max(1,s['first'])-base) if base else None)})
    rows.sort(key=lambda r:(r['id']=='none', -r['firstp']))
    out[key]={'rows':rows,'games':o['games'],'avgLog':o['turns']/o['games'],'winnerLostLife':o['winnerLostLife']/o['games'],'lifeLoss':o['lifeLossTotal']/o['games']}
json.dump(out, open(sys.argv[4],'w'), ensure_ascii=False); print('summary ok')
