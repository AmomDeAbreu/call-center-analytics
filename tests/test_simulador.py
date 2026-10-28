"""Casos manuais para decisões FIFO e limites temporais."""

import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from src.simulador import simular


CONFIG = json.loads(
    (Path(__file__).resolve().parents[1] / "config.json")
    .read_text(encoding="utf-8")
)


def instante(hora):
    return datetime.fromisoformat("2026-01-01 " + hora)


def chamada(numero, entrada, tolerancia=60, contato=60, pos=0):
    return {
        "chamada_id": f"CH{numero:06d}",
        "fila_id": "F01",
        "entrada_em": instante(entrada),
        "tolerancia_espera_segundos": tolerancia,
        "duracao_contato_planejada_segundos": contato,
        "pos_atendimento_planejado_segundos": pos,
    }


def disponibilidade(numero, inicio, fim, atendente=None, fila="F01"):
    return {
        "disponibilidade_id": f"DISP{numero:06d}",
        "atendente_id": atendente or f"AT{numero:02d}",
        "fila_id": fila,
        "inicio_disponibilidade_em": instante(inicio),
        "fim_disponibilidade_em": instante(fim),
    }


class TestSimulador(unittest.TestCase):
    def test_duas_no_limite_dois_profissionais(self):
        chamadas = [chamada(1, "09:59:00"), chamada(2, "09:59:00")]
        turnos = [
            disponibilidade(1, "10:00:00", "11:00:00"),
            disponibilidade(2, "10:00:00", "11:00:00"),
        ]
        resultado = simular(chamadas, turnos, CONFIG)
        self.assertEqual([r["status"] for r in resultado], ["ATENDIDA"] * 2)
        self.assertEqual(
            [r["inicio_atendimento_em"] for r in resultado],
            [instante("10:00:00")] * 2
        )
        self.assertEqual(
            [r["atendente_id"] for r in resultado], ["AT01", "AT02"]
        )

    def test_primeira_nao_cabe_expira_segunda_atendida(self):
        chamadas = [
            chamada(1, "09:59:00", contato=300),
            chamada(2, "09:59:00", contato=60),
        ]
        turnos = [disponibilidade(1, "10:00:00", "10:02:00")]
        a, b = simular(chamadas, turnos, CONFIG)
        self.assertEqual(a["motivo_abandono"], "DESISTENCIA")
        self.assertEqual(a["saida_em"], instante("10:00:00"))
        self.assertEqual(b["status"], "ATENDIDA")
        self.assertEqual(b["inicio_atendimento_em"], instante("10:00:00"))

    def test_posterior_expira_sem_ultrapassar_primeira(self):
        chamadas = [
            chamada(1, "09:59:00", tolerancia=180, contato=300),
            chamada(2, "09:59:30", tolerancia=30, contato=60),
        ]
        turnos = [disponibilidade(1, "10:00:00", "10:02:00")]
        a, b = simular(chamadas, turnos, CONFIG)
        self.assertEqual(a["saida_em"], instante("10:02:00"))
        self.assertEqual(b["saida_em"], instante("10:00:00"))
        self.assertEqual(b["motivo_abandono"], "DESISTENCIA")

    def test_expiracao_sem_outro_evento(self):
        r, = simular([chamada(1, "10:00:00", tolerancia=37)], [], CONFIG)
        self.assertEqual(r["saida_em"], instante("10:00:37"))
        self.assertEqual(r["motivo_abandono"], "DESISTENCIA")

    def test_liberacao_as_18_nao_permite_novo_atendimento(self):
        chamadas = [
            chamada(1, "17:59:00", contato=60),
            chamada(2, "17:59:30", tolerancia=30),
        ]
        turnos = [disponibilidade(1, "17:00:00", "18:30:00")]
        a, b = simular(chamadas, turnos, CONFIG)
        self.assertEqual(a["status"], "ATENDIDA")
        self.assertEqual(b["motivo_abandono"], "FECHAMENTO")
        self.assertEqual(b["saida_em"], instante("18:00:00"))

    def test_pos_atendimento_impede_sobreposicao(self):
        chamadas = [
            chamada(1, "10:00:00", contato=60, pos=30),
            chamada(2, "10:00:30", tolerancia=120),
        ]
        turnos = [disponibilidade(1, "10:00:00", "11:00:00")]
        a, b = simular(chamadas, turnos, CONFIG)
        self.assertEqual(
            b["inicio_atendimento_em"],
            a["saida_em"] + timedelta(seconds=30)
        )

    def test_ocupacao_pode_terminar_apos_18(self):
        chamadas = [chamada(1, "17:59:00", contato=300, pos=180)]
        turnos = [disponibilidade(1, "17:00:00", "18:07:00")]
        r, = simular(chamadas, turnos, CONFIG)
        self.assertEqual(r["status"], "ATENDIDA")
        self.assertEqual(
            r["saida_em"] + timedelta(seconds=r["pos_atendimento_segundos"]),
            instante("18:07:00")
        )

    def test_nao_combina_intervalos_adjacentes(self):
        chamadas = [chamada(1, "10:00:30", tolerancia=60, contato=60)]
        turnos = [
            disponibilidade(1, "10:00:00", "10:01:00", atendente="AT01"),
            disponibilidade(2, "10:01:00", "10:02:00", atendente="AT01"),
        ]
        r, = simular(chamadas, turnos, CONFIG)
        self.assertEqual(r["inicio_atendimento_em"], instante("10:01:00"))
        self.assertEqual(r["disponibilidade_id"], "DISP000002")

    def test_rejeita_disponibilidade_sobreposta_entre_filas(self):
        turnos = [
            disponibilidade(1, "10:00:00", "11:00:00", atendente="AT01"),
            disponibilidade(
                2, "10:59:59", "12:00:00", atendente="AT01", fila="F02"
            ),
        ]
        with self.assertRaisesRegex(ValueError, "Sobreposicao"):
            simular([], turnos, CONFIG)


if __name__ == "__main__":
    unittest.main()
