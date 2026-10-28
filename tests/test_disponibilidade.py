"""Testes desta etapa; não validam a simulação de chamadas."""

import json
import random
import unittest
from datetime import date, time
from pathlib import Path

from src.disponibilidade import gerar_disponibilidades


RAIZ = Path(__file__).resolve().parents[1]


class TestDisponibilidade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(
            (RAIZ / "config.json").read_text(encoding="utf-8")
        )
        cls.registros = gerar_disponibilidades(
            cls.config, random.Random(cls.config["semente"])
        )

    def test_repetibilidade(self):
        repeticao = gerar_disponibilidades(
            self.config, random.Random(self.config["semente"])
        )
        self.assertEqual(self.registros, repeticao)

    def test_ids_e_referencias(self):
        self.assertGreater(len(self.registros), 0)
        ids = [r["disponibilidade_id"] for r in self.registros]
        self.assertEqual(len(ids), len(set(ids)))
        atendentes = {f"AT{i:02d}" for i in range(1, 9)}
        for r in self.registros:
            self.assertIn(r["atendente_id"], atendentes)
            self.assertIn(r["fila_id"], {"F01", "F02", "F03"})

    def test_limites_temporais(self):
        for r in self.registros:
            inicio = r["inicio_disponibilidade_em"]
            fim = r["fim_disponibilidade_em"]
            self.assertGreaterEqual(inicio.date(), date(2026, 1, 1))
            self.assertLessEqual(inicio.date(), date(2026, 3, 31))
            self.assertEqual(inicio.date(), fim.date())
            self.assertGreaterEqual(inicio.time(), time(8))
            self.assertLess(inicio.time(), time(18))
            self.assertLessEqual(fim.time(), time(18, 30))
            self.assertLess(inicio, fim)

    def test_sem_sobreposicao_inclusive_entre_filas(self):
        fim_anterior = {}
        for r in sorted(self.registros, key=lambda x: (
            x["atendente_id"], x["inicio_disponibilidade_em"]
        )):
            atendente = r["atendente_id"]
            if atendente in fim_anterior:
                self.assertGreaterEqual(
                    r["inicio_disponibilidade_em"],
                    fim_anterior[atendente],
                )
            fim_anterior[atendente] = r["fim_disponibilidade_em"]

    def test_intervalos_correspondem_a_perfis_aprovados(self):
        permitidos = {
            (),
            (("08:00:00", "10:00:00"), ("10:15:00", "13:00:00")),
            (("13:00:00", "15:00:00"), ("15:15:00", "18:30:00")),
            (("09:00:00", "12:00:00"), ("14:00:00", "18:30:00")),
        }
        por_dia = {}
        for r in self.registros:
            chave = (
                r["atendente_id"], r["inicio_disponibilidade_em"].date()
            )
            por_dia.setdefault(chave, []).append((
                r["inicio_disponibilidade_em"].strftime("%H:%M:%S"),
                r["fim_disponibilidade_em"].strftime("%H:%M:%S"),
            ))
        for intervalos in por_dia.values():
            self.assertIn(tuple(sorted(intervalos)), permitidos)

    def test_disponibilidade_variavel(self):
        padroes = set()
        por_dia = {}
        for r in self.registros:
            chave = (
                r["atendente_id"], r["inicio_disponibilidade_em"].date()
            )
            por_dia.setdefault(chave, []).append((
                r["inicio_disponibilidade_em"].strftime("%H:%M:%S"),
                r["fim_disponibilidade_em"].strftime("%H:%M:%S"),
            ))
        for intervalos in por_dia.values():
            padroes.add(tuple(sorted(intervalos)))
        self.assertGreater(len(padroes), 1)
        self.assertEqual(
            {r["atendente_id"] for r in self.registros},
            {f"AT{i:02d}" for i in range(1, 9)},
        )


if __name__ == "__main__":
    unittest.main()
