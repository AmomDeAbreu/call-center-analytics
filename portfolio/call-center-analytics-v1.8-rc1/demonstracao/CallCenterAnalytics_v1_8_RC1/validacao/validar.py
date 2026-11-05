"""Validador da base demonstrativa; Python 3.10+, somente biblioteca padrão.
Não reproduz o gerador, FIFO ou o motor Power Query. Códigos estáveis de erro.
"""
import argparse,csv,json,hashlib,sys
from pathlib import Path
from datetime import datetime,timedelta,date,time
from collections import defaultdict

class Invalid(ValueError): pass
def require(ok,code,detail=''):
    if not ok: raise Invalid(f'{code}: {detail}')
def dt(value): return datetime.strptime(value,'%Y-%m-%d %H:%M:%S')
def load(folder):
    return {name:list(csv.DictReader((folder/(name+'.csv')).open(encoding='utf-8-sig',newline=''))) for name in ['chamadas','filas','atendentes','disponibilidade_atendentes']}
def unique(rows,key):
    ids=[r[key].strip() for r in rows]
    require(all(ids),'OBRIGATORIO',key)
    require(len(ids)==len(set(ids)),'DUPLICIDADE',key)
    return set(ids)
def overlaps(intervals,code):
    for agent,items in intervals.items():
        end=None
        for start,finish,ident in sorted(items):
            require(end is None or start>=end,code,f'{agent}/{ident}')
            end=finish if end is None else max(end,finish)
def validate(t):
    filas=unique(t['filas'],'fila_id');agents=unique(t['atendentes'],'atendente_id')
    unique(t['chamadas'],'chamada_id');unique(t['disponibilidade_atendentes'],'disponibilidade_id')
    for table,field in [('filas','fila_nome'),('atendentes','atendente_nome')]:
        require(all(r[field].strip() for r in t[table]),'OBRIGATORIO',field)
    disps={}; intervals=defaultdict(list)
    for r in t['disponibilidade_atendentes']:
        ident=r['disponibilidade_id'];require(all(v.strip() for v in r.values()),'DISP_OBRIGATORIO',ident)
        require(r['fila_id'] in filas and r['atendente_id'] in agents,'DISP_REFERENCIA',ident)
        start,end=dt(r['inicio_disponibilidade_em']),dt(r['fim_disponibilidade_em'])
        require(start<end and start.date()==end.date(),'DISP_INTERVALO',ident)
        require(date(2026,1,1)<=start.date()<=date(2026,3,31) and start.time()>=time(8) and end.time()<=time(18,30),'DISP_ESCOPO',ident)
        disps[ident]=(r,start,end);intervals[r['atendente_id']].append((start,end,ident))
    overlaps(intervals,'DISP_SOBREPOSICAO');occupancy=defaultdict(list);answered=0;total=0;sla=0
    for r in t['chamadas']:
        ident=r['chamada_id'];required=['fila_id','entrada_em','saida_em','status','tolerancia_espera_segundos','duracao_contato_planejada_segundos','pos_atendimento_planejado_segundos']
        require(all(r[k].strip() for k in required),'OBRIGATORIO',ident)
        require(r['fila_id'] in filas,'REFERENCIA',ident)
        start,end=dt(r['entrada_em']),dt(r['saida_em']);tol=int(r['tolerancia_espera_segundos']);contact=int(r['duracao_contato_planejada_segundos']);post=int(r['pos_atendimento_planejado_segundos'])
        require(date(2026,1,1)<=start.date()<=date(2026,3,31),'CALENDARIO',ident)
        require(time(8)<=start.time()<time(18) and end.date()==start.date(),'HORARIO',ident)
        require(5<=tol<=600,'TOLERANCIA',ident)
        lo,hi={'F01':(30,300),'F02':(180,1200),'F03':(120,900)}[r['fila_id']]
        require(lo<=contact<=hi and 0<=post<=180,'DURACAO',ident)
        limit=start+timedelta(seconds=tol);close=datetime.combine(start.date(),time(18))
        fields=['atendente_id','disponibilidade_id','inicio_atendimento_em','pos_atendimento_segundos']
        if r['status']=='ATENDIDA':
            require(all(r[k].strip() for k in fields) and not r['motivo_abandono'],'CONDICIONAL',ident)
            require(r['atendente_id'] in agents and r['disponibilidade_id'] in disps,'REFERENCIA',ident)
            begin=dt(r['inicio_atendimento_em']);actual=int(r['pos_atendimento_segundos']);finish=end+timedelta(seconds=actual)
            require(start<=begin<=limit and begin<close and end>begin,'HORARIO',ident)
            require((end-begin).total_seconds()==contact and actual==post,'DURACAO',ident)
            d,ds,de=disps[r['disponibilidade_id']]
            require(d['fila_id']==r['fila_id'] and d['atendente_id']==r['atendente_id'] and ds<=begin and finish<=de and finish<=close+timedelta(minutes=30),'CONTENCAO',ident)
            occupancy[r['atendente_id']].append((begin,finish,ident));answered+=1;total+=contact+post;sla+=int((begin-start).total_seconds()<=20)
        else:
            require(r['status']=='ABANDONADA','STATUS',ident)
            require(all(not r[k] for k in fields),'CONDICIONAL',ident)
            require(end>start and end==min(limit,close),'ABANDONO_INSTANTE',ident)
            require(r['motivo_abandono']==('DESISTENCIA' if limit<close else 'FECHAMENTO'),'ABANDONO_MOTIVO',ident)
    overlaps(occupancy,'OCUPACAO_SOBREPOSTA');n=len(t['chamadas'])
    return {'recebidas':n,'atendidas':answered,'abandonadas':n-answered,'taxa_abandono':(n-answered)/n if n else None,'tma_segundos':total/answered if answered else None,'atendidas_20s':sla,'sla':sla/n if n else None}
def main():
    p=argparse.ArgumentParser();p.add_argument('pasta',type=Path);a=p.parse_args()
    try:
        result=validate(load(a.pasta));result['sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(a.pasta.glob('*.csv'))}
        print(json.dumps({'status':'PASS','controles':result},ensure_ascii=False,indent=2));return 0
    except (Invalid,ValueError,KeyError,OSError,TypeError) as exc:
        print(json.dumps({'status':'FAIL','erro':str(exc)},ensure_ascii=False));return 1
if __name__=='__main__':sys.exit(main())
