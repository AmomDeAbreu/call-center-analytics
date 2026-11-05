"""Verifica publicação em pasta temporária. Sem rede e sem escrita na candidata."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'CallCenterAnalytics_v1_8_RC1.zip': '741f6cbf143c5682d1fd5555d50185d51555aaccc6221c8899b05a39e332db5e',
    'Entrega_CallCenterAnalytics_v1_8_RC1.zip': '1c93baad8db281dc295d63eac010e61f56e39831719c8576184a90ce075a6f7f',
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def inventory(root):
    return {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def main():
    records = []
    for name, expected in EXPECTED.items():
        observed = digest((ROOT / 'artifacts' / name).read_bytes())
        require(observed == expected, 'Hash divergente: ' + name)
        records.append({'teste': name, 'camada': 'SHA-256', 'esperado': expected, 'observado': observed, 'resultado': 'PASS'})
    with zipfile.ZipFile(ROOT / 'artifacts/Entrega_CallCenterAnalytics_v1_8_RC1.zip') as delivery:
        require(digest(delivery.read('CallCenterAnalytics_v1_8_RC1.zip')) == EXPECTED['CallCenterAnalytics_v1_8_RC1.zip'], 'Candidata interna divergente')
    with tempfile.TemporaryDirectory(prefix='cca-check-') as tmp:
        with zipfile.ZipFile(ROOT / 'artifacts/CallCenterAnalytics_v1_8_RC1.zip') as z:
            names = z.namelist()
            require(len(names) == len(set(names)), 'Entradas duplicadas no ZIP')
            require(z.testzip() is None, 'CRC inválido')
            for item in z.infolist():
                path = PurePosixPath(item.filename)
                require(not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename, 'Caminho inválido no ZIP')
                require((item.external_attr >> 16) & 0o170000 != 0o120000, 'Link simbólico no ZIP')
                require(path.parts[0] == 'CallCenterAnalytics_v1_8_RC1', 'Raiz inesperada')
                z.extract(item, tmp)
        candidate = Path(tmp) / 'CallCenterAnalytics_v1_8_RC1'
        before = inventory(candidate)
        require(before == inventory(ROOT / 'demonstracao/CallCenterAnalytics_v1_8_RC1'), 'Extração para navegação difere do ZIP')
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        for script, args in [('conferir_manifesto.py', []), ('validar.py', ['.']), ('testar.py', []), ('regressao_qa.py', []), ('conferir_manifesto.py', [])]:
            command = [sys.executable, '-B', 'validacao/' + script, *args]
            run = subprocess.run(command, cwd=candidate, env=env, capture_output=True, text=True, timeout=120)
            require(run.returncode == 0, 'Falhou: ' + script + '\n' + run.stdout + run.stderr)
            result = json.loads(run.stdout)
            records.append({'teste': script, 'camada': 'Python/SQL/estrutura; não M/DAX', 'esperado': 'saída 0', 'observado': run.returncode, 'resultado': result})
        require(inventory(candidate) == before, 'Testes alteraram a extração')
    print(json.dumps({'status': 'PASS', 'python': sys.version.split()[0], 'arquivos_candidata': len(before), 'extracao_identica': True,
                      'sem_modificacoes_pelos_testes': True, 'testes': records, 'limite': 'Não executa M/DAX/Desktop.'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print('FAIL:', error, file=sys.stderr)
        sys.exit(1)
