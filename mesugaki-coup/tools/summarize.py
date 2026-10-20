"""raw sim JSON -> summary JSON for build_analysis.py
usage: summarize.py key=sim.json [key=sim.json ...] out.json
  key は build_analysis.py が参照する条件名（例 basic_p4, basic_p3456, fresh_p4, fresh_p3456, basic_p4_dud0）
ハズレが山に無いときは全カード平均を基準にする"""
import json, sys
names={'t1':'おしおき返し','t2':'山札のぞき','t3':'ダサすぎ返し','t4':'まるみえ','t5':'総入れ替え','t6':'みかじめ','t7':'まわして','t8':'値上げ','t9':'♥コレクター','t10':'ルール改変','t11':'みちづれのキス','t12':'仕返し','t13':'山分け','t14':'値下げ','t15':'遺言','t16':'着替え','t17':'トリガーチェック','t18':'かくれんぼ','t19':'無敵宣言','t20':'口止め料','t21':'おねだり','t22':'ボディガード','t23':'人気者','t24':'復讐の誓い','t25':'ごほうび','t26':'内緒話','t27':'お色直し','t28':'道連れ','t29':'はね返し','t30':'身代わり','t31':'返金','t32':'盾の値段','t33':'安売り','t34':'連射','t35':'強制徴収','t36':'ざこ免除','t37':'よわよわ税','t38':'疑いの目','t39':'は？よわ','t40':'一人占め','none':'ハズレ'}
out={}
for arg in sys.argv[1:-1]:
    key,f=arg.split('=',1)
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
