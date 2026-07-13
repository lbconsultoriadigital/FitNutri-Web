from __future__ import annotations

import re

import markdown


def render_report_html(markdown_text: str) -> str:
    """Renderiza o Markdown do laudo com suporte real a tabelas, listas e ênfases."""
    cleaned = re.sub(r"<[^>]+>", "", markdown_text or "")
    body = markdown.markdown(
        cleaned,
        extensions=["tables", "sane_lists", "nl2br"],
        output_format="html5",
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Laudo clínico FitNutri</title>
  <style>
    :root {{
      --graphite:#121716;
      --forest:#0b4f3c;
      --lime:#b7f21c;
      --off:#f3f4ef;
      --line:#dfe4df;
      --muted:#66736d;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      background:#fff;
      color:var(--graphite);
      font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      font-size:15px;
      line-height:1.65;
    }}
    .report {{
      width:min(980px,100%);
      margin:0 auto;
      padding:42px 48px 64px;
    }}
    h1 {{
      color:var(--graphite);
      font-size:2rem;
      line-height:1.18;
      letter-spacing:-.04em;
      border-bottom:4px solid var(--lime);
      padding-bottom:18px;
      margin:0 0 24px;
    }}
    h2 {{
      color:var(--forest);
      font-size:1.32rem;
      line-height:1.3;
      letter-spacing:-.025em;
      border-bottom:1px solid var(--line);
      padding-bottom:9px;
      margin:34px 0 16px;
    }}
    h3 {{ color:#173d31;font-size:1.02rem;margin:24px 0 10px; }}
    h4 {{ color:var(--graphite);font-size:.95rem;margin:19px 0 8px; }}
    p {{ margin:0 0 12px; }}
    strong {{ font-weight:780; }}
    em {{ color:#47534e; }}
    ul,ol {{ margin:8px 0 16px;padding-left:22px; }}
    li {{ margin:5px 0; }}
    blockquote {{
      margin:16px 0;
      border-left:4px solid var(--lime);
      background:#f6faef;
      padding:13px 16px;
      color:#34443d;
    }}
    table {{
      width:100%;
      min-width:640px;
      display:block;
      overflow-x:auto;
      border-collapse:separate;
      border-spacing:0;
      border:1px solid var(--line);
      border-radius:12px;
      margin:16px 0 22px;
    }}
    thead th {{
      background:var(--forest);
      color:#fff;
      text-align:left;
      font-size:.78rem;
      letter-spacing:.02em;
      padding:11px 12px;
    }}
    tbody td {{
      vertical-align:top;
      padding:11px 12px;
      border-top:1px solid var(--line);
      font-size:.88rem;
    }}
    tbody tr:nth-child(even) td {{ background:#f8faf7; }}
    hr {{ border:0;border-top:1px solid var(--line);margin:28px 0; }}
    .footer {{
      margin-top:44px;
      padding-top:18px;
      border-top:1px solid var(--line);
      color:var(--muted);
      font-size:.78rem;
    }}
    @media(max-width:720px) {{
      .report {{ padding:25px 18px 42px; }}
      h1 {{ font-size:1.55rem; }}
      h2 {{ font-size:1.12rem; }}
    }}
    @media print {{
      .report {{ width:100%;max-width:none;padding:0; }}
      body {{ font-size:12px; }}
      h1 {{ font-size:22px; }}
      h2 {{ font-size:16px;break-after:avoid; }}
      table {{ break-inside:avoid; }}
    }}
  </style>
</head>
<body>
  <main class="report">
    {body}
    <footer class="footer">Documento gerado pelo FitNutri. Rascunho sujeito à revisão e aprovação profissional.</footer>
  </main>
</body>
</html>"""
