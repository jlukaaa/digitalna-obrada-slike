"""Statistika izlaza ``izdvoji_pcele`` za podešavanje parametara."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def analiza_rezultata(izlaz: str | Path, grafik: bool = True) -> pd.DataFrame:
    """Ispiše broj izreza po kategoriji i raspodjele dužine, oštrine, solidnosti
    i površine. Ako je ``grafik=True``, histogrami se snime u ``<izlaz>/analiza.png``."""
    izlaz = Path(izlaz)
    t = pd.read_csv(izlaz / "pcele.csv")
    n = len(t)
    print(f"\n=== {izlaz / 'pcele.csv'} ===")
    print(f"Ukupno izreza: {n}")
    for kat, broj in t["kategorija"].value_counts().sort_index().items():
        print(f"  {kat:<12} {broj:5d}  ({100 * broj / max(n, 1):.0f}%)")
    if n == 0:
        return t

    def pct(kol, *q):
        return np.nanpercentile(t[kol], q)

    d10, d50, d90 = pct("duzina_px", 10, 50, 90)
    print("\nDužina pčele (px na originalu):")
    print(f"  10% = {d10:.0f}   medijan = {d50:.0f}   90% = {d90:.0f}")
    print(f"  -> prijedlog: duzina_pcele = {d50:.0f}")

    o = pct("ostrina", 10, 25, 50, 75, 90)
    print("\nOštrina:")
    print("  10% = {:.0f}   25% = {:.0f}   medijan = {:.0f}   75% = {:.0f}   90% = {:.0f}".format(*o))
    print("  -> min_ostrina postaviti između najmutnije prihvatljive i najoštrije\n"
          "     neprihvatljive pčele (pogledati izreze oko ovih vrijednosti).")

    s5, s10, s50 = pct("solidnost", 5, 10, 50)
    p50, p90, p95 = pct("povrsina_rel", 50, 90, 95)
    print("\nSolidnost (1 = konveksno, spojene pčele imaju manje):")
    print(f"  5% = {s5:.2f}   10% = {s10:.2f}   medijan = {s50:.2f}")
    print("Površina / očekivana površina jedne pčele:")
    print(f"  medijan = {p50:.2f}   90% = {p90:.2f}   95% = {p95:.2f}")

    if grafik:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ose = plt.subplots(1, 4, figsize=(16, 3.5))
        for osa, (kol, naslov) in zip(ose, [("duzina_px", "dužina pčele [px]"),
                                             ("ostrina", "oštrina"),
                                             ("solidnost", "solidnost"),
                                             ("povrsina_rel", "površina / očekivana")]):
            osa.hist(t[kol].dropna(), bins=30)
            osa.set_title(naslov)
        fig.tight_layout()
        fig.savefig(izlaz / "analiza.png", dpi=100)
        plt.close(fig)
        print(f"\nHistogrami: {izlaz / 'analiza.png'}")
    return t


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        sys.exit("Upotreba: python -m varoa.analiza <izlazni folder>")
    analiza_rezultata(sys.argv[1])
