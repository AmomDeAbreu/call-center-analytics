"""Controles SQL independentes + inspeção estrutural. NÃO executa DAX/M/Desktop.
Python 3.10+, biblioteca padrão. Não modifica arquivos. Use python -B.
"""
from pathlib import Path
import csv,json,sqlite3,re,sys
from fractions import Fraction
from datetime import datetime
R=Path(__file__).resolve().parents[1]
checks=[]
def check(name,actual,expected,layer):
    ok=actual==expected
    checks.append({'teste':name,'camada':layer,'esperado':expected,'observado':actual,'resultado':'PASSOU' if ok else 'FALHOU'})
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    db=sqlite3.connect(':memory:');tables={}
    for name in ['chamadas','filas','atendentes','disponibilidade_atendentes']:
        with (R/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);cols=reader.fieldnames;rows=list(reader);tables[name]=rows
        db.execute(f'CREATE TABLE "{name}" ('+','.join('"'+c+'" TEXT' for c in cols)+')')
        db.executemany(f'INSERT INTO "{name}" VALUES ('+','.join('?' for _ in cols)+')',[[r[c] for c in cols] for r in rows])
    def metrics(where='1=1',args=()):
        n,a,seconds,sla=db.execute('''SELECT COUNT(*),
          COALESCE(SUM(status='ATENDIDA'),0),
          COALESCE(SUM(CASE WHEN status='ATENDIDA' THEN CAST(strftime('%s',saida_em) AS INTEGER)-CAST(strftime('%s',inicio_atendimento_em) AS INTEGER)+CAST(pos_atendimento_segundos AS INTEGER) ELSE 0 END),0),
          COALESCE(SUM(status='ATENDIDA' AND CAST(strftime('%s',inicio_atendimento_em) AS INTEGER)-CAST(strftime('%s',entrada_em) AS INTEGER)<=20),0)
          FROM chamadas WHERE '''+where,args).fetchone()
        return {'recebidas':n,'atendidas':a,'abandonadas':n-a,'tempo_total_s':seconds,'ate_20s':sla,'tma_s_exato':str(Fraction(seconds,a)) if a else None,'tma_min_exato':str(Fraction(seconds,a*60)) if a else None,'abandono_exato':str(Fraction(n-a,n)) if n else None,'sla_exato':str(Fraction(sla,n)) if n else None}
    base=metrics();controls={'global':base,'F02':metrics('fila_id=?',('F02',)),'fevereiro':metrics("entrada_em >= ? AND entrada_em < ?",('2026-02-01','2026-03-01')),'AT01':metrics('atendente_id=?',('AT01',))}
    for scope,expected in [('global',{'recebidas':3000,'atendidas':1959,'abandonadas':1041,'ate_20s':1846}),('F02',{'recebidas':1070,'atendidas':655}),('fevereiro',{'recebidas':889,'atendidas':574}),('AT01',{'atendidas':244})]:
        check(scope,{k:controls[scope][k] for k in expected},expected,'SQL nos CSVs; não interação Desktop')
    # Actual durations vs independent planned-duration total, both integer seconds.
    planned=db.execute("SELECT SUM(CAST(duracao_contato_planejada_segundos AS INTEGER)+CAST(pos_atendimento_planejado_segundos AS INTEGER)) FROM chamadas WHERE status='ATENDIDA'").fetchone()[0]
    check('tempo realizado igual ao planejado',base['tempo_total_s'],planned,'SQL nos CSVs')
    check('abandono exato',base['abandono_exato'],'347/1000','SQL nos CSVs')
    check('SLA exato',base['sla_exato'],'923/1500','SQL nos CSVs')
    check('TMA arredondado 2 casas para conferência',f"{float(Fraction(base['tma_min_exato'])):.2f}",'8.01','Controle numérico Python; não formatação visual')
    empty=metrics('1=0');check('contexto vazio',[empty[k] for k in ['recebidas','atendidas','tma_s_exato','abandono_exato','sla_exato']],[0,0,None,None,None],'SQL nos CSVs')
    aband=metrics("entrada_em >= ? AND entrada_em < ? AND fila_id=?",("2026-01-04","2026-01-05","F02"));check('somente abandonadas',[aband[k] for k in ['atendidas','tma_s_exato','abandono_exato','sla_exato']],[0,None,'1','0'],'SQL: 04/01/2026, F02; sem filtro status; execução DAX pendente')
    check('horas existentes', [v[0] for v in db.execute("SELECT DISTINCT CAST(substr(entrada_em,12,2) AS INTEGER) FROM chamadas ORDER BY 1")],list(range(8,18)),'SQL nos CSVs')
    check('datas com chamadas',db.execute('SELECT COUNT(DISTINCT substr(entrada_em,1,10)) FROM chamadas').fetchone()[0],90,'SQL nos CSVs')
    agents=[v[0] for v in db.execute("SELECT DISTINCT atendente_id FROM chamadas WHERE status='ATENDIDA' ORDER BY 1")]
    check('oito profissionais com atendimentos',agents,[f'AT{i:02}' for i in range(1,9)],'SQL nos CSVs')
    by_agent=[{'atendente':a,**metrics('atendente_id=?',(a,))} for a in agents]
    check('soma dos atendimentos por profissional',sum(x['atendidas'] for x in by_agent),1959,'SQL nos CSVs')
    check('TMA ponderado consolidado',str(Fraction(sum(x['tempo_total_s'] for x in by_agent),sum(x['atendidas'] for x in by_agent))),base['tma_s_exato'],'SQL nos CSVs')
    for table,key,n in [('chamadas','chamada_id',3000),('filas','fila_id',3),('atendentes','atendente_id',8),('disponibilidade_atendentes','disponibilidade_id',1110)]:
        check('chaves '+table,list(db.execute(f'SELECT COUNT(*),COUNT(DISTINCT {key}),SUM({key}="") FROM {table}').fetchone()),[n,n,0],'SQL nos CSVs')
    missing=db.execute("SELECT COUNT(*) FROM chamadas c LEFT JOIN filas f ON c.fila_id=f.fila_id LEFT JOIN atendentes a ON c.atendente_id=a.atendente_id WHERE f.fila_id IS NULL OR (c.status='ATENDIDA' AND a.atendente_id IS NULL)").fetchone()[0]
    check('referências fila/atendente',missing,0,'SQL nos CSVs')
    # Independently compare every pair; do not reuse validar.py implementation.
    for label,table,ident,begin,end in [('disponibilidade','disponibilidade_atendentes','disponibilidade_id','inicio_disponibilidade_em','fim_disponibilidade_em')]:
        count=db.execute(f'SELECT COUNT(*) FROM {table} a JOIN {table} b ON a.{ident}<b.{ident} AND a.atendente_id=b.atendente_id AND a.{begin}<b.{end} AND b.{begin}<a.{end}').fetchone()[0]
        check('sobreposições por pares '+label,count,0,'SQL nos CSVs')
    db.execute("CREATE VIEW ocupacoes AS SELECT chamada_id,atendente_id,inicio_atendimento_em AS inicio,datetime(saida_em,'+'||pos_atendimento_segundos||' seconds') AS fim FROM chamadas WHERE status='ATENDIDA'")
    check('sobreposições por pares ocupação',db.execute('SELECT COUNT(*) FROM ocupacoes a JOIN ocupacoes b ON a.chamada_id<b.chamada_id AND a.atendente_id=b.atendente_id AND a.inicio<b.fim AND b.inicio<a.fim').fetchone()[0],0,'SQL nos CSVs')
    reportroot=R/'projeto/CallCenterAnalytics.Report';definition=reportroot/'definition';model=R/'projeto/CallCenterAnalytics.SemanticModel/definition'
    report=read(definition/'report.json');check('localidade relatório',report['settings'].get('locale'),'pt-BR','Estrutura PBIR; renderização pendente')
    check('cultura modelo','\tculture: pt-BR' in (model/'model.tmdl').read_text(),True,'Estrutura TMDL')
    check('página inicial',read(definition/'pages/pages.json')['activePageName'],'visao_geral','Estrutura PBIR')
    for page in ['visao_geral','atendentes']:
        v=read(definition/'pages'/page/'visuals/filtro_data/visual.json')
        check('intervalo de datas '+page,v['visual']['objects']['data'][0]['properties']['mode']['expr']['Literal']['Value'],"'Between'",'PBIR; interação Desktop pendente')
    check('fonte neutra','C:\\Users\\' in (model/'expressions.tmdl').read_text(),False,'TMDL')
    allowed_filters=[];unexpected=[];refs=[]
    def walk(x,path):
        if isinstance(x,dict):
            if 'Where' in x:
                if path.endswith('atendentes/page.json') and 'NAO_ATRIBUIDO' in json.dumps(x) and len(x['Where'])==1:allowed_filters.append(path)
                else:unexpected.append(path)
            for kind in ['Measure','Column']:
                v=x.get(kind)
                if isinstance(v,dict) and 'Expression' in v and 'Property' in v:
                    sr=v['Expression'].get('SourceRef',{});ent=sr.get('Entity')
                    if ent:refs.append((ent,kind,v['Property']))
            for v in x.values():walk(v,path)
        elif isinstance(x,list):
            for v in x:walk(v,path)
    for p in definition.rglob('*.json'):walk(read(p),p.relative_to(definition).as_posix())
    check('ausência de predicados de teste',unexpected,[],'Inspeção de filtros PBIR')
    check('filtro funcional preservado',allowed_filters,['pages/atendentes/page.json'],'Inspeção PBIR; exclusão NAO_ATRIBUIDO intencional')
    for name in ['visao_geral','atendentes']:
        pg=read(definition/'pages'/name/'page.json');check('dimensões '+name,[pg['width'],pg['height']],[1440,810],'Estrutura PBIR')
    for vpath in ['visao_geral/visuals/kpi_2','visao_geral/visuals/kpi_3','visao_geral/visuals/kpi_4','atendentes/visuals/tma']:
        v=read(definition/'pages'/vpath/'visual.json')['visual'];pr=v['objects']['labels'][0]['properties'];check('precisão '+vpath,pr['labelPrecision']['expr']['Literal']['Value'],'2L','Estrutura PBIR')
    for name in ['volume','tma_prof']:
        v=read(definition/'pages/atendentes/visuals'/name/'visual.json')['visual'];order=v['query']['sortDefinition']['sort'];check('ordenação '+name,[(x['field']['Column']['Property'],x['direction']) for x in order],[('atendente_nome','Ascending')],'Estrutura PBIR; renderização pendente')
    hora=read(definition/'pages/visao_geral/visuals/hora/visual.json')['visual'];check('eixo horário visível',hora['objects']['categoryAxis'][0]['properties']['show']['expr']['Literal']['Value'],'true','Estrutura PBIR')
    check('ordem horária',hora['query']['sortDefinition']['sort'][0]['direction'],'Ascending','Estrutura PBIR')
    fields={}
    for p in (model/'tables').glob('*.tmdl'):
        text=p.read_text();fields[p.stem]={kind:{(a or b) for a,b in re.findall(r'^\t'+kind.lower()+r" (?:'([^']+)'|([^\s=]+))",text,re.M)} for kind in ['Column','Measure']}
    invalid=[ref for ref in refs if ref[0] not in fields or ref[2] not in fields[ref[0]][ref[1]]]
    check('referências explícitas dos visuais',invalid,[],'Inspeção TMDL/PBIR; não parser oficial')
    rel=(model/'relationships.tmdl').read_text();check('quantidade relacionamentos',len(re.findall('^relationship ',rel,re.M)),3,'Inspeção TMDL')
    check('sem relação inativa/bidirecional explícita',bool(re.search(r'isActive:\s*false|crossFilteringBehavior:\s*bothDirections',rel)),False,'Inspeção TMDL; defaults mantidos')
    invalid_rel=[]
    for table,col in re.findall(r'(?:fromColumn|toColumn): (\w+)\.(\w+)',rel):
        if table not in fields or col not in fields[table]['Column']:invalid_rel.append(table+'.'+col)
    check('referências relacionamentos',invalid_rel,[],'Inspeção TMDL')
    for kind,owner,d in [('PBIP',R/'projeto',read(R/'projeto/CallCenterAnalytics.pbip')),('PBIR',reportroot,read(reportroot/'definition.pbir'))]:
        target=d['artifacts'][0]['report']['path'] if kind=='PBIP' else d['datasetReference']['byPath']['path']
        check('destino '+kind,(owner/target).is_dir(),True,'Sistema de arquivos')
    check('sem cache distribuído',len(list(R.rglob('.pbi'))),0,'Sistema de arquivos')
    measures=(model/'tables/Medidas.tmdl').read_text();check('medidas numéricas sem FORMAT',bool(re.search(r'\bFORMAT\s*\(',measures,re.I)),False,'Inspeção DAX; sem execução DAX')
    check('formato TMA com 2 casas',measures.count('formatString: 0.00" min"'),2,'Metadados TMDL')
    # Geometric bounds only; cannot verify actual rendering or text clipping.
    out=[]
    for p in definition.glob('pages/*/visuals/*/visual.json'):
        d=read(p);z=d['position']
        if not (z['x']>=0 and z['y']>=0 and z['x']+z['width']<=1440.01 and z['y']+z['height']<=810.01):out.append(p.relative_to(definition).as_posix())
    check('contêineres dentro das páginas',out,[],'Geometria PBIR; não renderização')
    result={'status':'PASSOU' if all(c['resultado']=='PASSOU' for c in checks) else 'FALHOU','limite':'SQL/Python e inspeção estática. NÃO comprova execução de M/DAX, seleção cruzada, renderização ou reabertura no Desktop.','controles':controls,'por_atendente':by_agent,'testes':checks}
    print(json.dumps(result,ensure_ascii=False,indent=2));return result['status']!='PASSOU'
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:print(json.dumps({'status':'FALHOU','erro':str(e)},ensure_ascii=False));sys.exit(1)
