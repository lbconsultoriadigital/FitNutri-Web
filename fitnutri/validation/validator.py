"""
FitNutri - Validação de Dados & Sistema de Escalação
Valida dados de entrada e detecta alertas críticos que requerem escalação.
"""

import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class AlertaSeveridade(Enum):
    """Níveis de severidade de alerta."""
    VERDE = "ok"          # Tudo normal
    AMARELO = "atencao"   # Atenção, monitor
    VERMELHO = "critico"  # Crítico, escalação imediata
    PRETO = "emergencia"  # Emergência, atendimento imediato


class ValidadorFitNutri:
    """Valida dados de pacientes e detecta alertas críticos."""

    @staticmethod
    def validar_dados_pessoais(dados: Dict) -> Tuple[bool, List[str]]:
        """
        Valida dados pessoais do paciente.
        
        Returns:
            (é_válido, lista_de_erros)
        """
        erros = []

        # Validar peso
        peso = dados.get("peso_kg", 0)
        if peso <= 0 or peso > 300:
            erros.append(f"Peso inválido: {peso}kg. Intervalo esperado: 1-300kg")

        # Validar altura
        altura = dados.get("altura_m", 0)
        if altura <= 0 or altura > 2.5:
            erros.append(f"Altura inválida: {altura}m. Intervalo esperado: 0.5-2.5m")

        # Validar IMC coerência
        if peso > 0 and altura > 0:
            imc_calculado = peso / (altura ** 2)
            imc_reportado = dados.get("imc", 0)
            
            if imc_reportado and abs(imc_calculado - imc_reportado) > 1:
                erros.append(
                    f"IMC incoerente. Calculado: {imc_calculado:.1f}, "
                    f"Reportado: {imc_reportado}. Verificar peso/altura."
                )

        # Validar idade
        idade = dados.get("idade", 0)
        if idade < 14 or idade > 120:
            erros.append(f"Idade inválida: {idade}. Intervalo esperado: 14-120")

        return len(erros) == 0, erros

    @staticmethod
    def validar_habitos_vida(dados: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Valida hábitos de vida. Retorna avisos além de erros.
        
        Returns:
            (é_válido, lista_de_erros, lista_de_avisos)
        """
        erros = []
        avisos = []

        # Sono
        sono_horas = dados.get("sono_horas", 0)
        if sono_horas < 4 or sono_horas > 12:
            avisos.append(f"Sono incomum: {sono_horas}h. Ideal 7-9h para recuperação.")

        # Agua
        agua_litros = dados.get("agua_litros", 0)
        if agua_litros < 1:
            avisos.append("Ingestão de água baixa. Meta: 2-3L/dia (35-50ml/kg)")

        # Cafeína
        cafeina_diaria = dados.get("cafeina_diaria", "")
        if "não" in str(cafeina_diaria).lower():
            pass  # OK
        elif any(word in str(cafeina_diaria).lower() for word in ["muito", "alto", ">500"]):
            avisos.append(f"Consumo de cafeína elevado. Limite: 400mg/dia (5 cafés)")

        # Fumante
        if dados.get("fumante", False):
            avisos.append("Paciente fumante. Aumenta risco cardiovascular e reduz performance.")

        return len(erros) == 0, erros, avisos

    @staticmethod
    def validar_exames(exames: Dict) -> Tuple[bool, List[str], List[Dict]]:
        """
        Valida marcadores bioquímicos e detecta red flags.
        
        Returns:
            (é_válido, lista_de_erros, lista_de_red_flags)
            Red flag: {"marcador": "...", "valor": X, "severidade": AlertaSeveridade, "recomendacao": "..."}
        """
        red_flags = []
        erros = []

        if not exames:
            return True, [], []

        # Red flags críticas por marcador
        verificacoes = {
            "glicemia": {
                "valores_criticos": [
                    (250, AlertaSeveridade.VERMELHO, "Glicemia >250mg/dL: risco de hiperglicemia aguda"),
                    (50, AlertaSeveridade.VERMELHO, "Glicemia <50mg/dL: risco de hipoglicemia aguda")
                ]
            },
            "creatinina": {
                "valores_criticos": [
                    (3.0, AlertaSeveridade.VERMELHO, "Creatinina >3.0: função renal severamente comprometida")
                ]
            },
            "tsh": {
                "valores_criticos": [
                    (10, AlertaSeveridade.AMARELO, "TSH >10: possível hipotireoidismo severo")
                ]
            },
            "hemoglobina": {
                "valores_criticos": [
                    (7, AlertaSeveridade.VERMELHO, "Hemoglobina <7: anemia profunda"),
                    (6, AlertaSeveridade.PRETO, "Hemoglobina <6: EMERGÊNCIA - transfusão necessária")
                ]
            },
            "pressao_arterial_sistolica": {
                "valores_criticos": [
                    (180, AlertaSeveridade.VERMELHO, "Pressão >180/120: risco de AVC"),
                ]
            }
        }

        for marcador, config in verificacoes.items():
            valor = exames.get(marcador)
            if valor is None:
                continue

            for limite, severidade, msg in config["valores_criticos"]:
                if valor > limite:
                    red_flags.append({
                        "marcador": marcador,
                        "valor": valor,
                        "severidade": severidade,
                        "recomendacao": msg
                    })

        return len(erros) == 0, erros, red_flags

    @staticmethod
    def validar_relatos_sintomas(relato_texto: str) -> List[Dict]:
        """
        Detecta palavras-chave em relatos de sintomas que indicam escalação.
        
        Returns:
            Lista de alertas detectados
        """
        alertas = []
        
        # Palavras-chave críticas
        criticos = [
            ("dor no peito", AlertaSeveridade.PRETO, "Possível infarto"),
            ("falta de ar", AlertaSeveridade.PRETO, "Possível embolia ou insuficiência cardíaca"),
            ("tontura severa", AlertaSeveridade.VERMELHO, "Tontura com risco de queda"),
            ("convulsão", AlertaSeveridade.PRETO, "Episódio convulsivo"),
            ("perda de consciência", AlertaSeveridade.PRETO, "Síncope ou desmaio"),
            ("dor abdominal severa", AlertaSeveridade.VERMELHO, "Abdômen agudo")
        ]

        relato_lower = relato_texto.lower()
        for palavra_chave, severidade, recomendacao in criticos:
            if palavra_chave in relato_lower:
                alertas.append({
                    "palavra_chave": palavra_chave,
                    "severidade": severidade,
                    "recomendacao": recomendacao
                })

        return alertas

    @staticmethod
    def gerar_disclaimer(severidade: AlertaSeveridade) -> str:
        """Gera disclaimer apropriado baseado na severidade."""
        disclaimers = {
            AlertaSeveridade.VERDE: "✓ Sem alertas identificados.",
            AlertaSeveridade.AMARELO: (
                "⚠️ AVISO: Alguns marcadores requerem atenção. "
                "Recomenda-se acompanhamento médico para esclarecimento."
            ),
            AlertaSeveridade.VERMELHO: (
                "🔴 ALERTA: Marcadores críticos detectados. "
                "RECOMENDA-SE CONSULTA MÉDICA PRESENCIAL URGENTE."
            ),
            AlertaSeveridade.PRETO: (
                "🚨 EMERGÊNCIA: Sintomas graves detectados. "
                "PROCURE PRONTO-SOCORRO IMEDIATAMENTE. "
                "A plataforma FitNutri não substitui atendimento médico de emergência."
            )
        }
        return disclaimers.get(severidade, "Verifique com seu médico.")


class SistemaEscalacao:
    """Gerencia escalação de casos críticos para profissionais."""

    @staticmethod
    def avaliar_necessidade_escalacao(
        contexto: Dict,
        red_flags_exames: List[Dict] = None,
        red_flags_sintomas: List[Dict] = None
    ) -> Tuple[bool, AlertaSeveridade, str]:
        """
        Avalia se o caso requer escalação imediata.
        
        Returns:
            (necessita_escalacao, severidade, mensagem_para_profissional)
        """
        red_flags_exames = red_flags_exames or []
        red_flags_sintomas = red_flags_sintomas or []

        severidade_max = AlertaSeveridade.VERDE

        # Verificar severidade máxima
        for flag in red_flags_exames + red_flags_sintomas:
            flag_sev = flag.get("severidade")
            if flag_sev == AlertaSeveridade.PRETO:
                severidade_max = AlertaSeveridade.PRETO
                break
            elif flag_sev == AlertaSeveridade.VERMELHO:
                severidade_max = AlertaSeveridade.VERMELHO
            elif flag_sev == AlertaSeveridade.AMARELO and severidade_max == AlertaSeveridade.VERDE:
                severidade_max = AlertaSeveridade.AMARELO

        necessita_escalacao = severidade_max != AlertaSeveridade.VERDE

        # Montar mensagem para profissional
        msg = f"Paciente: {contexto.get('paciente_nome', 'Desconhecido')}\n"
        msg += f"Severidade: {severidade_max.value}\n\n"

        if red_flags_exames:
            msg += "RED FLAGS EM EXAMES:\n"
            for flag in red_flags_exames:
                msg += f"- {flag['marcador']}: {flag['valor']} → {flag['recomendacao']}\n"

        if red_flags_sintomas:
            msg += "\nRED FLAGS EM SINTOMAS:\n"
            for flag in red_flags_sintomas:
                msg += f"- {flag['palavra_chave']}: {flag['recomendacao']}\n"

        return necessita_escalacao, severidade_max, msg


# Instâncias globais
validador = ValidadorFitNutri()
escalacao = SistemaEscalacao()
