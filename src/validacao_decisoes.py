"""Reconstrucao segundo a segundo; nao importa o simulador."""

from collections import defaultdict
from datetime import datetime, timedelta, time

from src.validacao_integridade import validar_integridade


def validar_decisoes(entradas, disponibilidades, resultados, config,
                     mostrar_progresso=False):
    validar_integridade(entradas, disponibilidades, resultados, config)

    por_dia = defaultdict(list)
    escalas_dia = defaultdict(list)
    for c in entradas:
        por_dia[c["entrada_em"].date()].append(c)
    for d in disponibilidades:
        escalas_dia[d["inicio_disponibilidade_em"].date()].append(d)

    abertura = time.fromisoformat(config["horarios"]["abertura"])
    fechamento = time.fromisoformat(config["horarios"]["fechamento"])
    fim_trabalho = time.fromisoformat(
        config["horarios"]["fim_maximo_ocupacao"]
    )
    esperados = {}

    for numero_dia, dia in enumerate(sorted(por_dia), start=1):
        t = datetime.combine(dia, abertura)
        fechar_em = datetime.combine(dia, fechamento)
        encerrar_em = datetime.combine(dia, fim_trabalho)

        chegadas = defaultdict(list)
        prazos = {}
        for c in por_dia[dia]:
            chegadas[c["entrada_em"]].append(c)
            prazos[c["chamada_id"]] = c["entrada_em"] + timedelta(
                seconds=c["tolerancia_espera_segundos"]
            )

        pendentes = []
        ocupacoes = {}
        liberacoes = {}
        escalas = escalas_dia[dia]

        while t <= encerrar_em:
            # Esta verificacao acontece em cada segundo, inclusive apos 18h.
            for profissional in list(ocupacoes):
                if ocupacoes[profissional] <= t:
                    del ocupacoes[profissional]

            pendentes.extend(chegadas.get(t, []))
            pendentes.sort(key=lambda c: (c["entrada_em"], c["chamada_id"]))

            if t >= fechar_em:
                for c in pendentes:
                    if prazos[c["chamada_id"]] < t:
                        raise ValueError("Controle: tolerancia perdida.")
                    esperados[c["chamada_id"]] = {
                        **c, "status": "ABANDONADA",
                        "atendente_id": None, "disponibilidade_id": None,
                        "inicio_atendimento_em": None, "saida_em": t,
                        "pos_atendimento_segundos": None,
                        "motivo_abandono": "FECHAMENTO",
                    }
                pendentes = []
            else:
                # Uma passagem cronologica: chamadas posteriores da mesma
                # fila ficam bloqueadas apenas se uma anterior permanecer.
                bloqueadas = set()
                continuam = []

                for c in pendentes:
                    identificador = c["chamada_id"]
                    fila = c["fila_id"]
                    prazo = prazos[identificador]
                    if prazo < t:
                        raise ValueError("Controle: tolerancia perdida.")

                    contato = c["duracao_contato_planejada_segundos"]
                    pos = c["pos_atendimento_planejado_segundos"]
                    fim = t + timedelta(seconds=contato + pos)
                    candidatos = []

                    if fila not in bloqueadas:
                        for d in escalas:
                            profissional = d["atendente_id"]
                            inicio_intervalo = d["inicio_disponibilidade_em"]
                            if (
                                d["fila_id"] == fila
                                and inicio_intervalo <= t
                                and t < d["fim_disponibilidade_em"]
                                and fim <= d["fim_disponibilidade_em"]
                                and fim <= encerrar_em
                                and profissional not in ocupacoes
                            ):
                                livre_desde = max(
                                    inicio_intervalo,
                                    liberacoes.get(profissional, inicio_intervalo)
                                )
                                candidatos.append((
                                    livre_desde, profissional,
                                    d["disponibilidade_id"]
                                ))

                    if candidatos:
                        _, profissional, intervalo = min(candidatos)
                        ocupacoes[profissional] = fim
                        liberacoes[profissional] = fim
                        esperados[identificador] = {
                            **c, "status": "ATENDIDA",
                            "atendente_id": profissional,
                            "disponibilidade_id": intervalo,
                            "inicio_atendimento_em": t,
                            "saida_em": t + timedelta(seconds=contato),
                            "pos_atendimento_segundos": pos,
                            "motivo_abandono": None,
                        }
                    elif prazo == t:
                        esperados[identificador] = {
                            **c, "status": "ABANDONADA",
                            "atendente_id": None, "disponibilidade_id": None,
                            "inicio_atendimento_em": None, "saida_em": t,
                            "pos_atendimento_segundos": None,
                            "motivo_abandono": "DESISTENCIA",
                        }
                    else:
                        continuam.append(c)
                        bloqueadas.add(fila)

                pendentes = continuam

            t += timedelta(seconds=1)

        if pendentes or ocupacoes:
            raise ValueError("Controle: trabalho ou fila apos o limite diario.")

        if mostrar_progresso and (
            numero_dia % 10 == 0 or numero_dia == len(por_dia)
        ):
            print(
                f"Reconstrucao: {numero_dia}/{len(por_dia)} dias",
                flush=True
            )

    if set(esperados) != {r["chamada_id"] for r in resultados}:
        raise ValueError("Controle: conjunto de chamadas divergente.")

    for obtido in resultados:
        esperado = esperados[obtido["chamada_id"]]
        for campo in esperado:
            if obtido[campo] != esperado[campo]:
                raise ValueError(
                    f"Decisao divergente: {obtido['chamada_id']} / {campo}; "
                    f"esperado={esperado[campo]!r}; obtido={obtido[campo]!r}"
                )

        if esperado["status"] == "ATENDIDA":
            fim_esperado = esperado["saida_em"] + timedelta(
                seconds=esperado["pos_atendimento_segundos"]
            )
            fim_obtido = obtido["saida_em"] + timedelta(
                seconds=obtido["pos_atendimento_segundos"]
            )
            if fim_esperado != fim_obtido:
                raise ValueError("Controle: fim de ocupacao divergente.")

    return {
        "dias_reconstruidos": len(por_dia),
        "chamadas_com_decisoes_conferidas": len(esperados),
        "divergencias": 0,
    }
