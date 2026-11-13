#!/usr/bin/env python3
"""Busca teses/dissertacoes dos integrantes no repositorio da UFMG (ultimos N anos).
--diagnostico : testa os endpoints e mostra o que cada um devolve (nao grava nada).
Sem opcoes    : grava scripts/teses_candidatas.yaml para revisao manual (nao altera perfis)."""
import argparse, datetime, os, re, sys, time, unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
import requests, yaml

ROOT = Path(__file__).resolve().parent.parent
EQ = ROOT / "content" / "equipe"
SAIDA = ROOT / "scripts" / "teses_candidatas.yaml"
OAI = ["https://repositorio.ufmg.br/oai/request", "https://repositorio.ufmg.br/server/oai/request"]
REST = ["https://repositorio.ufmg.br/server/api"]
MAIL = os.environ.get("OPENALEX_MAILTO", "")
S = requests.Session()
S.headers["User-Agent"] = f"LabIntegra-site (mailto:{MAIL})"
STOP = {"de", "da", "do", "dos", "das", "e"}
TIPOS = ("tese", "dissert", "thesis", "doctoral", "master")
SETKW = ("nuclear", "pctn")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return [t for t in re.split(r"[^a-z0-9]+", s) if t and t not in STOP]


def local(tag):
    return tag.rsplit("}", 1)[-1]


def pessoas():
    res = {}
    for d in sorted(EQ.iterdir()):
        md = d / "index.md"
        if not md.exists():
            continue
        m = re.match(r"^---\s*\n(.*?)\n---", md.read_text(encoding="utf-8"), re.S)
        fm = (yaml.safe_load(m.group(1)) if m else {}) or {}
        res[d.name] = fm.get("title") or d.name
    return res


def casar(pn, rn):
    p, r = norm(pn), set(norm(rn))
    if not p or not r:
        return None
    if set(p) <= r:
        return "alta"
    if len(p) >= 2 and p[0] in r and p[-1] in r:
        return "media"
    return None


def reg(d):
    anos = []
    for x in d.get("date", []):
        m = re.search(r"(19|20)\d{2}", x)
        if m:
            anos.append(int(m.group(0)))
    uri = next((x for x in d.get("identifier", []) if x.startswith("http")), "")
    return {
        "titulo": (d.get("title") or [""])[0],
        "autores": d.get("creator", []),
        "contribuidores": d.get("contributor", []),
        "ano": min(anos) if anos else None,
        "tipo": d.get("type", []),
        "uri": uri,
        "resumo": max(d.get("description") or [""], key=len),
    }


# ---------------- OAI-PMH ----------------
def oai_get(base, params):
    ult = None
    for t in range(3):
        try:
            r = S.get(base, params=params, timeout=60)
            if r.status_code == 200:
                return ET.fromstring(r.content)
            ult = f"HTTP {r.status_code}"
            if r.status_code in (429, 503):
                time.sleep(10 * (t + 1))
                continue
            break
        except (requests.RequestException, ET.ParseError) as e:
            ult = str(e)
            time.sleep(3)
    raise RuntimeError(ult)


def oai_base():
    for b in OAI:
        try:
            oai_get(b, {"verb": "Identify"})
            return b
        except Exception:
            continue
    return None


def token(root):
    return next((e.text for e in root.iter() if local(e.tag) == "resumptionToken" and e.text), None)


def oai_sets(b):
    sets, params = [], {"verb": "ListSets"}
    while True:
        root = oai_get(b, params)
        for s in root.iter():
            if local(s.tag) == "set":
                spec = next((c.text for c in s if local(c.tag) == "setSpec"), "")
                nome = next((c.text for c in s if local(c.tag) == "setName"), "")
                sets.append((spec, nome or ""))
        tok = token(root)
        if not tok:
            return sets
        params = {"verb": "ListSets", "resumptionToken": tok}


def dc(md):
    d = {}
    for e in md.iter():
        k = local(e.tag)
        if k not in ("dc", "oai_dc") and e.text and e.text.strip():
            d.setdefault(k, []).append(e.text.strip())
    return d


def oai_colher(b, desde, spec, maxp):
    params = {"verb": "ListRecords", "metadataPrefix": "oai_dc", "from": desde}
    if spec:
        params["set"] = spec
    n = 0
    while n < maxp:
        root = oai_get(b, params)
        n += 1
        for rec in root.iter():
            if local(rec.tag) != "record":
                continue
            md = next((x for x in rec.iter() if local(x.tag) == "dc"), None)
            if md is not None:
                yield reg(dc(md))
        if n % 10 == 0:
            print(f"  ... {n} paginas", flush=True)
        tok = token(root)
        if not tok:
            return
        params = {"verb": "ListRecords", "resumptionToken": tok}
    print("  ! limite de paginas atingido (use --max-paginas maior ou --set)")


# ---------------- REST (DSpace 7) ----------------
def rest_base():
    for b in REST:
        try:
            r = S.get(b, timeout=30)
            if r.status_code == 200 and "dspaceVersion" in r.text:
                return b
        except Exception:
            pass
    return None


def rest_buscar(b, nome, maxp=3):
    out = []
    for page in range(maxp):
        r = S.get(f"{b}/discover/search/objects", params={"query": f'"{nome}"', "dsoType": "ITEM", "size": 50, "page": page}, timeout=60)
        if r.status_code != 200:
            break
        sr = r.json().get("_embedded", {}).get("searchResult", {})
        for o in sr.get("_embedded", {}).get("objects", []):
            md = o.get("_embedded", {}).get("indexableObject", {}).get("metadata", {})

            def g(k):
                return [x.get("value", "") for x in md.get(k, [])]

            contrib = []
            for k in md:
                if k.startswith("dc.contributor") and k != "dc.contributor.author":
                    contrib += g(k)
            out.append(reg({"title": g("dc.title"), "creator": g("dc.creator") + g("dc.contributor.author"),
                            "contributor": contrib, "date": g("dc.date.issued"), "type": g("dc.type"),
                            "identifier": g("dc.identifier.uri"), "description": g("dc.description.abstract")}))
        if page + 1 >= sr.get("page", {}).get("totalPages", 1):
            break
    return out


# ---------------- principal ----------------
def achar(regs, pess, ano_min):
    out, vistos = [], set()
    for rg in regs:
        if rg["ano"] and rg["ano"] < ano_min:
            continue
        if not any(t in " ".join(rg["tipo"]).lower() for t in TIPOS):
            continue
        for pid, nome in pess.items():
            for papel, nomes in (("autor", rg["autores"]), ("orientacao_ou_banca", rg["contribuidores"])):
                conf = next((c for c in (casar(nome, n) for n in nomes) if c), None)
                if not conf:
                    continue
                k = (pid, papel, rg["uri"] or rg["titulo"])
                if k in vistos:
                    continue
                vistos.add(k)
                out.append({"pessoa": pid, "papel": papel, "confianca": conf, "titulo": rg["titulo"], "ano": rg["ano"],
                            "tipo": rg["tipo"], "autores": rg["autores"], "orientacao_ou_banca": rg["contribuidores"],
                            "uri": rg["uri"], "resumo": rg["resumo"][:600]})
    return sorted(out, key=lambda c: (c["pessoa"], -(c["ano"] or 0)))


def diagnostico():
    ano = datetime.date.today().year - 1
    print("== OAI-PMH ==")
    for b in OAI:
        try:
            r = S.get(b, params={"verb": "Identify"}, timeout=30)
            print(f"{b} -> HTTP {r.status_code} {r.headers.get('content-type', '')}")
            if r.status_code != 200:
                print("   ", r.text[:150].replace("\n", " "))
                continue
            for e in ET.fromstring(r.content).iter():
                if local(e.tag) in ("repositoryName", "granularity", "earliestDatestamp") and e.text:
                    print("   ", local(e.tag), ":", e.text)
            sets = oai_sets(b)
            print(f"    {len(sets)} sets; relevantes (nuclear/PCTN):")
            for s, n in sets:
                if any(k in " ".join(norm(n)) for k in SETKW):
                    print("      ", s, "|", n)
            root = oai_get(b, {"verb": "ListRecords", "metadataPrefix": "oai_dc", "from": f"{ano}-01-01"})
            for rec in root.iter():
                if local(rec.tag) == "record":
                    md = next((x for x in rec.iter() if local(x.tag) == "dc"), None)
                    if md is not None:
                        print("    amostra de registro:", {k: v[:2] for k, v in dc(md).items() if k in ("title", "creator", "contributor", "type", "date")})
                        break
        except Exception as e:
            print(f"   erro: {e}")
    print("\n== REST (DSpace 7) ==")
    for b in REST:
        try:
            r = S.get(b, timeout=30)
            print(f"{b} -> HTTP {r.status_code}")
            if r.status_code == 200:
                print("    versao:", r.json().get("dspaceVersion"))
                rs = rest_buscar(b, "Velasquez", 1)
                print(f"    busca 'Velasquez': {len(rs)} registros")
                for x in rs[:3]:
                    print("      ", x["ano"], x["titulo"][:80], "|", x["autores"][:2], "|", x["contribuidores"][:2])
        except Exception as e:
            print(f"   erro: {e}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnostico", action="store_true")
    ap.add_argument("--anos", type=int, default=5)
    ap.add_argument("--backend", choices=["auto", "rest", "oai"], default="auto")
    ap.add_argument("--set", help="setSpec do OAI (ver --diagnostico)")
    ap.add_argument("--todos", action="store_true", help="OAI: ignorar sets e varrer tudo")
    ap.add_argument("--max-paginas", type=int, default=300)
    a = ap.parse_args()
    if a.diagnostico:
        return diagnostico()
    pess = pessoas()
    ano_min = datetime.date.today().year - a.anos
    desde = f"{ano_min}-01-01"
    regs = []
    rb = rest_base() if a.backend in ("auto", "rest") else None
    if rb:
        print("Backend: REST (DSpace 7)")
        for pid, nome in pess.items():
            print(f"> {nome}", flush=True)
            regs += rest_buscar(rb, nome)
    else:
        ob = oai_base() if a.backend in ("auto", "oai") else None
        if not ob:
            print("Nenhum endpoint respondeu. Rode: python scripts/teses_ufmg.py --diagnostico e cole a saida.")
            return 1
        print(f"Backend: OAI-PMH ({ob}), desde {desde}")
        specs = [a.set] if a.set else []
        if not specs and not a.todos:
            specs = [s for s, n in oai_sets(ob) if any(k in " ".join(norm(n)) for k in SETKW)]
            print("sets usados:", specs or "nenhum encontrado -> varrendo tudo")
        for sp in (specs or [None]):
            print(f"> colhendo set={sp}", flush=True)
            regs += list(oai_colher(ob, desde, sp, a.max_paginas))
    unicos = {(r["uri"] or r["titulo"]): r for r in regs}
    print(f"{len(unicos)} registros lidos")
    cand = achar(list(unicos.values()), pess, ano_min)
    SAIDA.write_text(yaml.safe_dump(cand, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    for c in cand:
        print(f"[{c['pessoa']}] ({c['papel']}, {c['confianca']}) {c['ano']} {c['titulo'][:90]}")
    print(f"\nOK: {len(cand)} candidatas em scripts/teses_candidatas.yaml (revise antes de usar).")
    return 0


if __name__ == "__main__":
    sys.exit(main())