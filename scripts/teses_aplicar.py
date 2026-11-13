#!/usr/bin/env python3
"""Le scripts/teses_candidatas.yaml e acrescenta a data/teses/defendidas.yaml (so itens novos).
Apenas papel=autor e confianca=alta (use --media para incluir media). Nao altera itens ja existentes."""
import argparse, hashlib, re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "scripts" / "teses_candidatas.yaml"
OUT = ROOT / "data" / "teses" / "defendidas.yaml"
HEAD = "# Teses e dissertacoes defendidas. Gerado por scripts/teses_aplicar.py; pode editar.\n# 'ocultar: true' esconde um item do site. Itens existentes nunca sao sobrescritos.\n"


def tipo(c):
    s = " ".join(c.get("tipo") or []).lower()
    if "dissert" in s or "master" in s or "mestr" in s:
        return "dissertacao"
    if "tese" in s or "doctor" in s or "doutor" in s or "phd" in s:
        return "tese"
    return "dissertacao"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--media", action="store_true", help="incluir confianca media")
    a = ap.parse_args()
    if not CAND.exists():
        print("Rode antes: python scripts/teses_ufmg.py --backend oai --anos 15"); return
    cands = yaml.safe_load(CAND.read_text(encoding="utf-8")) or []
    atuais = (yaml.safe_load(OUT.read_text(encoding="utf-8")) if OUT.exists() else None) or []
    chaves = {x.get("uri") or x.get("titulo") for x in atuais}
    novos = 0
    for c in cands:
        if c.get("papel") != "autor" or (c.get("confianca") != "alta" and not a.media):
            continue
        k = c.get("uri") or c.get("titulo")
        if k in chaves:
            continue
        r = re.sub(r"\s+", " ", c.get("resumo") or "").strip()
        if len(r) >= 590:
            r = r[: r.rfind(" ")] + "…"
        atuais.append({"id": hashlib.md5(k.encode()).hexdigest()[:8], "pessoa": c["pessoa"], "tipo": tipo(c),
                       "titulo": c["titulo"], "ano": c.get("ano"), "uri": c.get("uri") or "", "resumo": r,
                       "confianca": c.get("confianca")})
        chaves.add(k)
        novos += 1
        print(f"  + [{c['pessoa']}] {c.get('ano')} {tipo(c)}: {c['titulo'][:80]}")
    atuais.sort(key=lambda x: (x["pessoa"], -(x.get("ano") or 0)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEAD + yaml.safe_dump(atuais, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    print(f"OK: {novos} novo(s); total {len(atuais)} em data/teses/defendidas.yaml")


if __name__ == "__main__":
    main()