"""Gera cópias isoladas para QA. Não altera os CSVs originais; não executa M/DAX.
Uso: python -B validacao/gerar_casos_desktop.py PASTA_NOVA
"""
from pathlib import Path
from copy import deepcopy
import argparse,csv,json
from validar import load,validate,Invalid

def main():
    p=argparse.ArgumentParser();p.add_argument('destino',type=Path);a=p.parse_args()
    if a.destino.exists():p.error('Use uma pasta nova para não sobrescrever evidências.')
    root=Path(__file__).resolve().parents[1];base=load(root)
    headers={k:list(next(csv.reader((root/(k+'.csv')).open(encoding='utf-8-sig')))) for k in base}
    used={x['disponibilidade_id'] for x in base['chamadas']}
    unused=next(i for i,x in enumerate(base['disponibilidade_atendentes']) if x['disponibilidade_id'] not in used)
    answered=next(i for i,x in enumerate(base['chamadas']) if x['status']=='ATENDIDA')
    cases=[]
    def case(name,code,edit,layer):
        t=deepcopy(base);edit(t)
        try:
            controls=validate(t)
            assert code is None,(name,'não rejeitado')
            outcome={'status':'PASS','controles':controls}
        except Invalid as e:
            assert code and str(e).startswith(code+':'),(name,str(e))
            outcome={'status':'REJEITADO_COMO_ESPERADO','erro':str(e)}
        folder=a.destino/name;folder.mkdir(parents=True)
        for table,rows in t.items():
            with (folder/(table+'.csv')).open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,fieldnames=headers[table]);w.writeheader();w.writerows(rows)
        cases.append({'caso':name,'camada_esperada':layer,'python_executado':outcome,'desktop':'PENDENTE'})
    case('01_duplicidade','DUPLICIDADE',lambda t:t['chamadas'].append(t['chamadas'][0].copy()),'Python e M')
    case('02_referencia','REFERENCIA',lambda t:t['chamadas'][0].update(fila_id='F99'),'Python e M')
    case('03_obrigatorio','OBRIGATORIO',lambda t:t['chamadas'][0].update(entrada_em=''),'Python e M')
    case('04_calendario','CALENDARIO',lambda t:t['chamadas'][0].update(entrada_em='2026-04-01 09:00:00'),'Python e M')
    case('05_duracao','DURACAO',lambda t:t['chamadas'][answered].update(pos_atendimento_segundos='-1'),'Python e M')
    case('06_ocupacao','OCUPACAO_SOBREPOSTA',lambda t:t['chamadas'].append(dict(t['chamadas'][answered],chamada_id='QA_OCUPACAO')),'Python obrigatório; não há bloqueio M equivalente declarado')
    case('07_disp_nao_utilizada','DISP_REFERENCIA',lambda t:t['disponibilidade_atendentes'][unused].update(fila_id='F99'),'Python e M')
    case('08_disp_sobreposta','DISP_SOBREPOSICAO',lambda t:t['disponibilidade_atendentes'].append(dict(t['disponibilidade_atendentes'][0],disponibilidade_id='QA_DISP')),'Python e M')
    case('09_sem_chamadas',None,lambda t:t.update(chamadas=[]),'Python PASS; M deve carregar; DAX: contagens 0, taxas e TMA em branco')
    def empty_bad(t):
        t['chamadas']=[];t['disponibilidade_atendentes'][unused]['fila_id']='F99'
    case('10_sem_chamadas_disp_invalida','DISP_REFERENCIA',empty_bad,'Python e M; validação global não pode depender de chamadas')
    (a.destino/'resultados_python.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'casos':len(cases),'resultado':'PASS','destino':str(a.destino),'M_DAX':'NÃO EXECUTADOS'},ensure_ascii=False))

if __name__=='__main__':main()
