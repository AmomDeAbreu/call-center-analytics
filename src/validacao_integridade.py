"""Validação estrutural e temporal independente do simulador."""

from datetime import date, datetime, time, timedelta


def exigir(condicao, mensagem):
    if not condicao:
        raise ValueError(mensagem)


def validar_integridade(entradas, disponibilidades, resultados, config):
    inicio_periodo = date.fromisoformat(config["periodo"]["inicio"])
    fim_periodo = date.fromisoformat(config["periodo"]["fim"])
    abertura = time.fromisoformat(config["horarios"]["abertura"])
    fechamento = time.fromisoformat(config["horarios"]["fechamento"])
    fim_trabalho = time.fromisoformat(
        config["horarios"]["fim_maximo_ocupacao"]
    )
    filas = {f["fila_id"]: f for f in config["filas"]}
    atendentes = {
        f'{config["atendentes"]["prefixo_id"]}{i:02d}'
        for i in range(1, config["atendentes"]["quantidade"] + 1)
    }

    def indexar(registros, chave):
        indice = {}
        for r in registros:
            identificador = r.get(chave)
            exigir(
                isinstance(identificador, str) and bool(identificador),
                f"{chave}: identificador invalido"
            )
            exigir(identificador not in indice, f"{chave}: duplicidade")
            indice[identificador] = r
        return indice

    def conferir_data(valor, campo):
        exigir(type(valor) is datetime, f"{campo}: tipo invalido")
        exigir(
            valor.tzinfo is None and valor.microsecond == 0,
            f"{campo}: usar horario local com precisao de segundos"
        )
        exigir(
            inicio_periodo <= valor.date() <= fim_periodo,
            f"{campo}: fora do periodo"
        )

    def inteiro(valor, minimo, maximo, campo):
        exigir(type(valor) is int, f"{campo}: inteiro obrigatorio")
        exigir(minimo <= valor <= maximo, f"{campo}: fora dos limites")

    def sem_sobreposicao(intervalos, nome):
        for profissional, lista in intervalos.items():
            fim_anterior = None
            for inicio, fim in sorted(lista):
                exigir(
                    fim_anterior is None or inicio >= fim_anterior,
                    f"{nome}: sobreposicao de {profissional}"
                )
                fim_anterior = fim

    origens = indexar(entradas, "chamada_id")
    escalas = indexar(disponibilidades, "disponibilidade_id")
    saidas = indexar(resultados, "chamada_id")
    exigir(set(origens) == set(saidas), "IDs das entradas e resultados divergem")

    intervalos = {}
    for identificador, d in escalas.items():
        profissional = d.get("atendente_id")
        exigir(profissional in atendentes, f"{identificador}: atendente invalido")
        exigir(d.get("fila_id") in filas, f"{identificador}: fila invalida")
        inicio = d.get("inicio_disponibilidade_em")
        fim = d.get("fim_disponibilidade_em")
        conferir_data(inicio, "inicio_disponibilidade")
        conferir_data(fim, "fim_disponibilidade")
        exigir(
            inicio.date() == fim.date()
            and abertura <= inicio.time() < fechamento
            and inicio < fim and fim.time() <= fim_trabalho,
            f"{identificador}: intervalo invalido"
        )
        intervalos.setdefault(profissional, []).append((inicio, fim))
    sem_sobreposicao(intervalos, "Disponibilidade")

    campos_origem = {
        "chamada_id", "fila_id", "entrada_em",
        "tolerancia_espera_segundos",
        "duracao_contato_planejada_segundos",
        "pos_atendimento_planejado_segundos",
    }
    campos_resultado = campos_origem | {
        "status", "atendente_id", "disponibilidade_id",
        "inicio_atendimento_em", "saida_em",
        "pos_atendimento_segundos", "motivo_abandono",
    }
    ocupacoes = {}

    for identificador, origem in origens.items():
        r = saidas[identificador]
        exigir(set(origem) == campos_origem, f"{identificador}: campos de origem")
        exigir(set(r) == campos_resultado, f"{identificador}: campos de resultado")
        exigir(
            all(r[c] == origem[c] for c in campos_origem),
            f"{identificador}: origem alterada"
        )
        exigir(r["fila_id"] in filas, f"{identificador}: fila invalida")
        fila = filas[r["fila_id"]]
        entrada = r["entrada_em"]
        saida = r["saida_em"]
        conferir_data(entrada, "entrada")
        conferir_data(saida, "saida")
        exigir(
            abertura <= entrada.time() < fechamento,
            f"{identificador}: entrada fora do horario"
        )
        exigir(saida.date() == entrada.date(), f"{identificador}: saida em outro dia")
        tolerancia = r["tolerancia_espera_segundos"]
        contato = r["duracao_contato_planejada_segundos"]
        pos = r["pos_atendimento_planejado_segundos"]
        inteiro(
            tolerancia, config["espera"]["tolerancia_segundos_min"],
            config["espera"]["tolerancia_segundos_max"], "tolerancia"
        )
        inteiro(
            contato, fila["contato_segundos_min"],
            fila["contato_segundos_max"], "contato planejado"
        )
        inteiro(
            pos, 0, config["pos_atendimento"]["segundos_positivos_max"],
            "pos planejado"
        )
        prazo = entrada + timedelta(seconds=tolerancia)
        fechar_em = datetime.combine(entrada.date(), fechamento)

        if r["status"] == "ABANDONADA":
            for campo in (
                "atendente_id", "disponibilidade_id",
                "inicio_atendimento_em", "pos_atendimento_segundos"
            ):
                exigir(r[campo] is None, f"{identificador}: nulo obrigatorio em {campo}")
            motivo = "DESISTENCIA" if prazo < fechar_em else "FECHAMENTO"
            exigir(r["motivo_abandono"] == motivo, f"{identificador}: motivo incorreto")
            exigir(saida == min(prazo, fechar_em), f"{identificador}: abandono fora do prazo")
            exigir(saida > entrada, f"{identificador}: espera invalida")

        elif r["status"] == "ATENDIDA":
            exigir(r["motivo_abandono"] is None, f"{identificador}: motivo indevido")
            profissional = r["atendente_id"]
            exigir(profissional in atendentes, f"{identificador}: atendente invalido")
            exigir(
                r["disponibilidade_id"] in escalas,
                f"{identificador}: disponibilidade inexistente"
            )
            d = escalas[r["disponibilidade_id"]]
            exigir(
                d["atendente_id"] == profissional
                and d["fila_id"] == r["fila_id"],
                f"{identificador}: disponibilidade de outro atendente ou fila"
            )
            inicio = r["inicio_atendimento_em"]
            conferir_data(inicio, "inicio_atendimento")
            exigir(
                entrada <= inicio <= prazo and inicio < fechar_em,
                f"{identificador}: inicio invalido"
            )
            inteiro(
                r["pos_atendimento_segundos"], 0,
                config["pos_atendimento"]["segundos_positivos_max"], "pos efetivo"
            )
            exigir(r["pos_atendimento_segundos"] == pos, f"{identificador}: pos divergente")
            exigir(
                saida == inicio + timedelta(seconds=contato),
                f"{identificador}: duracao divergente"
            )
            fim_ocupacao = saida + timedelta(seconds=pos)
            exigir(
                d["inicio_disponibilidade_em"] <= inicio
                and fim_ocupacao <= d["fim_disponibilidade_em"]
                and fim_ocupacao <= datetime.combine(entrada.date(), fim_trabalho),
                f"{identificador}: ocupacao fora da disponibilidade"
            )
            ocupacoes.setdefault(profissional, []).append((inicio, fim_ocupacao))
        else:
            raise ValueError(f"{identificador}: status invalido")

    sem_sobreposicao(ocupacoes, "Ocupacao")
    return {
        "chamadas_conferidas": len(resultados),
        "disponibilidades_conferidas": len(disponibilidades),
    }
