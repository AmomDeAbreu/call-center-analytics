"""Simulação FIFO por eventos, sem sorteios e sem escrita de arquivos."""

import heapq
from collections import defaultdict
from datetime import datetime, time, timedelta


def simular(entradas, disponibilidades, config):
    filas_ids = sorted(f["fila_id"] for f in config["filas"])
    profissionais = {
        f'{config["atendentes"]["prefixo_id"]}{i:02d}'
        for i in range(1, config["atendentes"]["quantidade"] + 1)
    }
    abertura = time.fromisoformat(config["horarios"]["abertura"])
    fechamento = time.fromisoformat(config["horarios"]["fechamento"])
    limite_trabalho = time.fromisoformat(
        config["horarios"]["fim_maximo_ocupacao"]
    )
    disponibilidades_dia = defaultdict(list)
    entradas_dia = defaultdict(list)

    # Validar disponibilidades antes de qualquer decisão.
    ids = set()
    ultimo_fim = {}
    for d in sorted(disponibilidades, key=lambda x: (
        x["atendente_id"], x["inicio_disponibilidade_em"]
    )):
        identificador = d["disponibilidade_id"]
        profissional = d["atendente_id"]
        inicio = d["inicio_disponibilidade_em"]
        fim = d["fim_disponibilidade_em"]
        if not identificador or identificador in ids:
            raise ValueError("ID de disponibilidade vazio ou duplicado.")
        ids.add(identificador)
        if profissional not in profissionais or d["fila_id"] not in filas_ids:
            raise ValueError("Referencia invalida na disponibilidade.")
        if not (
            inicio.date() == fim.date()
            and abertura <= inicio.time() < fechamento
            and inicio < fim
            and fim.time() <= limite_trabalho
        ):
            raise ValueError("Intervalo de disponibilidade invalido.")
        if profissional in ultimo_fim and inicio < ultimo_fim[profissional]:
            raise ValueError("Sobreposicao de disponibilidade.")
        ultimo_fim[profissional] = fim
        disponibilidades_dia[inicio.date()].append(d)

    ids = set()
    for c in entradas:
        identificador = c["chamada_id"]
        entrada = c["entrada_em"]
        if not identificador or identificador in ids:
            raise ValueError("ID de chamada vazio ou duplicado.")
        ids.add(identificador)
        if c["fila_id"] not in filas_ids:
            raise ValueError("Fila desconhecida.")
        if not abertura <= entrada.time() < fechamento:
            raise ValueError("Entrada fora do horario.")
        for campo, minimo in (
            ("tolerancia_espera_segundos", 1),
            ("duracao_contato_planejada_segundos", 1),
            ("pos_atendimento_planejado_segundos", 0),
        ):
            if type(c[campo]) is not int or c[campo] < minimo:
                raise ValueError(f"Valor invalido: {campo}")
        entradas_dia[entrada.date()].append(c)

    resultados = []

    for dia in sorted(entradas_dia):
        fechar_em = datetime.combine(dia, fechamento)
        limite_em = datetime.combine(dia, limite_trabalho)
        disponibilidades_deste_dia = disponibilidades_dia[dia]
        chegadas = defaultdict(list)
        filas = {fila: [] for fila in filas_ids}
        ocupado_ate = {}
        eventos = set([fechar_em])

        for d in disponibilidades_deste_dia:
            eventos.add(d["inicio_disponibilidade_em"])
            eventos.add(d["fim_disponibilidade_em"])

        for c in entradas_dia[dia]:
            chegadas[c["entrada_em"]].append(c)
            eventos.add(c["entrada_em"])
            prazo = c["entrada_em"] + timedelta(
                seconds=c["tolerancia_espera_segundos"]
            )
            eventos.add(min(prazo, fechar_em))

        agenda = list(eventos)
        heapq.heapify(agenda)
        agendados = set(eventos)

        def agendar(instante):
            if instante not in agendados:
                heapq.heappush(agenda, instante)
                agendados.add(instante)

        def prazo_de(c):
            return c["entrada_em"] + timedelta(
                seconds=c["tolerancia_espera_segundos"]
            )

        def abandonar(c, instante, motivo):
            resultados.append({
                **c,
                "status": "ABANDONADA",
                "atendente_id": None,
                "disponibilidade_id": None,
                "inicio_atendimento_em": None,
                "saida_em": instante,
                "pos_atendimento_segundos": None,
                "motivo_abandono": motivo,
            })

        while agenda:
            t = heapq.heappop(agenda)

            # Liberação só ocorre no fim da ocupação, após o pós-atendimento.
            # Não apagamos o instante: ele também informa há quanto tempo
            # o profissional está livre dentro do intervalo atual.
            for c in chegadas.get(t, []):
                filas[c["fila_id"]].append(c)

            if t >= fechar_em:
                if t == fechar_em:
                    for fila in filas.values():
                        for c in fila:
                            if prazo_de(c) < t:
                                raise ValueError("Prazo perdido antes do fechamento.")
                            abandonar(c, t, "FECHAMENTO")
                        fila.clear()
                # Percorrer eventos até todas as ocupações terminarem.
                continue

            for fila_id in filas_ids:
                fila = filas[fila_id]
                fila.sort(key=lambda c: (c["entrada_em"], c["chamada_id"]))

                if any(prazo_de(c) < t for c in fila):
                    raise ValueError("Chamada permaneceu apos sua tolerancia.")

                while fila:
                    c = fila[0]
                    duracao = c["duracao_contato_planejada_segundos"]
                    pos = c["pos_atendimento_planejado_segundos"]
                    fim_ocupacao = t + timedelta(seconds=duracao + pos)
                    elegiveis = []

                    for d in disponibilidades_deste_dia:
                        if d["fila_id"] != fila_id:
                            continue
                        inicio = d["inicio_disponibilidade_em"]
                        fim = d["fim_disponibilidade_em"]
                        profissional = d["atendente_id"]
                        livre_desde = max(
                            inicio, ocupado_ate.get(profissional, inicio)
                        )
                        if (
                            inicio <= t < fim
                            and livre_desde <= t
                            and fim_ocupacao <= fim
                            and fim_ocupacao <= limite_em
                        ):
                            elegiveis.append((
                                livre_desde, profissional,
                                d["disponibilidade_id"]
                            ))

                    if elegiveis:
                        _, profissional, disponibilidade_id = min(elegiveis)
                        resultados.append({
                            **c,
                            "status": "ATENDIDA",
                            "atendente_id": profissional,
                            "disponibilidade_id": disponibilidade_id,
                            "inicio_atendimento_em": t,
                            "saida_em": t + timedelta(seconds=duracao),
                            "pos_atendimento_segundos": pos,
                            "motivo_abandono": None,
                        })
                        ocupado_ate[profissional] = fim_ocupacao
                        agendar(fim_ocupacao)
                        fila.pop(0)
                        continue

                    if prazo_de(c) == t:
                        abandonar(c, t, "DESISTENCIA")
                        fila.pop(0)
                        continue

                    # A primeira bloqueia a fila, mas posteriores podem desistir.
                    restantes = []
                    for posterior in fila:
                        if prazo_de(posterior) == t:
                            abandonar(posterior, t, "DESISTENCIA")
                        else:
                            restantes.append(posterior)
                    fila[:] = restantes
                    break

        if any(filas.values()):
            raise ValueError("Fila nao encerrada.")
        if any(fim > limite_em for fim in ocupado_ate.values()):
            raise ValueError("Ocupacao ultrapassa o limite diario.")

    if len(resultados) != len(entradas):
        raise ValueError("Quantidade de resultados diverge das entradas.")

    return sorted(resultados, key=lambda c: c["chamada_id"])
