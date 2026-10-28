"""Gera entradas e tempos planejados, sem decidir atendimentos."""

from datetime import date, datetime, time, timedelta


def gerar_entradas(config, rng):
    """Recebe o mesmo RNG usado anteriormente nas disponibilidades."""
    inicio = date.fromisoformat(config["periodo"]["inicio"])
    fim = date.fromisoformat(config["periodo"]["fim"])
    if fim < inicio:
        raise ValueError("Periodo invertido.")

    dias = [
        inicio + timedelta(days=i)
        for i in range((fim - inicio).days + 1)
    ]
    volume = config["volume"]
    reservadas = volume["chamadas_reservadas_por_dia"]
    restantes = volume["total_chamadas"] - len(dias) * reservadas
    if reservadas < 0 or restantes < 0:
        raise ValueError("Reserva diaria incompativel com o volume.")

    pesos_datas = [
        volume["pesos_dias_semana_segunda_a_domingo"][dia.weekday()]
        for dia in dias
    ]
    filas = sorted(config["filas"], key=lambda f: f["fila_id"])
    pesos_filas = [f["peso"] for f in filas]
    horarios = config["horarios"]
    espera = config["espera"]
    pos = config["pos_atendimento"]
    registros = []

    def criar(dia):
        hora = rng.choices(
            horarios["horas_entrada"],
            weights=horarios["pesos_horas"], k=1
        )[0]
        segundo = rng.randint(0, 3599)
        entrada = datetime.combine(dia, time(hora)) + timedelta(
            seconds=segundo
        )
        fila = rng.choices(filas, weights=pesos_filas, k=1)[0]
        contato = rng.randint(
            fila["contato_segundos_min"], fila["contato_segundos_max"]
        )
        tolerancia = rng.randint(
            espera["tolerancia_segundos_min"],
            espera["tolerancia_segundos_max"]
        )
        positivo = rng.choices(
            [False, True],
            weights=[pos["peso_zero"], pos["peso_positivo"]],
            k=1
        )[0]
        pos_planejado = (
            rng.randint(
                pos["segundos_positivos_min"],
                pos["segundos_positivos_max"]
            )
            if positivo else 0
        )
        registros.append({
            "_sequencia": len(registros),
            "fila_id": fila["fila_id"],
            "entrada_em": entrada,
            "tolerancia_espera_segundos": tolerancia,
            "duracao_contato_planejada_segundos": contato,
            "pos_atendimento_planejado_segundos": pos_planejado,
        })

    # A data reservada nao consome um sorteio de data.
    for dia in dias:
        for _ in range(reservadas):
            criar(dia)

    # Sortear data e demais atributos de uma chamada antes da seguinte.
    for _ in range(restantes):
        criar(rng.choices(dias, weights=pesos_datas, k=1)[0])

    registros.sort(key=lambda r: (r["entrada_em"], r["_sequencia"]))

    resultado = []
    for indice, registro in enumerate(registros, start=1):
        resultado.append({
            "chamada_id": f"CH{indice:06d}",
            **{
                chave: valor
                for chave, valor in registro.items()
                if chave != "_sequencia"
            },
        })
    return resultado
