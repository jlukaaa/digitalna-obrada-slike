"""Greška orijentacije glave po izvoru smjera – iz ručno ispravljenih izreza.

Poredi svaki izrez iz foldera koji je ručno pregledan (i gdje su naopake pčele
ručno okrenute) sa originalnim izrezom iz izdvajanja:
    isti                  -> program je pogodio smjer
    okrenut za 180°       -> program je pogriješio

Upotreba (u folderu repoa, sa uključenim .venv):
    python scripts/dijagnoza_orijentacije.py "<pregledani folder>" [--korijen "<predobrada>"]

<pregledani folder> = izlaz `varoa.izbor` (imena <dan>__<izrez>.png), poslije ručnog pregleda.
<predobrada>        = folder sa <dan>_2 folderima (podrazumijevano: putanje.predobrada).

Snima <pregledani folder>/rucna_orijentacija.csv (oznake za kasniju provjeru izbora).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from varoa import slike


def razlika(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("pregledani")
    p.add_argument("--korijen")
    a = p.parse_args(argv)

    pregledani = Path(a.pregledani)
    if a.korijen:
        korijen = Path(a.korijen)
    else:
        from varoa.konfiguracija import ucitaj_konfiguraciju
        korijen = ucitaj_konfiguraciju(napravi_izlaze=False)["putanje"]["predobrada"]

    tabele: dict[str, pd.DataFrame] = {}
    redovi = []
    for f in slike.listaj(pregledani):
        if "__" not in f.stem:
            continue
        dan, izrez = f.name.split("__", 1)
        izvor = korijen / f"{dan}_2" / "pcele" / izrez
        if not izvor.exists():
            print(f"  ⚠️ nema originala: {izvor}")
            continue
        if dan not in tabele:
            tabele[dan] = pd.read_csv(korijen / f"{dan}_2" / "pcele_ispravljeno.csv").set_index("izrez")
        info = tabele[dan].loc[izrez]
        moj, original = slike.ucitaj(f), slike.ucitaj(izvor)
        d0, d180 = razlika(moj, original), razlika(moj, np.rot90(original, 2))
        redovi.append({
            "slika": f.name, "dan": dan, "naopako": d180 < d0,
            "smjer_izvor": info["smjer_izvor"], "pouzdanost_glave": info["pouzdanost_glave"],
            "ispravljeno_kretanjem": int(info["ispravljeno"]),
            "sigurnost_poredjenja": round(abs(d0 - d180), 1),
        })

    d = pd.DataFrame(redovi)
    if d.empty:
        print("Nema izreza za poređenje.")
        return 1
    d.to_csv(pregledani / "rucna_orijentacija.csv", index=False)
    nesigurno = (d["sigurnost_poredjenja"] < 2).sum()

    print(f"Upoređeno: {len(d)} izreza | program pogriješio: {d['naopako'].sum()} "
          f"({100 * d['naopako'].mean():.1f}%)")
    if nesigurno:
        print(f"  ⚠️ {nesigurno} poređenja nesigurna (slika izmijenjena i na drugi način?)")

    def tabela(kol, naslov):
        g = d.groupby(kol, observed=True)["naopako"].agg(ukupno="size", naopako="sum")
        g["greska_%"] = (100 * g["naopako"] / g["ukupno"]).round(1)
        print(f"\n== {naslov} ==\n{g.to_string()}")

    tabela("smjer_izvor", "Po izvoru smjera")
    d["pouzdanost"] = pd.cut(d["pouzdanost_glave"], [0, 0.15, 0.3, 0.5, 1.0], include_lowest=True)
    tabela("pouzdanost", "Po pouzdanosti šablona")
    tabela("dan", "Po danu")
    print(f"\nOznake snimljene: {pregledani / 'rucna_orijentacija.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
