"""Executar na raiz: python3 -m src.exportar."""

import csv
import hashlib
import io
import json
import platform
import random
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

from src.disponibilidade import gerar_disponibilidades
from src.entradas import gerar_entradas
from src.simulador import simular
from src.validacao_integridade import validar_integridade
from src.validacao_decisoes import validar_decisoes


RAIZ = Path(__file__).resolve().parents[1]

COLUNAS = {
    "chamadas.csv": [
        "chamada_id", "fila_id", "entrada_em", "status", "atendente_id",
        "disponibilidade_id", "inicio_atendimento_em", "saida_em",
        "pos_atendimento_segundos", "tolerancia_espera_segundos",
        "duracao_contato_planejada_segundos",
        "pos_atendimento_planejado_segundos", "motivo_abandono",
    ],
    "atendentes.csv": ["atendente_id", "atendente_nome"],
    "filas.csv": ["fila_id", "fila_nome"],
    "disponibilidade_atendentes.csv": [
        "disponibilidade_id", "atendente_id", "fila_id",
        "inicio_disponibilidade_em", "fim_disponibilidade_em",
    ],
}


def sha(conteudo):
    return hashlib.sha256(conteudo).hexdigest()


def gerar(config):
    rng = random.Random(config["semente"])
    disponibilidades = gerar_disponibilidades(config, rng)
    entradas = gerar_entradas(config, rng)
    resultados = simular(entradas, disponibilidades, config)
    return entradas, disponibilidades, resultados


def serializar(nome, registros, config):
    formato = config["exportacao"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer, fieldnames=COLUNAS[nome],
        delimiter=formato["separador"],
        lineterminator=formato["quebra_linha"],
        extrasaction="raise",
    )
    writer.writeheader()
    for registro in registros:
        linha = {}
        for campo in COLUNAS[nome]:
            valor = registro[campo]
            if isinstance(valor, datetime):
                valor = valor.strftime(formato["formato_data_hora"])
            elif valor is None:
                valor = formato["valor_nulo"]
            linha[campo] = valor
        writer.writerow(linha)
    return buffer.getvalue().encode(formato["encoding"])


def pacote(config, disponibilidades, resultados):
    tabelas = {
        "chamadas.csv": sorted(resultados, key=lambda r: r["chamada_id"]),
        "disponibilidade_atendentes.csv": sorted(
            disponibilidades, key=lambda r: r["disponibilidade_id"]
        ),
        "atendentes.csv": [
            {
                "atendente_id": f'{config["atendentes"]["prefixo_id"]}{i:02d}',
                "atendente_nome": f'{config["atendentes"]["prefixo_nome"]} {i:02d}',
            }
            for i in range(1, config["atendentes"]["quantidade"] + 1)
        ],
        "filas.csv": [
            {"fila_id": f["fila_id"], "fila_nome": f["fila_nome"]}
            for f in sorted(config["filas"], key=lambda r: r["fila_id"])
        ],
    }
    return {
        nome: serializar(nome, registros, config)
        for nome, registros in tabelas.items()
    }, tabelas


def conferir_cobertura(resultados, disponibilidades):
    atendidas = [r for r in resultados if r["status"] == "ATENDIDA"]
    abandonadas = [r for r in resultados if r["status"] == "ABANDONADA"]
    filas = Counter((r["fila_id"], r["status"]) for r in resultados)
    motivos = Counter(r["motivo_abandono"] for r in abandonadas)
    esperas = [
        (r["inicio_atendimento_em"] - r["entrada_em"]).total_seconds()
        for r in atendidas
    ]
    perfis = {}
    for d in disponibilidades:
        chave = (d["atendente_id"], d["inicio_disponibilidade_em"].date())
        perfis.setdefault(chave, []).append((
            d["inicio_disponibilidade_em"].time(),
            d["fim_disponibilidade_em"].time(),
        ))
    padroes = {tuple(sorted(v)) for v in perfis.values()}
    criterios = {
        "3000_chamadas": len(resultados) == 3000,
        "90_dias": {r["entrada_em"].date() for r in resultados} == {
            date(2026, 1, 1) + timedelta(days=i) for i in range(90)
        },
        "conciliacao": len(atendidas) + len(abandonadas) == len(resultados),
        "filas_com_ambos_status": all(
            filas[(f, s)] > 0
            for f in ("F01", "F02", "F03")
            for s in ("ATENDIDA", "ABANDONADA")
        ),
        "oito_atendentes_com_atendimento": {
            r["atendente_id"] for r in atendidas
        } == {f"AT{i:02d}" for i in range(1, 9)},
        "esperas_ate_20s": any(e <= 20 for e in esperas),
        "esperas_acima_20s": any(e > 20 for e in esperas),
        "desistencia": motivos["DESISTENCIA"] > 0,
        "fechamento": motivos["FECHAMENTO"] > 0,
        "pos_positivo": any(r["pos_atendimento_segundos"] > 0 for r in atendidas),
        "disponibilidade_variavel": len(padroes) > 1,
    }
    falhas = [nome for nome, ok in criterios.items() if not ok]
    if falhas:
        raise ValueError(f"Cobertura reprovada: {falhas}")
    return criterios


def main():
    inicio = perf_counter()
    if Path.cwd().resolve() != RAIZ:
        raise SystemExit("Execute na raiz do repositorio.")

    arquivo_config = RAIZ / "config.json"
    config_bytes = arquivo_config.read_bytes()
    config = json.loads(config_bytes)
    if platform.python_version() != config["python_referencia"]:
        raise SystemExit("Versao do Python difere da referencia; revisar antes de gerar.")

    relatorio = RAIZ / "reports/validacao_base_v1.json"
    log_testes = RAIZ / "reports/testes_base_v1.txt"
    destinos = [RAIZ / "data" / nome for nome in COLUNAS]
    for caminho in destinos + [relatorio, log_testes]:
        if caminho.exists() or caminho.is_symlink():
            raise SystemExit(f"Destino existente; nada sobrescrito: {caminho}")
        if not caminho.parent.is_dir():
            raise SystemExit(f"Pasta ausente: {caminho.parent}")

    print("Executando testes...", flush=True)
    testes = subprocess.run(
        [sys.executable, "-m", "unittest", "discover",
         "-s", "tests", "-p", "test_*.py", "-v"],
        cwd=RAIZ, capture_output=True, text=True,
    )
    texto_testes = testes.stdout + testes.stderr
    print(texto_testes, flush=True)
    if testes.returncode != 0:
        raise SystemExit("Testes falharam; exportacao cancelada.")

    print("Gerando e reconstruindo decisoes...", flush=True)
    entradas, disponibilidades, resultados = gerar(config)
    integridade = validar_integridade(
        entradas, disponibilidades, resultados, config
    )
    decisoes = validar_decisoes(
        entradas, disponibilidades, resultados, config,
        mostrar_progresso=True
    )
    cobertura = conferir_cobertura(resultados, disponibilidades)
    bytes_a, tabelas = pacote(config, disponibilidades, resultados)

    print("Segunda geracao para verificar reproducibilidade...", flush=True)
    entradas_b, disponibilidades_b, resultados_b = gerar(config)
    validar_integridade(entradas_b, disponibilidades_b, resultados_b, config)
    bytes_b, _ = pacote(config, disponibilidades_b, resultados_b)
    if bytes_a != bytes_b:
        raise ValueError("Arquivos divergentes entre geracoes.")

    # Conferir cabecalhos e valores apos interpretar o CSV.
    for nome, conteudo in bytes_a.items():
        reader = csv.DictReader(
            io.StringIO(conteudo.decode("utf-8")),
            delimiter=config["exportacao"]["separador"],
        )
        if reader.fieldnames != COLUNAS[nome]:
            raise ValueError(f"Cabecalho divergente: {nome}")
        linhas = list(reader)
        esperadas = []
        for r in tabelas[nome]:
            esperadas.append({
                campo: (
                    r[campo].strftime(config["exportacao"]["formato_data_hora"])
                    if isinstance(r[campo], datetime)
                    else "" if r[campo] is None else str(r[campo])
                )
                for campo in COLUNAS[nome]
            })
        if linhas != esperadas:
            raise ValueError(f"Conteudo divergente apos leitura: {nome}")

    atendidas = [r for r in resultados if r["status"] == "ATENDIDA"]
    tempo_total = sum(
        (r["saida_em"] - r["inicio_atendimento_em"]).total_seconds()
        + r["pos_atendimento_segundos"] for r in atendidas
    )
    sla_n = sum(
        (r["inicio_atendimento_em"] - r["entrada_em"]).total_seconds()
        <= config["indicadores"]["sla_limite_segundos"]
        for r in atendidas
    )
    fontes = sorted((RAIZ / "src").glob("*.py"))
    fontes += sorted((RAIZ / "tests").glob("test_*.py"))
    evidencias = {
        "status": "VALIDACOES_PYTHON_CONCLUIDAS_POWER_BI_PENDENTE",
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "config_sha256": sha(config_bytes),
        "fontes_sha256": {
            str(p.relative_to(RAIZ)): sha(p.read_bytes()) for p in fontes
        },
        "integridade": integridade,
        "decisoes": decisoes,
        "cobertura": cobertura,
        "duas_geracoes_identicas": True,
        "leitura_csv_conferida": True,
        "testes_exit_code": testes.returncode,
        "indicadores_controle": {
            "recebidas": len(resultados),
            "atendidas": len(atendidas),
            "abandonadas": len(resultados) - len(atendidas),
            "atendidas_ate_20s": sla_n,
            "tempo_total_atendimento_segundos": tempo_total,
            "tma_segundos": tempo_total / len(atendidas),
            "taxa_abandono": (len(resultados) - len(atendidas)) / len(resultados),
            "sla_demonstrativo": sla_n / len(resultados),
        },
        "arquivos": {
            nome: {"linhas": len(tabelas[nome]), "sha256": sha(conteudo)}
            for nome, conteudo in bytes_a.items()
        },
    }

    for nome, conteudo in bytes_a.items():
        caminho = RAIZ / "data" / nome
        with caminho.open("xb") as arquivo:
            arquivo.write(conteudo)
        if caminho.read_bytes() != conteudo:
            raise ValueError(f"Falha na verificacao do arquivo gravado: {nome}")

    evidencias["tempo_execucao_segundos"] = round(perf_counter() - inicio, 3)
    with log_testes.open("x", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write(texto_testes)
    with relatorio.open("x", encoding="utf-8", newline="\n") as arquivo:
        json.dump(evidencias, arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")

    print("\nEXPORTACAO CONCLUIDA")
    for nome, dados in evidencias["arquivos"].items():
        print(f"{nome}: {dados['linhas']} registros; SHA256 {dados['sha256']}")
    print(json.dumps(evidencias["indicadores_controle"], indent=2))
    print("Evidencias: reports/validacao_base_v1.json e reports/testes_base_v1.txt")
    print("Power BI e revisao final de entrega continuam pendentes.")


if __name__ == "__main__":
    main()
