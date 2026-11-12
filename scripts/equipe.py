#!/usr/bin/env python3
"""Cria o perfil de um integrante (PT e EN) e o cadastra na sincronizacao ORCID.
Exemplo: python scripts/equipe.py --orcid 0000-0000-0000-0000 --categoria doutorando"""
import argparse
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CARGOS = {
    "professor": ("Professor(a)", "Professor"),
    "pesquisador": ("Pesquisador(a)", "Researcher"),
    "posdoc": ("Pós-doutorando(a)", "Postdoctoral researcher"),
    "doutorando": ("Doutorando(a)", "PhD student"),
    "mestrando": ("Mestrando(a)", "MSc student"),
    "ic": ("Iniciação científica", "Undergraduate researcher"),
    "colaborador": ("Colaborador(a)", "Collaborator"),
    "egresso": ("Egresso(a)", "Alumni"),
}


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def orcid_person(orcid):
    try:
        r = requests.get(f"https://pub.orcid.org/v3.0/{orcid}/person",
                         headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Aviso: nao foi possivel ler o ORCID:", e)
        return {}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--orcid", default="")
    a.add_argument("--id", default="")
    a.add_argument("--nome", default="")
    a.add_argument("--categoria", required=True, choices=list(CARGOS))
    a.add_argument("--cargo", default="")
    a.add_argument("--cargo-en", default="")
    a.add_argument("--bio", default="")
    a.add_argument("--bio-en", default="")
    a.add_argument("--lattes", default="")
    a.add_argument("--scholar", default="")
    a.add_argument("--linkedin", default="")
    a.add_argument("--email", default="")
    a.add_argument("--areas", default="", help="separadas por ;")
    a.add_argument("--foto", default="", help="caminho de uma imagem local")
    a.add_argument("--force", action="store_true")
    o = a.parse_args()

    p = orcid_person(o.orcid) if o.orcid else {}
    nm = p.get("name") or {}
    nome = o.nome or " ".join(filter(None, [(nm.get("given-names") or {}).get("value"),
                                            (nm.get("family-name") or {}).get("value")]))
    if not nome:
        sys.exit("Informe --nome (ou um --orcid com nome publico).")
    pid = o.id or slug(nome)
    orc_bio = (p.get("biography") or {}).get("content", "") or ""
    kws = [k.get("content") for k in ((p.get("keywords") or {}).get("keyword") or []) if k.get("content")]
    urls = [(u.get("url") or {}).get("value", "") for u in ((p.get("researcher-urls") or {}).get("researcher-url") or [])]
    lattes, scholar, linkedin = o.lattes, o.scholar, o.linkedin
    for u in urls:
        if "lattes.cnpq.br" in u and not lattes:
            lattes = u
        elif "scholar.google" in u and not scholar:
            scholar = u
        elif "linkedin.com" in u and not linkedin:
            linkedin = u
    areas = [x.strip() for x in o.areas.split(";") if x.strip()] or kws

    foto = ""
    if o.foto:
        src = Path(o.foto)
        dst_dir = ROOT / "static" / "images" / "equipe"
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst_dir / f"{pid}{src.suffix.lower()}")
        foto = f"images/equipe/{pid}{src.suffix.lower()}"

    def fm(cargo):
        d = {"title": nome, "id": pid, "categoria": o.categoria, "cargo": cargo, "ativo": True,
             "orcid": o.orcid, "lattes": lattes, "scholar": scholar, "linkedin": linkedin,
             "email": o.email, "foto": foto, "areas": areas}
        return {k: v for k, v in d.items() if v not in ("", None, [])}

    pasta = ROOT / "content" / "equipe" / pid
    pasta.mkdir(parents=True, exist_ok=True)
    versoes = {
        "index.md": (fm(o.cargo or CARGOS[o.categoria][0]), o.bio or orc_bio),
        "index.en.md": (fm(o.cargo_en or CARGOS[o.categoria][1]), o.bio_en or orc_bio or o.bio),
    }
    for nome_arq, (front, corpo) in versoes.items():
        arq = pasta / nome_arq
        if arq.exists() and not o.force:
            sys.exit(f"{arq} ja existe. Use --force para sobrescrever.")
        txt = "---\n" + yaml.safe_dump(front, allow_unicode=True, sort_keys=False) + "---\n\n" + corpo + "\n"
        arq.write_text(txt, encoding="utf-8", newline="\n")

    if o.orcid:
        reg = ROOT / "scripts" / "orcids.yaml"
        atual = reg.read_text(encoding="utf-8")
        if o.orcid not in atual:
            bloco = yaml.safe_dump([{"id": pid, "nome": nome, "orcid": o.orcid}], allow_unicode=True, sort_keys=False)
            reg.write_text(atual.rstrip("\n") + "\n" + bloco, encoding="utf-8", newline="\n")
            print("Cadastrado em scripts/orcids.yaml")
    print(f"OK: perfil criado em content/equipe/{pid}/")
    if o.orcid:
        print("Para trazer as publicacoes dessa pessoa: python scripts/orcid_sync.py")


if __name__ == "__main__":
    main()