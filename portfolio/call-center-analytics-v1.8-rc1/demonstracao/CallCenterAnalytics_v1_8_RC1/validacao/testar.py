"""Testes novos do validador externo, não a suíte original do simulador."""
from validar import load,validate,Invalid
from pathlib import Path
from copy import deepcopy
import json
base=load(Path(__file__).resolve().parents[1]);results=[]
def test(name,code,edit):
    t=deepcopy(base);edit(t)
    try:validate(t)
    except Invalid as e:
        assert str(e).startswith(code+':'),(name,str(e));results.append({'caso':name,'resultado':'PASS','rejeicao':str(e)})
    else:raise AssertionError(name+' não rejeitado')
assert validate(base)['atendidas']==1959
results.append({'caso':'base original','resultado':'PASS'})
test('chamada duplicada','DUPLICIDADE',lambda t:t['chamadas'].append(t['chamadas'][0].copy()))
test('fila desconhecida','REFERENCIA',lambda t:t['chamadas'][0].update(fila_id='F99'))
test('obrigatorio vazio','OBRIGATORIO',lambda t:t['chamadas'][0].update(entrada_em=''))
test('01 abril','CALENDARIO',lambda t:t['chamadas'][0].update(entrada_em='2026-04-01 09:00:00'))
test('pos negativo','DURACAO',lambda t:t['chamadas'][0].update(pos_atendimento_segundos='-1'))
test('ocupacao sobreposta','OCUPACAO_SOBREPOSTA',lambda t:t['chamadas'].append(dict(t['chamadas'][0],chamada_id='CH_NOVA')))
used={r['disponibilidade_id'] for r in base['chamadas']};idx=next(i for i,r in enumerate(base['disponibilidade_atendentes']) if r['disponibilidade_id'] not in used)
test('disponibilidade nao utilizada com fila desconhecida','DISP_REFERENCIA',lambda t:t['disponibilidade_atendentes'][idx].update(fila_id='F99'))
test('disponibilidade nao utilizada invertida','DISP_INTERVALO',lambda t:t['disponibilidade_atendentes'][idx].update(fim_disponibilidade_em=t['disponibilidade_atendentes'][idx]['inicio_disponibilidade_em']))
test('nova disponibilidade nao referenciada sobreposta','DISP_SOBREPOSICAO',lambda t:t['disponibilidade_atendentes'].append(dict(t['disponibilidade_atendentes'][0],disponibilidade_id='DISP_NOVA')))
test('disponibilidade duplicada','DUPLICIDADE',lambda t:t['disponibilidade_atendentes'].append(t['disponibilidade_atendentes'][0].copy()))
empty=deepcopy(base);empty['chamadas']=[];assert validate(empty)['recebidas']==0
results.append({'caso':'sem chamadas, disponibilidades ainda validadas','resultado':'PASS'})
def empty_bad(t):
    t['chamadas']=[];t['disponibilidade_atendentes'][0]['fila_id']='F99'
test('sem chamadas e disponibilidade invalida','DISP_REFERENCIA',empty_bad)
print(json.dumps({'camada':'Python; não comprova execução M','testes':results},ensure_ascii=False,indent=2))
