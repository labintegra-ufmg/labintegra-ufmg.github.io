#!/usr/bin/env python3
"""Preenche researchgate/scholar/linkedin/lattes VAZIOS dos perfis a partir dos 'researcher-urls' do ORCID.
Manual:  python scripts/links_orcid.py --set arthur-mota researchgate=URL scholar=URL   (sobrescreve)"""
import argparse, re
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
EQ = ROOT / "content" / "equipe"
CAMPOS = {"researchgate": ("researchgate.net",), "scholar": ("scholar.google.",),
          "linkedin": ("linkedin.com",), "lattes": ("lattes.cnpq.br", "cvlattesweb")}
OR = re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]")


def ler(p):
    return p.read_bytes().decode("utf-8")


def gravar(p, t):
    p.write_bytes(t.encode("utf-8"))


def fm_split(t):
    m = re.match(r"^(---[ \t]*\r?\n)(.*?)(\r?\n---)", t, re.S)
    return m


def valor(fm, campo):
    m = re.search(rf"(?m)^{campo}:[ \t]*(.*)$", fm)
    return None if not m else m.group(1).strip().strip("\"'")


def setar(p, campo, url, force=False):
    t = ler(p)
    m = fm_split(t)
    if not m:
        return False
    fm = m.group(2)
    atual = valor(fm, campo)
    if atual and not force:
        return False
    if atual is not None:
        fm2 = re.sub(rf"(?m)^{campo}:.*$", f'{campo}: "{url}"', fm, count=1)
    else:
        fm2 = fm + f'\n{campo}: "{url}"'
    gravar(p, t[:m.start(2)] + fm2 + t[m.end(2):])
    return True


def arquivos(pid):
    return [f for f in (EQ / pid / "index.md", EQ / pid / "index.en.md") if f.exists()]


def do_orcid(orcid):
    try:
        r = requests.get(f"https://pub.orcid.org/v3.0/{orcid}/researcher-urls", headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        return [(x.get("url") or {}).get("value", "") for x in r.json().get("researcher-url", [])]
    except Exception as e:
        print(f"   ! ORCID {orcid}: {e}")
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", nargs="+", metavar="ID campo=URL")
    a = ap.parse_args()
    if a.set:
        pid, pares = a.set[0], a.set[1:]
        for par in pares:
            c, _, u = par.partition("=")
            if c not in CAMPOS or not u:
                print(f"ignorado: {par} (campos: {', '.join(CAMPOS)})"); continue
            for f in arquivos(pid):
                print(("OK" if setar(f, c, u, True) else "sem mudanca"), f.relative_to(ROOT), c)
        return
    for d in sorted(EQ.iterdir()):
        md = d / "index.md"
        if not md.exists():
            continue
        m = fm_split(ler(md))
        fm = m.group(2) if m else ""
        o = OR.search(fm)
        print(f"> {d.name}" + (f" (ORCID {o.group(0)})" if o else " (sem ORCID no perfil)"))
        if o:
            for u in do_orcid(o.group(0)):
                for c, hosts in CAMPOS.items():
                    if u and any(h in u.lower() for h in hosts):
                        for f in arquivos(d.name):
                            if setar(f, c, u):
                                print(f"   + {c}: {u}  ({f.name})")
        fm = fm_split(ler(md)).group(2)
        falta = [c for c in CAMPOS if not valor(fm, c)]
        print("   faltando: " + (", ".join(falta) if falta else "nada"))


if __name__ == "__main__":
    main()