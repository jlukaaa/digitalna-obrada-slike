"""Ocjena podešavanja praćenja na ručno označenim izrezima (bez ponovnog izdvajanja).

Ulaz: folder koji je ručno pregledan i u kojem je ``dijagnoza_orijentacije.py``
snimio ``rucna_orijentacija.csv`` (tačan smjer glave za svaki izrez).

Za svaku varijantu podešavanja ``OpcijePracenja`` ponovo se donose odluke o
smjeru glave iz stanja PRIJE ispravke (``<dan>_2/pcele_prije_ispravke.csv``) i
porede sa tačnim smjerom. Varijanta A = trenutna podešavanja i mora dati istu
grešku kao dijagnoza (provjera da je ocjena ispravna).

Upotreba:
    python scripts/ocjena_pracenja.py "<pregledani folder>" [--korijen "<predobrada>"]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from varoa.pracenje import OpcijePracenja, odredi_smjer

A = OpcijePracenja()
B = replace(A, max_razmak=0.7, max_pomak_duzina=0.6, pomak_tolerancija=0.15,
            max_razlika_ose=30, max_odnos_duzine=1.33)
C = replace(B, max_dt_glasa=0.4, min_poravnanje=0.8)
VARIJANTE = {
    "A trenutno": A,
    "B strože povezivanje": B,
    "C B + glas samo susjedne slike": C,
    "D C + 2 slaganja": replace(C, min_neto_glasova=2),
    "E C bez širenja na susjede": replace(C, sirenje_na_susjede=False),
    "F D bez širenja na susjede": replace(C, min_neto_glasova=2, sirenje_na_susjede=False),
    "G samo šablon (bez kretanja)": replace(A, min_pomak_duzina=1e9, sirenje_na_susjede=False),
}


def razlika_ugla(a, b):
    d = np.abs((np.asarray(a) - np.asarray(b)) % 360)
    return np.minimum(d, 360 - d)


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

    oznake = pd.read_csv(pregledani / "rucna_orijentacija.csv")
    oznake["izrez"] = oznake["slika"].str.split("__", n=1).str[1]

    # po danu: stanje prije ispravke, konačno stanje i tačan ugao za označene izreze
    dani = {}
    for dan, grupa in oznake.groupby("dan"):
        folder = korijen / f"{dan}_2"
        prije = pd.read_csv(folder / "pcele_prije_ispravke.csv")
        konacno = pd.read_csv(folder / "pcele.csv").set_index("izrez")["ugao_stepeni"]
        g = grupa.set_index("izrez")
        tacno = (konacno.loc[g.index] + 180 * g["naopako"].astype(int)) % 360
        dani[dan] = (prije, tacno)

    rezultati = []
    for ime, o in VARIJANTE.items():
        greske, izvori = [], []
        for prije, tacno in dani.values():
            r = odredi_smjer(prije, o)
            ugao = (prije["ugao_stepeni"].to_numpy() + 180 * r["okreni"]) % 360
            red = prije.reset_index(drop=True)
            idx = red.index[red["izrez"].isin(tacno.index)]
            pogresno = razlika_ugla(ugao[idx], tacno.loc[red.loc[idx, "izrez"]].to_numpy()) > 90
            greske.extend(pogresno)
            izvori.extend(r["izvor_smjera"][idx])
        g, iz = np.array(greske), np.array(izvori)
        kret = iz == "kretanje"
        rezultati.append({
            "varijanta": ime,
            "greska_%": round(100 * g.mean(), 1),
            "kretanje_udio_%": round(100 * kret.mean(), 1),
            "greska_kretanje_%": round(100 * g[kret].mean(), 1) if kret.any() else float("nan"),
            "greska_ostalo_%": round(100 * g[~kret].mean(), 1) if (~kret).any() else float("nan"),
        })

    t = pd.DataFrame(rezultati)
    pd.set_option("display.width", 160)
    print(f"Označenih izreza: {len(oznake)} | ručno: naopako {oznake['naopako'].mean() * 100:.1f}%\n")
    print(t.to_string(index=False))
    print("\nA mora biti ≈ ručna greška (provjera ocjene). Niže je bolje.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
