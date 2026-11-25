"""Prepara a base de vendas Porsche para a dashboard.

Uso: python scripts/preparar_base.py caminho/da/planilha.xlsx

Gera:
  data/vendas_porsche_tratada.csv  -> base tratada, só com colunas usadas
  index.html                        -> atualizado com os dados embutidos
"""
import csv
import json
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent

MESES = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

GRUPO_PAGAMENTO = {
    "Wire Transfer": "Transferência",
    "Bank Transfer": "Transferência",
    "ACH Payment": "Transferência",
    "Credit Card": "Cartão",
    "Debit Card": "Cartão",
    "Financing": "Financiamento",
    "Lease": "Leasing",
    "Cash": "Dinheiro",
    "Crypto Payment": "Cripto",
}


def ano_da_venda(bruto):
    """O ano aparece no texto cru mesmo quando a data é impossível (ex.: 31 de abril)."""
    if hasattr(bruto, "year"):
        return bruto.year
    s = str(bruto)
    m = re.search(r"(20\d\d)", s)
    if m:
        return int(m.group(1))
    m = re.search(r"[/-](\d\d)$", s)  # formatos MM/DD/AA
    return 2000 + int(m.group(1)) if m else None


def recuperar_data(bruto, sanitizada):
    """Segunda regra: datas no formato AAAA/DD/MM que a 1ª regra marcou INVALID."""
    if sanitizada != "INVALID":
        return sanitizada, "original"
    m = re.fullmatch(r"(20\d\d)/(\d\d)/(\d\d)", str(bruto))
    if m:
        a, d, mes = map(int, m.groups())
        if mes <= 12 and d <= 31:
            return f"{a:04d}-{mes:02d}-{d:02d}", "recuperada"
    return "", "invalida"


def main(xlsx):
    ws = openpyxl.load_workbook(xlsx, data_only=True)["Sanitized"]
    linhas = list(ws.iter_rows(values_only=True))
    h = linhas[0]
    col = {nome: h.index(nome) for nome in h}

    saida = []
    for r in linhas[1:]:
        data, status_data = recuperar_data(r[col["sale_date"]], r[col["SaleDateSanitized"]])
        modelo = r[col["PorscheModelSanitized"]]
        pag = r[col["PayMethodSanitized"]]
        saida.append({
            "id": int(r[col["sale_id"]]),
            "data_venda": data,
            "status_data": status_data,
            "ano_venda": ano_da_venda(r[col["sale_date"]]),
            "familia": modelo.split()[0],
            "modelo": modelo,
            "ano_modelo": int(r[col["ModelYearSanitized"]]),
            "preco": float(r[col["SalesPriceSanitized"]]),
            "quilometragem_mi": int(float(r[col["VehicleMileageSanitized"]])),
            "pagamento": pag,
            "grupo_pagamento": GRUPO_PAGAMENTO[pag],
            "cidade": r[col["CitySanitized"]],
            "estado": r[col["StateSanitized"]],
            "status_entrega": r[col["DeliveryStatusSanitized"]],
        })

    (ROOT / "data").mkdir(exist_ok=True)
    with open(ROOT / "data/vendas_porsche_tratada.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(saida[0]))
        w.writeheader()
        w.writerows(saida)

    # embute os dados no index.html, entre os marcadores /*DADOS*/ e /*FIM*/
    html = ROOT / "index.html"
    if html.exists():
        texto = html.read_text(encoding="utf-8")
        ini, fim = texto.index("/*DADOS*/") + len("/*DADOS*/"), texto.index("/*FIM*/")
        html.write_text(texto[:ini] + json.dumps(saida, ensure_ascii=False) + texto[fim:], encoding="utf-8")

    rec = sum(1 for s in saida if s["status_data"] == "recuperada")
    inv = sum(1 for s in saida if s["status_data"] == "invalida")
    print(f"{len(saida)} vendas | datas recuperadas: {rec} | datas ainda inválidas: {inv}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "base_porsche.xlsx")
