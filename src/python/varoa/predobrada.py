"""Cijeli postupak izdvajanja pčela za jedan ili više foldera (dana).

Za svaki folder sa slikama iz košnice::

    1. prolaz: izdvoji_pcele (ručni šablon) + ispravi_smjer_kretanjem
    2. novi šablon od izreza čiji je smjer poznat iz KRETANJA
    3. prolaz: izdvoji_pcele (novi šablon) + ispravi_smjer_kretanjem  -> <dan>_2/

Konačni rezultat je u ``<korijen_izlaz>/<dan>_2/``.

Pokretanje iz terminala (putanje iz config_lokalno.yaml)::

    python -m varoa.predobrada --sablon "C:\\...\\sablon"
"""

from __future__ import annotations

import argparse
import time
from dataclasses import replace
from pathlib import Path

import pandas as pd

from . import sablon as sablon_modul
from .analiza import analiza_rezultata
from .izdvajanje import Opcije, izdvoji_pcele
from .pracenje import ispravi_smjer_kretanjem


def napravi_sablon_iz_kretanja(izlaz: str | Path, izlaz_npy: str | Path,
                               min_ostrina: float = 0, min_broj: int = 10):
    """Šablon od izreza iz ``pcele/`` kojima je smjer određen kretanjem.

    Vraća šablon, ili ``None`` ako ima manje od ``min_broj`` takvih izreza
    (tada je ručni šablon bolji)."""
    izlaz = Path(izlaz)
    t = pd.read_csv(izlaz / "pcele_ispravljeno.csv")
    izabrani = t[(t["kategorija"] == "ok") & (t["smjer_izvor"] == "kretanje")
                 & (t["ostrina"] >= min_ostrina)]
    fajlovi = [izlaz / "pcele" / f for f in izabrani["izrez"] if (izlaz / "pcele" / f).exists()]
    print(f"Izreza sa smjerom iz kretanja: {len(fajlovi)}")
    if len(fajlovi) < min_broj:
        print(f"Premalo za novi šablon (min {min_broj}) – ostaje ručni šablon.")
        return None
    return sablon_modul.napravi(fajlovi, izlaz_npy)


def obradi_folder(ulaz: str | Path, izlaz: str | Path, opcije: Opcije,
                  drugi_prolaz: bool = True) -> Path:
    """Oba prolaza za jedan folder. Vraća folder sa konačnim rezultatom."""
    ulaz, izlaz = Path(ulaz), Path(izlaz)
    izdvoji_pcele(ulaz, izlaz, opcije)
    ispravi_smjer_kretanjem(izlaz)
    if not drugi_prolaz:
        analiza_rezultata(izlaz)
        return izlaz

    print("\n===== DRUGI PROLAZ =====")
    sablon_npy = izlaz / "sablon_kretanje.npy"
    o2 = opcije
    if napravi_sablon_iz_kretanja(izlaz, sablon_npy, opcije.min_ostrina) is not None:
        o2 = replace(opcije, sablon_glave=sablon_npy)
    izlaz2 = izlaz.with_name(izlaz.name + "_2")
    izdvoji_pcele(ulaz, izlaz2, o2)
    ispravi_smjer_kretanjem(izlaz2)
    analiza_rezultata(izlaz2)
    return izlaz2


def obradi_sve(korijen_ulaz: str | Path, korijen_izlaz: str | Path, opcije: Opcije) -> None:
    """Obradi sve podfoldere (dane) jedan za drugim.

    Folder koji već ima konačni rezultat (``<dan>_2/pcele_ispravljeno.csv``)
    se preskače, pa se obrada može prekinuti i ponovo pokrenuti."""
    korijen_ulaz, korijen_izlaz = Path(korijen_ulaz), Path(korijen_izlaz)
    dani = sorted(p for p in korijen_ulaz.iterdir() if p.is_dir())
    if not dani:
        raise FileNotFoundError(f'U "{korijen_ulaz}" nema podfoldera.')
    korijen_izlaz.mkdir(parents=True, exist_ok=True)

    t_ukupno = time.time()
    for j, dan in enumerate(dani, start=1):
        izlaz1 = korijen_izlaz / dan.name
        izlaz2 = korijen_izlaz / (dan.name + "_2")
        print(f"\n########## {dan.name}  ({j} / {len(dani)}) ##########")
        if (izlaz2 / "pcele_ispravljeno.csv").exists():
            print("Već obrađeno, preskačem.")
            continue
        if izlaz1.exists() or izlaz2.exists():
            print(f"⚠️ Postoji nedovršen izlaz za {dan.name} – obriši foldere\n"
                  f"   {izlaz1}\n   {izlaz2}\n   i pokreni ponovo. Preskačem.")
            continue
        t0 = time.time()
        obradi_folder(dan, izlaz1, opcije)
        print(f"{dan.name} gotov za {(time.time() - t0) / 60:.1f} min")
    print(f"\nSVE GOTOVO za {(time.time() - t_ukupno) / 60:.1f} min")


# =====================================================================
def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m varoa.predobrada",
        description="Izdvajanje pčela iz slika košnice (svi dani). Putanje iz config_lokalno.yaml.")
    p.add_argument("--sablon", required=True,
                   help="folder sa 20-30 pčela sigurno okrenutih glavom gore")
    p.add_argument("--ulaz", help="korijen sa podfolderima po danima (podrazumijevano: putanje.kosnica)")
    p.add_argument("--izlaz", help="korijen za rezultate (podrazumijevano: putanje.predobrada)")
    p.add_argument("--duzina-pcele", type=float, default=Opcije.duzina_pcele)
    p.add_argument("--min-ostrina", type=float, default=Opcije.min_ostrina)
    p.add_argument("--velicina", type=int, default=Opcije.izlazna_velicina[0],
                   help="stranica kvadratnog izreza u px (npr. 640 ili 224)")
    p.add_argument("--debug", action="store_true", help="snimi debug slike detekcija")
    a = p.parse_args(argv)

    if a.ulaz and a.izlaz:
        ulaz, izlaz = Path(a.ulaz), Path(a.izlaz)
    else:
        from .konfiguracija import ucitaj_konfiguraciju
        cfg = ucitaj_konfiguraciju()
        ulaz = Path(a.ulaz) if a.ulaz else cfg["putanje"]["kosnica"]
        izlaz = Path(a.izlaz) if a.izlaz else cfg["putanje"]["predobrada"]

    opcije = Opcije(sablon_glave=a.sablon, duzina_pcele=a.duzina_pcele,
                    min_ostrina=a.min_ostrina, izlazna_velicina=(a.velicina, a.velicina),
                    sacuvaj_debug=a.debug)
    print(f"Ulaz:  {ulaz}\nIzlaz: {izlaz}")
    obradi_sve(ulaz, izlaz, opcije)


if __name__ == "__main__":
    main()
