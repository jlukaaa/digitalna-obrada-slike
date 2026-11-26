"""Ispravka smjera glave na osnovu kretanja pčela kroz uzastopne slike.

Pčela hoda glavom naprijed. Fiksna kamera snima 3 slike u sekundi, pa se iz
pomaka iste pčele između uzastopnih slika vidi gdje joj je glava.

Postupak (nad izlazom ``izdvoji_pcele``):

1. iz ``pcele.csv`` učita pozicije, uglove i vrijeme (iz imena slike)
2. poveže istu pčelu kroz uzastopne slike (praćenje, "trag")
3. kad se pčela pomjeri duž tijela, smjer kretanja = smjer glave
4. pčela koja miruje dobije smjer od najbliže slike istog traga u kojoj se
   kretala (pčela se ne okrene za 180° u djeliću sekunde)
5. pčela koja je mirovala CIJELO vrijeme: glasanje svih slika traga
   (težina = pouzdanost šablona)
6. pogrešno okrenute izreze zarotira za 180°, a riješene iz ``provjeriti/``
   premjesti u ``pcele/``

``pcele.csv`` se ažurira (ponovno pokretanje je bezbjedno), stanje prije prve
ispravke čuva se u ``pcele_prije_ispravke.csv``, a ``pcele_ispravljeno.csv``
dobija i kolone ``trag``, ``smjer_izvor`` i ``ispravljeno``.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import slike
from .izdvajanje import FOLDERI


@dataclass
class OpcijePracenja:
    # --- povezivanje iste pčele kroz slike ---
    max_razmak: float = 1.5          # s, najveći razmak slika u istom tragu
    max_pomak_duzina: float = 1.0    # najveći pomak po sekundi, u dužinama pčele
    pomak_tolerancija: float = 0.3   # + stalni dio dozvoljenog pomaka (dužine pčele)
    max_razlika_ose: float | None = None    # stepeni; osa tijela se ne smije naglo okrenuti
    max_odnos_duzine: float | None = None   # npr. 1.33: dužina tijela slična (ista pčela)
    # --- glasanje iz kretanja ---
    min_pomak_duzina: float = 0.12   # najmanji pomak koji se računa kao kretanje
    min_poravnanje: float = 0.6      # |cos| ugla između kretanja i tijela
    max_dt_glasa: float | None = None       # s; kretanje samo između bliskih slika
    min_neto_glasova: int = 1        # koliko više glasova "naprijed" nego "nazad"
    sirenje_na_susjede: bool = True  # pčela koja miruje dobija smjer od susjedne slike
    # --- ostalo ---
    fps: float = 3                   # ako vrijeme nije u imenu slike
    min_jacina_traga: float = 0.5    # slaganje slika u tragu za premještanje u pcele/


_VRIJEME = re.compile(r"(\d{2})-(\d{2})-(\d{2})-(\d{3})")


def vrijeme_iz_imena(ime: str) -> float:
    """``slika_C_2026-08-01_07-31-38-906.jpg`` -> sekunde od ponoći (NaN ako nema)."""
    nadjeno = _VRIJEME.findall(ime)
    if not nadjeno:
        return float("nan")
    h, m, s, ms = (int(x) for x in nadjeno[-1])
    return h * 3600 + m * 60 + s + ms / 1000


def odredi_smjer(t: pd.DataFrame, o: OpcijePracenja | None = None) -> dict:
    """Odluka o smjeru glave za svaki red ``pcele.csv`` – bez diranja fajlova.

    Vraća rječnik: ``trag``, ``okreni`` (bool po redu), ``izvor_smjera``
    ('kretanje' / 'susjed' / 'trag' / 'nepoznato'), ``sigurno_iz_traga``,
    ``broj_tragova``. Koristi je ``ispravi_smjer_kretanjem`` i ocjena podešavanja."""
    o = o or OpcijePracenja()
    n = len(t)

    # ---- vrijeme svake detekcije ----
    izvori = sorted(t["izvor"].unique())
    t_izvor = np.array([vrijeme_iz_imena(x) for x in izvori])
    if np.isnan(t_izvor).any():
        t_izvor = np.arange(len(izvori)) / o.fps
    idx_izvor = t["izvor"].map({x: k for k, x in enumerate(izvori)}).to_numpy()
    vrijeme = t_izvor[idx_izvor]

    # vektor glave u koordinatama originalne slike (y prema dolje):
    # izrez je nastao rotacijom za ugao (suprotno kazaljci) -> glava = (sin u, -cos u)
    u = np.radians(t["ugao_stepeni"].to_numpy())
    glava = np.column_stack([np.sin(u), -np.cos(u)])
    pos = t[["x_centar", "y_centar"]].to_numpy(float)
    duz = t["duzina_px"].to_numpy(float)
    u_tragu = (t["kategorija"] != "spojene").to_numpy()
    osa = np.degrees(u) % 180                                # osa tijela bez smjera

    # ---- praćenje: pohlepno povezivanje najbližih detekcija ----
    trag = np.zeros(n, int)
    zadnji: list[int] = []
    for f in np.argsort(t_izvor):
        ovdje = np.nonzero((idx_izvor == f) & u_tragu)[0]
        if ovdje.size == 0:
            continue
        kandidati = []
        for k, zi in enumerate(zadnji):
            dt = t_izvor[f] - vrijeme[zi]
            if dt <= 0 or dt > o.max_razmak:
                continue
            for d in ovdje:
                rast = np.linalg.norm(pos[d] - pos[zi])
                if rast > (o.pomak_tolerancija + o.max_pomak_duzina * dt) * max(duz[d], duz[zi]):
                    continue
                if o.max_odnos_duzine and max(duz[d], duz[zi]) / max(min(duz[d], duz[zi]), 1) > o.max_odnos_duzine:
                    continue
                if o.max_razlika_ose is not None and _razlika_ose(osa[d], osa[zi]) > o.max_razlika_ose:
                    continue
                kandidati.append((rast, d, k + 1))
        for _, d, k in sorted(kandidati):
            if trag[d] == 0 and not (trag[ovdje] == k).any():
                trag[d] = k
                zadnji[k - 1] = d
        for d in ovdje:
            if trag[d] == 0:
                zadnji.append(d)
                trag[d] = len(zadnji)
    broj_tragova = len(zadnji)

    # ---- glasovi iz kretanja ----
    glas = np.zeros(n)
    for k in range(1, broj_tragova + 1):
        clanovi = np.nonzero(trag == k)[0]
        clanovi = clanovi[np.argsort(vrijeme[clanovi])]
        for a, b in zip(clanovi[:-1], clanovi[1:]):
            if o.max_dt_glasa is not None and vrijeme[b] - vrijeme[a] > o.max_dt_glasa:
                continue
            pomak = pos[b] - pos[a]
            d = np.linalg.norm(pomak)
            if d < o.min_pomak_duzina * (duz[a] + duz[b]) / 2:
                continue
            smjer = pomak / d
            for x in (a, b):
                c = smjer @ glava[x]
                if abs(c) >= o.min_poravnanje:
                    glas[x] += np.sign(c)

    # ---- odluka po detekciji ----
    okreni = np.zeros(n, bool)
    izvor_smjera = np.array(["nepoznato"] * n, dtype=object)
    ispravna_glava = np.full((n, 2), np.nan)
    for d in np.nonzero(np.abs(glas) >= o.min_neto_glasova)[0]:
        okreni[d] = glas[d] < 0
        izvor_smjera[d] = "kretanje"
        ispravna_glava[d] = glava[d] * (-1 if okreni[d] else 1)

    # pčele koje miruju: smjer od najbliže slike istog traga u kojoj se kretala
    for d in np.nonzero((izvor_smjera == "nepoznato") & (trag > 0) & o.sirenje_na_susjede)[0]:
        ostali = np.nonzero((trag == trag[d]) & ~np.isnan(ispravna_glava[:, 0]))[0]
        if ostali.size == 0:
            continue
        ref = ispravna_glava[ostali[np.argmin(np.abs(vrijeme[ostali] - vrijeme[d]))]]
        c = ref @ glava[d]
        if abs(c) >= o.min_poravnanje:
            okreni[d] = c < 0
            izvor_smjera[d] = "susjed"

    # pčele koje su mirovale CIJELO vrijeme: glasanje cijelog traga
    pouzdanost = t["pouzdanost_glave"].to_numpy(float)
    sigurno_iz_traga = np.zeros(n, bool)
    for k in range(1, broj_tragova + 1):
        clanovi = np.nonzero((trag == k) & (izvor_smjera == "nepoznato"))[0]
        if clanovi.size < 2 or ((trag == k) & (izvor_smjera != "nepoznato")).any():
            continue
        ref = glava[clanovi[np.argmax(pouzdanost[clanovi])]]
        zbir = ukupno = 0.0
        for d in clanovi:
            c = ref @ glava[d]
            if abs(c) >= o.min_poravnanje:
                zbir += np.sign(c) * pouzdanost[d]
                ukupno += pouzdanost[d]
        if ukupno == 0:
            continue
        if zbir < 0:
            ref = -ref
        jacina = abs(zbir) / ukupno
        for d in clanovi:
            c = ref @ glava[d]
            if abs(c) >= o.min_poravnanje:
                okreni[d] = c < 0
                izvor_smjera[d] = "trag"
                sigurno_iz_traga[d] = clanovi.size >= 3 and jacina >= o.min_jacina_traga

    return {"trag": trag, "okreni": okreni, "izvor_smjera": izvor_smjera,
            "sigurno_iz_traga": sigurno_iz_traga, "broj_tragova": broj_tragova}


def _razlika_ose(a: float, b: float) -> float:
    """Razlika dvije ose (0..180°) bez obzira na smjer: 0..90°."""
    d = abs(a - b) % 180
    return min(d, 180 - d)


def ispravi_smjer_kretanjem(izlaz: str | Path, opcije: OpcijePracenja | None = None) -> pd.DataFrame:
    """Ispravi smjer glave u izlaznom folderu ``izdvoji_pcele``. Vraća tabelu sa tragovima."""
    o = opcije or OpcijePracenja()
    izlaz = Path(izlaz)
    t = pd.read_csv(izlaz / "pcele.csv")
    n = len(t)
    if n == 0:
        print("Nema izreza.")
        return t
    r = odredi_smjer(t, o)
    trag, okreni, izvor_smjera = r["trag"], r["okreni"], r["izvor_smjera"]
    sigurno_iz_traga, broj_tragova = r["sigurno_iz_traga"], r["broj_tragova"]

    # ---- primjena: rotacija fajlova i premještanje iz provjeriti/ ----
    ispravljeno = np.zeros(n, int)
    premjesteno = 0
    for d in range(n):
        kat = t.at[d, "kategorija"]
        staro = izlaz / FOLDERI[kat] / t.at[d, "izrez"]
        if not staro.exists():
            continue
        if okreni[d]:
            slike.sacuvaj(staro, np.rot90(slike.ucitaj(staro), 2).copy())
            ispravljeno[d] = 1
            t.at[d, "ugao_stepeni"] = (t.at[d, "ugao_stepeni"] + 180) % 360
            t.at[d, "okrenuta_180"] = 1 - t.at[d, "okrenuta_180"]
        rijeseno = izvor_smjera[d] in ("kretanje", "susjed") or sigurno_iz_traga[d]
        if kat == "provjeriti" and rijeseno:
            shutil.move(staro, izlaz / "pcele" / t.at[d, "izrez"])
            t.at[d, "kategorija"] = "ok"
            premjesteno += 1

    # ---- CSV i izvještaj ----
    kopija = izlaz / "pcele_prije_ispravke.csv"
    if not kopija.exists():
        shutil.copy(izlaz / "pcele.csv", kopija)
    t.to_csv(izlaz / "pcele.csv", index=False)
    t2 = t.assign(trag=trag, smjer_izvor=izvor_smjera, ispravljeno=ispravljeno)
    t2.to_csv(izlaz / "pcele_ispravljeno.csv", index=False)

    n_kret = int((izvor_smjera == "kretanje").sum())
    n_sus = int((izvor_smjera == "susjed").sum())
    n_trag = int((izvor_smjera == "trag").sum())
    print(f"Tragova (pojedinačnih pčela kroz vrijeme): {broj_tragova}")
    print(f"Smjer iz kretanja: {n_kret} | od susjednih slika: {n_sus} | "
          f"glasanje traga: {n_trag} | nepoznato: {n - n_kret - n_sus - n_trag}")
    print(f"Okrenuto za 180°: {ispravljeno.sum()} | "
          f"premješteno iz provjeriti/ u pcele/: {premjesteno}")
    return t2
