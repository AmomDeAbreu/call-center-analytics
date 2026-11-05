"""Confere todos os arquivos; usar antes de abrir/salvar no Desktop."""
import hashlib,json,sys
from pathlib import Path
r=Path(__file__).resolve().parents[1]
m=r/'conferencias/manifesto_sha256.json'
try:
    expected=json.loads(m.read_text())
    actual={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file() and p!=m}
    errors=[k for k in sorted(set(expected)|set(actual)) if expected.get(k)!=actual.get(k)]
    print(json.dumps({'status':'FAIL' if errors else 'PASS','arquivos':len(actual),'divergencias':errors},ensure_ascii=False,indent=2))
    sys.exit(bool(errors))
except (OSError,ValueError) as e:
    print('FAIL:',e);sys.exit(1)
