#!/usr/bin/env python3
"""Lista coautores das publicacoes em auto.yaml (OpenAlex), para escolher quem incluir na equipe."""
import collections
import os
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
pubs = yaml.safe_load((ROOT / "data/publicacoes/auto.yaml").read_text(encoding="utf-8")) or []
membros = yaml.safe_load((ROOT / "scripts/orcids.yaml").read_text(encoding="utf-8")) or []
meus = {m["orcid"] for m in membros}
dois = [p["doi"] for p in pubs if p.get("doi")]
mailto = os.getenv("OPENALEX_MAILTO", "")
key = os.getenv("OPENALEX_API_KEY", "")

cont = collections.Counter()
info = {}
for i in range(0, len(dois), 40):
    lote = dois[i:i + 40]
    params = {"filter": "doi:" + "|".join("https://doi.org/" + d for d in lote),
              "per-page": 100, "select": "authorships"}
    if mailto:
        params["mailto"] = mailto
    if key:
        params["api_key"] = key
    r = requests.get("https://api.openalex.org/works", params=params, timeout=60)
    r.raise_for_status()
    for w in r.json().get("results", []):
        for a in w.get("authorships", []):
            au = a.get("author") or {}
            orc = (au.get("orcid") or "").replace("https://orcid.org/", "")
            if orc in meus or not au.get("display_name"):
                continue
            k = au.get("id")
            cont[k] += 1
            inst = "; ".join(x.get("display_name", "") for x in a.get("institutions", [])[:2])
            info[k] = (au["display_name"], orc, inst)
    time.sleep(0.3)

print(f"{'obras':>5}  {'nome':35} {'ORCID':20} instituicao")
for k, n in cont.most_common():
    nome, orc, inst = info[k]
    print(f"{n:>5}  {nome[:35]:35} {orc or '-':20} {inst}")
print("\nPara criar um perfil: python scripts/equipe.py --orcid <ORCID> --categoria <categoria>")