"""Casos independentes, incluindo dados deliberadamente invalidos."""

import copy
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from src.validacao_integridade import validar_integridade


CONFIG = json.loads(
    (Path(__file__).resolve().parents[1] / "config.json")
    .read_text(encoding="utf-8")
)


class TestValidacaoIntegridade(unittest.TestCase):
    def setUp(self):
        t = datetime(2026, 1, 1, 10)
        self.entradas = [{
            "chamada_id": "CH000001", "fila_id": "F01",
            "entrada_em": t, "tolerancia_espera_segundos": 60,
            "duracao_contato_planejada_segundos": 60,
            "pos_atendimento_planejado_segundos": 30,
        }]
        self.disponibilidades = [{
            "disponibilidade_id": "DISP000001",
            "atendente_id": "AT01", "fila_id": "F01",
            "inicio_disponibilidade_em": t,
            "fim_disponibilidade_em": t + timedelta(hours=1),
        }]
        self.resultados = [{
            **self.entradas[0], "status": "ATENDIDA",
            "atendente_id": "AT01", "disponibilidade_id": "DISP000001",
            "inicio_atendimento_em": t + timedelta(seconds=20),
            "saida_em": t + timedelta(seconds=80),
            "pos_atendimento_segundos": 30, "motivo_abandono": None,
        }]

    def validar(self):
        return validar_integridade(
            self.entradas, self.disponibilidades, self.resultados, CONFIG
        )

    def test_aceita_caso_manual(self):
        self.assertEqual(self.validar()["chamadas_conferidas"], 1)

    def test_rejeita_duplicidade(self):
        self.resultados.append(copy.deepcopy(self.resultados[0]))
        with self.assertRaisesRegex(ValueError, "duplicidade"):
            self.validar()

    def test_rejeita_referencia_inexistente(self):
        self.resultados[0]["disponibilidade_id"] = "INEXISTENTE"
        with self.assertRaisesRegex(ValueError, "disponibilidade inexistente"):
            self.validar()

    def test_rejeita_nulo_em_atendida(self):
        self.resultados[0]["atendente_id"] = None
        with self.assertRaisesRegex(ValueError, "atendente invalido"):
            self.validar()

    def test_rejeita_disponibilidade_de_outra_fila(self):
        self.disponibilidades[0]["fila_id"] = "F02"
        with self.assertRaisesRegex(ValueError, "outro atendente ou fila"):
            self.validar()

    def test_rejeita_duracao_adulterada(self):
        self.resultados[0]["saida_em"] += timedelta(seconds=1)
        with self.assertRaisesRegex(ValueError, "duracao divergente"):
            self.validar()

    def test_rejeita_sobreposicao_de_ocupacao(self):
        entrada = {**self.entradas[0], "chamada_id": "CH000002"}
        resultado = {**self.resultados[0], "chamada_id": "CH000002"}
        self.entradas.append(entrada)
        self.resultados.append(resultado)
        with self.assertRaisesRegex(ValueError, "Ocupacao: sobreposicao"):
            self.validar()

    def test_aceita_abandono_e_rejeita_atraso(self):
        r = self.resultados[0]
        r.update(
            status="ABANDONADA", atendente_id=None, disponibilidade_id=None,
            inicio_atendimento_em=None, pos_atendimento_segundos=None,
            motivo_abandono="DESISTENCIA",
            saida_em=r["entrada_em"] + timedelta(seconds=60),
        )
        self.validar()
        r["saida_em"] += timedelta(seconds=1)
        with self.assertRaisesRegex(ValueError, "abandono fora do prazo"):
            self.validar()


if __name__ == "__main__":
    unittest.main()
