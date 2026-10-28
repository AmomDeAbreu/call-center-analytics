"""Geração dos intervalos; não simula chamadas nem escreve CSVs."""

from datetime import date, datetime, timedelta


def gerar_disponibilidades(config, rng):
    """Usa a instância aleatória recebida, sem reiniciar a semente."""
    inicio = date.fromisoformat(config["periodo"]["inicio"])
    fim = date.fromisoformat(config["periodo"]["fim"])
    if fim < inicio:
        raise ValueError("Período invertido.")

    perfis = config["disponibilidade"]["perfis"]
    pesos_perfis = [perfil["peso"] for perfil in perfis]
    filas = sorted(fila["fila_id"] for fila in config["filas"])
    pesos_filas = [
        config["disponibilidade"]["pesos_filas_por_intervalo"][fila]
        for fila in filas
    ]
    prefixo = config["atendentes"]["prefixo_id"]
    quantidade = config["atendentes"]["quantidade"]
    registros = []

    for numero in range(1, quantidade + 1):
        atendente_id = f"{prefixo}{numero:02d}"
        for deslocamento in range((fim - inicio).days + 1):
            dia = inicio + timedelta(days=deslocamento)
            perfil = rng.choices(perfis, weights=pesos_perfis, k=1)[0]
            for hora_inicio, hora_fim in perfil["intervalos"]:
                fila_id = rng.choices(filas, weights=pesos_filas, k=1)[0]
                registros.append({
                    "atendente_id": atendente_id,
                    "fila_id": fila_id,
                    "inicio_disponibilidade_em": datetime.fromisoformat(
                        f"{dia.isoformat()} {hora_inicio}"
                    ),
                    "fim_disponibilidade_em": datetime.fromisoformat(
                        f"{dia.isoformat()} {hora_fim}"
                    ),
                })

    registros.sort(key=lambda r: (
        r["atendente_id"], r["inicio_disponibilidade_em"]
    ))

    return [
        {"disponibilidade_id": f"DISP{indice:06d}", **registro}
        for indice, registro in enumerate(registros, start=1)
    ]
