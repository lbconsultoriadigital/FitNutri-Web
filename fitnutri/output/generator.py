"""
FitNutri Local - Gerador de Laudos
Converte o contexto do pipeline em laudos formatados (Markdown, HTML).
"""

import logging
from datetime import datetime
from typing import Optional
from ..models.schemas import ContextoPipeline, LaudoFinal

logger = logging.getLogger(__name__)


class LaudoGenerator:
    """Gera laudos clínicos formatados a partir do contexto do pipeline."""

    def gerar_laudo(self, contexto: ContextoPipeline) -> tuple[LaudoFinal, str, str]:
        """Gera o laudo final completo.

        Returns:
            tuple: (LaudoFinal, conteudo_markdown, conteudo_html)
        """
        laudo = getattr(contexto, "laudo_final", None)

        if not laudo or not isinstance(laudo, LaudoFinal):
            # Cria um LaudoFinal básico se o orquestrador não preencheu
            laudo = LaudoFinal(
                paciente=contexto.paciente.dados_pessoais.nome if contexto.paciente else "Paciente",
                data_geracao=datetime.now(),
                sumario_executivo="Laudo consolidado automaticamente.",
                anamnese=contexto.paciente,
                analise_exames=contexto.analise_exames,
                protocolo_suplementacao=contexto.protocolo_suplementacao,
                plano_alimentar=contexto.plano_alimentar,
                plano_treino=contexto.plano_treino,
            )

        conteudo_md = self._gerar_markdown(laudo, contexto)
        conteudo_html = self._gerar_html(conteudo_md)

        return laudo, conteudo_md, conteudo_html

    def _gerar_markdown(self, laudo: LaudoFinal, ctx: ContextoPipeline) -> str:
        """Gera o laudo em formato Markdown."""
        p = laudo.anamnese
        partes = []

        # ─── Cabeçalho ──────────────────────────────────────────────────
        partes.append(f"# 🏥 LAUDO CLÍNICO INTEGRADO — FitNutri\n")
        partes.append(f"**Paciente:** {laudo.paciente}")
        partes.append(f"**Data:** {laudo.data_geracao.strftime('%d/%m/%Y')}")
        partes.append(f"**Responsável Clínico:** Equipe Multidisciplinar FitNutri")
        partes.append(f"**Versão do Laudo:** {laudo.versao}")
        partes.append(f"\n---\n")

        # ─── Sumário Executivo ──────────────────────────────────────────
        if laudo.sumario_executivo:
            partes.append(f"## 📋 1. SUMÁRIO EXECUTIVO\n")
            partes.append(laudo.sumario_executivo)
            partes.append("")

        # ─── Dados do Paciente ──────────────────────────────────────────
        if p:
            partes.append(f"## 👤 2. DADOS DO PACIENTE\n")
            dp = p.dados_pessoais
            # Tabela
            partes.append("| Campo | Valor |")
            partes.append("|-------|-------|")
            partes.append(f"| **Nome** | {dp.nome} |")
            partes.append(f"| **Idade** | {dp.idade} anos |")
            partes.append(f"| **Peso** | {dp.peso_kg} kg |")
            partes.append(f"| **Altura** | {dp.altura_m} m |")
            imc = dp.imc or (dp.peso_kg / (dp.altura_m ** 2))
            partes.append(f"| **IMC** | {imc:.1f} kg/m² |")
            partes.append(f"| **Sexo** | {dp.sexo.value} |")
            partes.append(f"| **Profissão** | {dp.profissao} |")
            partes.append(f"| **Objetivo** | {dp.objetivo.value} |")
            if dp.objetivo_descricao:
                partes.append(f"| **Descrição** | {dp.objetivo_descricao} |")
            partes.append("")

        # ─── Análise de Exames ─────────────────────────────────────────
        if laudo.analise_exames:
            a = laudo.analise_exames
            partes.append(f"## 🔬 3. ANÁLISE DE EXAMES LABORATORIAIS\n")
            partes.append(f"*Parecer do Dr. Henrique Mendonça — Análises Clínicas*\n")

            if a.marcadores:
                partes.append("| Marcador | Valor | Referência | Status | Conduta |")
                partes.append("|----------|-------|------------|--------|---------|")
                for m in a.marcadores:
                    emoji = {"critico": "🔴", "atencao": "🟡", "normal": "🟢"}.get(m.status, "⚪")
                    partes.append(f"| {m.nome} | {m.valor} | {m.referencia} | {emoji} {m.status} | {m.conduta} |")
                partes.append("")

            if a.alertas_criticos:
                partes.append("### ⚠️ Alertas Críticos\n")
                for alerta in a.alertas_criticos:
                    partes.append(f"- 🔴 {alerta}")
                partes.append("")

            if a.parecer_medico:
                partes.append("### 📝 Parecer\n")
                partes.append(f">{a.parecer_medico}")
                partes.append("")

        # ─── Suplementação ──────────────────────────────────────────────
        if laudo.protocolo_suplementacao:
            s = laudo.protocolo_suplementacao
            partes.append(f"## 💊 4. PROTOCOLO DE SUPLEMENTAÇÃO\n")
            partes.append(f"*Parecer da Dra. Carolina Castro — Nutracêutica Clínica*\n")

            for sup in s.suplementos:
                partes.append(f"### {sup.nome}\n")
                partes.append(f"- **Dosagem:** {sup.dosagem}")
                partes.append(f"- **Posologia:** {sup.posologia}")
                partes.append(f"- **Duração:** {sup.duracao}")
                if sup.justificativa:
                    partes.append(f"- **Justificativa:** {sup.justificativa}")
                if sup.evidencias:
                    partes.append(f"- **Evidências:** {sup.evidencias}")
                partes.append("")

            if s.interacoes:
                partes.append("### ⚠️ Interações\n")
                for inter in s.interacoes:
                    partes.append(f"- {inter}")
                partes.append("")

            if s.contraindicacoes:
                partes.append("### 🚫 Contraindicações\n")
                for contra in s.contraindicacoes:
                    partes.append(f"- {contra}")
                partes.append("")

            if s.observacoes_gerais:
                partes.append(f"### Observações\n")
                partes.append(s.observacoes_gerais)
                partes.append("")

        # ─── Plano Alimentar ────────────────────────────────────────────
        if laudo.plano_alimentar:
            pa = laudo.plano_alimentar
            partes.append(f"## 🥗 5. PLANO ALIMENTAR PERSONALIZADO\n")
            partes.append(f"*Parecer de Felipe Leone — Nutricionista Clínico*\n")

            partes.append("### 📊 Cálculos Metabólicos\n")
            partes.append("| Métrica | Valor |")
            partes.append("|---------|-------|")
            if pa.tmb_kcal:
                partes.append(f"| **TMB (Mifflin-St Jeor)** | {pa.tmb_kcal:.0f} kcal |")
            if pa.get_kcal:
                partes.append(f"| **GET (Gasto Energético Total)** | {pa.get_kcal:.0f} kcal |")
            if pa.ajuste_kcal:
                delta = pa.ajuste_kcal - pa.get_kcal if pa.get_kcal else 0
                tipo = "déficit" if delta < 0 else "superávit"
                partes.append(f"| **Ajuste ({tipo})** | {pa.ajuste_kcal:.0f} kcal ({delta:+.0f} kcal) |")
            partes.append("")

            partes.append("### 🎯 Metas de Macronutrientes\n")
            partes.append("| Nutriente | Quantidade |")
            partes.append("|-----------|------------|")
            if pa.proteinas_g:
                partes.append(f"| **Proteínas** | {pa.proteinas_g:.0f}g |")
            if pa.carboidratos_g:
                partes.append(f"| **Carboidratos** | {pa.carboidratos_g:.0f}g |")
            if pa.gorduras_g:
                partes.append(f"| **Gorduras** | {pa.gorduras_g:.0f}g |")
            if pa.fibras_g:
                partes.append(f"| **Fibras** | {pa.fibras_g:.0f}g |")
            if pa.meta_hidrica_l:
                partes.append(f"| **Meta Hídrica** | {pa.meta_hidrica_l:.1f}L |")
            partes.append("")

            if pa.refeicoes:
                partes.append("### 🍽️ Estrutura do Cardápio\n")
                for ref in pa.refeicoes:
                    partes.append(f"#### {ref.nome} ({ref.horario})\n")
                    for alimento in ref.alimentos:
                        partes.append(f"- {alimento}")
                    if ref.observacoes:
                        partes.append(f"  > {ref.observacoes}")
                    partes.append("")

            if pa.observacoes_gerais:
                partes.append(f"### Observações\n")
                partes.append(pa.observacoes_gerais)
                partes.append("")

        # ─── Plano de Treino ────────────────────────────────────────────
        if laudo.plano_treino:
            pt = laudo.plano_treino
            partes.append(f"## 🏋️ 6. PLANO DE TREINO\n")
            partes.append(f"*Parecer de Daniel Rocha — Fisiologia do Exercício*\n")

            partes.append(f"**Estrutura:** {pt.estrutura}")
            partes.append(f"**Frequência:** {pt.frequencia_semanal}x/semana")
            partes.append("")

            if pt.aquecimento:
                partes.append(f"### 🔥 Aquecimento Clínico\n")
                partes.append(pt.aquecimento)
                partes.append("")

            if pt.dias_treino:
                partes.append("### 📅 Periodização Semanal\n")
                for dia in pt.dias_treino:
                    partes.append(f"#### {dia.dia} — {dia.foco}\n")
                    for ex in dia.exercicios:
                        partes.append(f"- {ex}")
                    partes.append("")

            if pt.observacoes:
                partes.append("### Observações\n")
                for obs in pt.observacoes:
                    partes.append(f"- {obs}")
                partes.append("")

        # ─── Recomendações e Próximos Passos ────────────────────────────
        if laudo.recomendacoes_gerais:
            partes.append(f"## 📌 7. RECOMENDAÇÕES GERAIS\n")
            for rec in laudo.recomendacoes_gerais:
                partes.append(f"- {rec}")
            partes.append("")

        if laudo.proximos_passos:
            partes.append(f"## ▶️ 8. PRÓXIMOS PASSOS\n")
            for passo in laudo.proximos_passos:
                partes.append(f"- [ ] {passo}")
            partes.append("")

        # ─── Rodapé ─────────────────────────────────────────────────────
        data_formatada = laudo.data_geracao.strftime("%d/%m/%Y às %H:%M")
        partes.append(f"---\n")
        partes.append(f"*Laudo gerado em {data_formatada} pelo Sistema FitNutri Local.*")
        partes.append(f"*Este documento é uma sugestão de conduta baseada em análise científica dos dados fornecidos.*")
        partes.append(f"*Recomendamos a validação de todos os protocolos com profissionais de saúde presenciais.*")

        return "\n".join(partes)

    def _gerar_html(self, conteudo_md: str) -> str:
        """Gera versão HTML simples a partir do Markdown."""
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Laudo Clínico FitNutri</title>
    <style>
        @page {{
            margin: 2cm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a2e;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        h1 {{ color: #0f3460; border-bottom: 3px solid #e94560; padding-bottom: 10px; }}
        h2 {{ color: #16213e; margin-top: 30px; border-bottom: 1px solid #ddd; }}
        h3 {{ color: #0f3460; margin-top: 20px; }}
        h4 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #0f3460; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9fb; }}
        blockquote {{
            border-left: 4px solid #e94560;
            padding: 10px 20px;
            margin: 15px 0;
            background: #fdf2f2;
            font-style: italic;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="content">
    {self._md_simples_para_html(conteudo_md)}
    </div>
    <div class="footer">
        <p><em>Documento gerado automaticamente pelo Sistema FitNutri Local.</em></p>
    </div>
</body>
</html>"""
        return html

    def _md_simples_para_html(self, md: str) -> str:
        """Conversão simples de Markdown para HTML (sem dependências pesadas)."""
        import html as html_mod

        linhas = md.split("\n")
        html_linhas = []
        in_table = False
        in_list = False
        in_blockquote = False

        for linha in linhas:
            linha_escaped = html_mod.escape(linha)

            # Tabela
            if linha.startswith("|"):
                if not in_table:
                    in_table = True
                cols = [c.strip() for c in linha.split("|")[1:-1]]
                if all(c.startswith("-") for c in cols if c):
                    continue  # Pula linha separadora
                html_linhas.append(
                    "<tr>" + "".join(f"<td>{c}</td>" for c in cols) + "</tr>"
                )
                continue
            else:
                if in_table:
                    html_linhas.append("</table>")
                    in_table = False

            # Headers
            if linha.startswith("### "):
                html_linhas.append(f"<h3>{linha[4:]}</h3>")
            elif linha.startswith("## "):
                html_linhas.append(f"<h2>{linha[3:]}</h2>")
            elif linha.startswith("# "):
                html_linhas.append(f"<h1>{linha[2:]}</h1>")

            # Listas
            elif linha.startswith("- ") or linha.startswith("* "):
                if not in_list:
                    html_linhas.append("<ul>")
                    in_list = True
                html_linhas.append(f"<li>{linha[2:]}</li>")
            elif linha.startswith("  > "):
                html_linhas.append(f"<blockquote><p>{linha[4:]}</p></blockquote>")
            elif linha.startswith(">"):
                html_linhas.append(f"<blockquote><p>{linha[2:]}</p></blockquote>")

            # Parágrafos
            elif linha.strip() == "":
                if in_list:
                    html_linhas.append("</ul>")
                    in_list = False
            else:
                # Negrito ** **
                linha_html = linha_escaped.replace("**", "<strong>", 1)
                if "**" in linha_html:
                    linha_html = linha_html.replace("**", "</strong>", 1)
                # Itálico * *
                linha_html = linha_html.replace("*", "<em>", 1)
                if "*" in linha_html:
                    linha_html = linha_html.replace("*", "</em>", 1)
                html_linhas.append(f"<p>{linha_html}</p>")

        if in_table:
            html_linhas.append("</table>")
        if in_list:
            html_linhas.append("</ul>")

        return "\n".join(html_linhas)
