#!/usr/bin/env python3
"""Miniatura da 1a pagina de artigos em acesso aberto (licenca CC) -> static/images/pubs/<id>.jpg"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml

try:
    import pymupdf as fitz
except ImportError:
    sys.exit("Instale as dependencias: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
PUBS = ROOT / "data" / "publicacoes" / "auto.yaml"
OUT = ROOT / "static" / "images" / "pubs"
FAIL = ROOT / "scripts" / "thumbs_falhas.json"
MAILTO = os.getenv("OPENALEX_MAILTO", "").strip()
MAX_BYTES = 25 * 1024 * 1024
LARGURA = 360

S = requests.Session()
S.headers["User-Agent"] = f"LabIntegra-site/1.0 (mailto:{MAILTO})"


def candidatos(doi, qualquer):
    r = S.get(f"https://api.unpaywall.org/v2/{doi}", params={"email": MAILTO}, timeout=30)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    d = r.json()
    locs = ([d["best_oa_location"]] if d.get("best_oa_location") else []) + (d.get("oa_locations") or [])
    out = []
    for loc in locs:
        pdf = loc.get("url_for_pdf")
        lic = (loc.get("license") or "").lower()
        if pdf and pdf not in out and (qualquer or lic.startswith("cc") or lic == "public-domain"):
            out.append(pdf)
    return out


def baixar(url):
    r = S.get(url, timeout=60, stream=True, headers={"Accept": "application/pdf"})
    r.raise_for_status()
    data = b""
    for chunk in r.iter_content(65536):
        data += chunk
        if len(data) > MAX_BYTES:
            return None
    return data if data[:5] == b"%PDF-" else None


def miniatura(data, dest):
    doc = fitz.open(stream=data, filetype="pdf")
    page = doc[0]
    z = LARGURA / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
    pix.save(str(dest), jpg_quality=80)
    doc.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="maximo de miniaturas novas (0 = sem limite)")
    ap.add_argument("--refazer", action="store_true")
    ap.add_argument("--qualquer-licenca", action="store_true")
    o = ap.parse_args()
    if not MAILTO:
        sys.exit("Defina OPENALEX_MAILTO (a Unpaywall exige um e-mail).")

    pubs = yaml.safe_load(PUBS.read_text(encoding="utf-8")) or []
    falhas = json.loads(FAIL.read_text(encoding="utf-8")) if FAIL.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    feitas = 0
    for p in pubs:
        pid, doi = p.get("id"), p.get("doi")
        if not (pid and doi and p.get("acesso_aberto")):
            continue
        dest = OUT / f"{pid}.jpg"
        if dest.exists() and not o.refazer:
            continue
        if not o.refazer and time.time() - falhas.get(pid, 0) < 60 * 86400:
            continue
        if o.limit and feitas >= o.limit:
            break
        ok = False
        try:
            for url in candidatos(doi, o.qualquer_licenca):
                data = baixar(url)
                if data:
                    miniatura(data, dest)
                    ok = True
                    break
        except Exception as e:
            print(f"  erro em {doi}: {e}")
        if ok:
            feitas += 1
            falhas.pop(pid, None)
            print(f"OK   {doi}")
        else:
            falhas[pid] = time.time()
            print(f"sem PDF/licenca CC: {doi}")
        time.sleep(0.5)
    FAIL.write_text(json.dumps(falhas, indent=1), encoding="utf-8")
    print(f"Concluido: {feitas} miniaturas novas.")


if __name__ == "__main__":
    main()