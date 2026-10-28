"""Testes das entradas; nao validam atribuicao ou abandono."""

import json
import random
import unittest
from datetime import date, time, timedelta
from pathlib import Path

from src.disponibilidade import gerar_disponibilidades
from src.entradas import gerar_entradas


RAIZ = Path(__file__).resolve().parents[1]


def preparar(config):
    rng = random.Random(config["semente"])
    disponibilidade = gerar_disponibilidades(config, rng)
    entradas = gerar_entradas(config, rng)
    return disponibilidade, entradas


class TestEntradas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(
            (RAIZ / "config.json").read_text(encoding="utf-8")
        )
        cls.disponibilidade, cls.entradas = preparar(cls.config)

    def test_volume_ids_e_ordem(self):
        self.assertEqual(len(self.entradas), 3000)
        self.assertEqual(
            [r["chamada_id"] for r in self.entradas],
            [f"CH{i:06d}" for i in range(1, 3001)]
        )
        instantes = [r["entrada_em"] for r in self.entradas]
        self.assertEqual(instantes, sorted(instantes))

    def test_cobertura_e_horarios(self):
        esperados = {
            date(2026, 1, 1) + timedelta(days=i) for i in range(90)
        }
        self.assertEqual(
            {r["entrada_em"].date() for r in self.entradas}, esperados
        )
        for r in self.entradas:
            self.assertGreaterEqual(r["entrada_em"].time(), time(8))
            self.assertLess(r["entrada_em"].time(), time(18))
            self.assertEqual(r["entrada_em"].microsecond, 0)

    def test_filas_e_tempos_planejados(self):
        limites = {"F01": (30, 300), "F02": (180, 1200), "F03": (120, 900)}
        for r in self.entradas:
            self.assertIn(r["fila_id"], limites)
            minimo, maximo = limites[r["fila_id"]]
            contato = r["duracao_contato_planejada_segundos"]
            tolerancia = r["tolerancia_espera_segundos"]
            pos = r["pos_atendimento_planejado_segundos"]
            for valor in (contato, tolerancia, pos):
                self.assertIs(type(valor), int)
            self.assertGreaterEqual(contato, minimo)
            self.assertLessEqual(contato, maximo)
            self.assertGreaterEqual(tolerancia, 5)
            self.assertLessEqual(tolerancia, 600)
            self.assertGreaterEqual(pos, 0)
            self.assertLessEqual(pos, 180)

    def test_repetibilidade_da_sequencia_completa(self):
        disponibilidade, entradas = preparar(self.config)
        self.assertEqual(disponibilidade, self.disponibilidade)
        self.assertEqual(entradas, self.entradas)

    def test_sem_resultados_de_atendimento_inventados(self):
        campos = {
            "chamada_id", "fila_id", "entrada_em",
            "tolerancia_espera_segundos",
            "duracao_contato_planejada_segundos",
            "pos_atendimento_planejado_segundos",
        }
        for r in self.entradas:
            self.assertEqual(set(r), campos)


if __name__ == "__main__":
    unittest.main()
