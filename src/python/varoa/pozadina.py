"""Maska tijela i siva pozadina (korak 3.4): V1 i košnica dobiju istu pozadinu.

Ulaz su izrezi 224x224 iz ``varoa.geometrija`` (oba izvora: tijelo vertikalno,
centrirano, dužina 80% visine), pa oba izvora polaze od iste elipse očekivanog tijela.
Ono po čemu se tijelo odvaja od pozadine se razlikuje, jer su pozadine različite:

    V1 (zelena pozadina): nije zeleno i (tamnije od pozadine ili jako obojeno)
        -> čišćenje -> konveksni omotač ∩ elipsa
    košnica (drvo): GrabCut u L*a*b* (drvo je smeđe kao pčela, krila su providna,
        svijetle pruge su svijetle kao drvo, pa prag na svjetlini ne radi)
        -> zaglađivanje (otvaranje skida noge i krila, zatvaranje popuni udubljenja)

Oba: komponenta najbliža centru, proširenje 2 px (grinja na rubu tijela ostaje unutra),
pozadina -> siva [128,128,128] sa mekim prelazom (nema oštre ivice).

Maska se snima kao zasebna slika jer je koristi detektor kandidata (varoa se traži
samo na tijelu). Maske idu u ``maske/``, a ne uz slike, da ih skripte koje listaju
slike ne bi pokupile kao slike.
"""

from __future__ import annotations

import argparse
import csv
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage
from skimage import measure

from . import slike

KLASA_VAROA = 0
IZVORI = ("v1", "kosnica")


@dataclass
class Opcije:
    boja_pozadine: tuple[int, int, int] = (128, 128, 128)   # BGR
    udio_duzine: float = 0.80        # tijelo = 80% visine izreza (dogovor iz 3.3)
    poluosa_x: float = 0.25          # poluosa elipse po širini, u odnosu na dužinu tijela
    poluosa_y: float = 0.56          # poluosa elipse po dužini (malo veća od 0.5: rezerva)
    prag_tamnjenja: float = 0.20     # tijelo je bar 20% tamnije od pozadine
    percentil_pozadine: float = 70   # košnica: svjetlina drveta = 70. percentil van elipse
    udio_otvaranja: float = 0.02     # radijus otvaranja/zatvaranja u odnosu na stranicu
    prosiri_px: int = 2              # proširenje maske (grinja na rubu tijela)
    sigma_ruba: float = 1.5          # meki prelaz tijelo -> siva
    # košnica (GrabCut): poluose elipsi (x, y) u odnosu na dužinu tijela:
    # vjerovatno pozadina do (0.30, 0.62), vjerovatno pčela (0.15, 0.47), sigurno pčela (0.06, 0.30)
    gc_poluose: tuple = (0.30, 0.62, 0.15, 0.47, 0.06, 0.30)
    gc_iteracije: int = 5
    gc_zagladi_px: int = 6
    # kontrola kvaliteta: van ovih granica slika ide u provjeriti/
    udio_maske: tuple[float, float] = (0.08, 0.35)
    visina_maske: tuple[float, float] = (0.60, 0.98)   # u odnosu na visinu izreza
    min_solidnost: float = 0.70                        # prije konveksnog omotača
    _kolone: list[str] = field(default_factory=lambda: [
        "slika", "kategorija", "razlog", "udio_maske", "visina_maske", "sirina_maske",
        "solidnost", "L_pozadine_prije", "broj_varoa", "varoa_u_maski"], repr=False)


# =====================================================================
# Maska
# =====================================================================
def maska_tijela(bgr: np.ndarray, izvor: str, opcije: Opcije | None = None) -> tuple[np.ndarray, dict]:
    """Vrati (maska bool HxW, info). ``izvor`` je "v1" ili "kosnica"."""
    if izvor not in IZVORI:
        raise ValueError(f"izvor mora biti jedan od {IZVORI}, a ne {izvor!r}")
    o = opcije or Opcije()
    h, w = bgr.shape[:2]
    duz = o.udio_duzine * h
    elipsa = _elipsa((h, w), w / 2, h / 2, o.poluosa_x * duz, o.poluosa_y * duz)

    g = slike.siva(bgr)
    if izvor == "kosnica":
        return _maska_kosnica(bgr, g, (h, w), duz, o)

    lab = _lab(bgr)
    ne_zeleno = lab[..., 1] > -8
    obojeno = np.hypot(lab[..., 1], lab[..., 2]) > 20
    zeleno_van = ~elipsa & ~ne_zeleno
    svjetlina_poz = float(np.median(g[zeleno_van])) if zeleno_van.any() else float(np.median(g[~elipsa]))
    kandidat = ne_zeleno & ((g < svjetlina_poz * (1 - o.prag_tamnjenja)) | obojeno) & elipsa

    m = _ocisti(kandidat, (h, w), o.udio_otvaranja)
    info = {"L_pozadine_prije": svjetlina_poz, "solidnost": 0.0}
    if not m.any():
        return m, info
    povrsina = int(m.sum())
    m = _konveksno(m) & elipsa
    info["solidnost"] = povrsina / max(int(m.sum()), 1)
    return _prosiri(m, o.prosiri_px), info


def _maska_kosnica(bgr, g, oblik, duz, o: Opcije):
    """Košnica: GrabCut u L*a*b*. Drvo je smeđe kao pčela, krila su providna, a svijetle
    pruge zatka su svijetle kao drvo, pa prag na svjetlini ne radi. GrabCut iz same slike
    nauči boje pčele (sredina) i drveta (rub) i razdvoji ih; elipsa je samo početna pretpostavka."""
    h, w = oblik
    gc = np.full(oblik, cv2.GC_BGD, np.uint8)
    gc[_elipsa(oblik, w / 2, h / 2, o.gc_poluose[0] * duz, o.gc_poluose[1] * duz)] = cv2.GC_PR_BGD
    gc[_elipsa(oblik, w / 2, h / 2, o.gc_poluose[2] * duz, o.gc_poluose[3] * duz)] = cv2.GC_PR_FGD
    gc[_elipsa(oblik, w / 2, h / 2, o.gc_poluose[4] * duz, o.gc_poluose[5] * duz)] = cv2.GC_FGD
    lab8 = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    cv2.grabCut(lab8, gc, None, np.zeros((1, 65)), np.zeros((1, 65)), o.gc_iteracije, cv2.GC_INIT_WITH_MASK)
    fg = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)

    info = {"L_pozadine_prije": float(np.median(g[~fg])) if (~fg).any() else 0.0, "solidnost": 0.0}
    # zaglađivanje: otvaranje skida noge i komadiće krila, zatvaranje popuni udubljenja
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * o.gc_zagladi_px + 1,) * 2)
    m = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, k) > 0
    m = _ocisti(m, oblik, udio=0.01)
    if not m.any():
        return m, info
    m = ndimage.binary_fill_holes(cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, k) > 0)
    info["solidnost"] = int(m.sum()) / max(int(_konveksno(m).sum()), 1)
    return _prosiri(m, o.prosiri_px), info


def _prosiri(m: np.ndarray, px: int) -> np.ndarray:
    if px <= 0:
        return m
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1,) * 2)
    return cv2.dilate(m.astype(np.uint8), k) > 0


def zamijeni_pozadinu(bgr: np.ndarray, maska: np.ndarray, boja=(128, 128, 128),
                      sigma: float = 1.5) -> np.ndarray:
    """Sve van maske -> ``boja``, sa mekim prelazom širine ~``sigma`` px."""
    alfa = maska.astype(np.float32)
    if sigma > 0:
        alfa = cv2.GaussianBlur(alfa, (0, 0), sigma)
    alfa = alfa[..., None]
    pozadina = np.empty_like(bgr, np.float32)
    pozadina[:] = boja
    return np.clip(alfa * bgr + (1 - alfa) * pozadina + 0.5, 0, 255).astype(np.uint8)


def _lab(bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(bgr.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)


def _elipsa(oblik, cx, cy, ax, ay) -> np.ndarray:
    m = np.zeros(oblik[:2], np.uint8)
    cv2.ellipse(m, (round(cx), round(cy)), (max(1, round(ax)), max(1, round(ay))), 0, 0, 360, 1, -1)
    return m > 0


def _ocisti(kandidat: np.ndarray, oblik, udio: float) -> np.ndarray:
    """Otvaranje (noge, antene), zatvaranje, rupe, komponenta najbliža centru."""
    h, w = oblik[:2]
    r = max(1, round(udio * max(h, w)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    m = cv2.morphologyEx(kandidat.astype(np.uint8), cv2.MORPH_OPEN, k)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    m = ndimage.binary_fill_holes(m > 0)
    oznake = measure.label(m, connectivity=2)
    if oznake.max() == 0:
        return m
    najbolja, najbliza = 0, np.inf
    for p in measure.regionprops(oznake):
        if p.area < 0.01 * h * w:
            continue
        y, x = p.centroid
        d = np.hypot(y - h / 2, x - w / 2)
        if d < najbliza:
            najbolja, najbliza = p.label, d
    return oznake == najbolja


def _konveksno(m: np.ndarray) -> np.ndarray:
    tacke = cv2.findNonZero(m.astype(np.uint8))
    omotac = cv2.convexHull(tacke)
    out = np.zeros(m.shape, np.uint8)
    cv2.fillConvexPoly(out, omotac, 1)
    return out > 0


def kontrola(maska: np.ndarray, info: dict, o: Opcije) -> tuple[dict, str]:
    """Mjere maske i razlog za provjeriti/ ('' ako je sve u redu)."""
    h, w = maska.shape
    redovi, kolone = np.nonzero(maska)
    mjere = {
        "udio_maske": float(maska.mean()),
        "visina_maske": (redovi.max() - redovi.min() + 1) / h if redovi.size else 0.0,
        "sirina_maske": (kolone.max() - kolone.min() + 1) / w if kolone.size else 0.0,
        "solidnost": info["solidnost"],
        "L_pozadine_prije": info["L_pozadine_prije"],
    }
    razlozi = []
    if not redovi.size:
        razlozi.append("nema maske")
    else:
        if not o.udio_maske[0] <= mjere["udio_maske"] <= o.udio_maske[1]:
            razlozi.append("udio")
        if not o.visina_maske[0] <= mjere["visina_maske"] <= o.visina_maske[1]:
            razlozi.append("visina")
        if mjere["solidnost"] < o.min_solidnost:
            razlozi.append("solidnost")
    return mjere, "+".join(razlozi)


# =====================================================================
# Folderi
# =====================================================================
def _ulazne_slike(ulaz: Path) -> list[Path]:
    """V1 iz geometrije ima images/ i provjeriti/ (smjer glave više nije bitan) -> obje.
    Inače: sve slike direktno u folderu."""
    if (ulaz / "images").is_dir():
        fajlovi = slike.listaj(ulaz / "images")
        if (ulaz / "provjeriti").is_dir():
            fajlovi += slike.listaj(ulaz / "provjeriti")
        return fajlovi
    return slike.listaj(ulaz)


def _varoe_u_maski(oznaka: Path, maska: np.ndarray) -> tuple[int, int]:
    """(broj grinja, koliko ih ima centar u maski) iz YOLO oznake."""
    if not oznaka.exists():
        return 0, 0
    h, w = maska.shape
    ukupno = unutra = 0
    for red in oznaka.read_text().splitlines():
        d = red.split()
        if len(d) == 5 and int(d[0]) == KLASA_VAROA:
            ukupno += 1
            x = min(w - 1, max(0, round(float(d[1]) * w)))
            y = min(h - 1, max(0, round(float(d[2]) * h)))
            unutra += bool(maska[y, x])
    return ukupno, unutra


def obradi(ulaz: str | Path, izlaz: str | Path, izvor: str, opcije: Opcije | None = None) -> dict:
    """Svi izrezi iz ``ulaz`` -> ``izlaz``:

        <izlaz>/images/      siva pozadina, maska u redu
        <izlaz>/provjeriti/  siva pozadina, ali maska sumnjiva (vidi kolonu razlog)
        <izlaz>/maske/       <ime>.png, 255 = tijelo (za obje grupe)
        <izlaz>/labels/      V1: YOLO oznake, nepromijenjene
        <izlaz>/pozadina.csv
    """
    o = opcije or Opcije()
    ulaz, izlaz = Path(ulaz), Path(izlaz)
    if (izlaz / "pozadina.csv").exists():
        raise FileExistsError(f'"{izlaz}" već sadrži rezultate – isprazni ga ili izaberi novi.')
    fajlovi = _ulazne_slike(ulaz)
    if not fajlovi:
        raise FileNotFoundError(f'Nema slika u "{ulaz}" (ni u images/).')
    for d in ("images", "provjeriti", "maske") + (("labels",) if izvor == "v1" else ()):
        (izlaz / d).mkdir(parents=True, exist_ok=True)
    print(f"{izvor}: {len(fajlovi)} izreza -> siva pozadina")

    brojac = {"ok": 0, "provjeriti": 0}
    varoa_ukupno = varoa_unutra = 0
    with open(izlaz / "pozadina.csv", "w", newline="", encoding="utf-8") as f:
        pisac = csv.writer(f)
        pisac.writerow(o._kolone)
        for put in fajlovi:
            bgr = slike.ucitaj(put)
            maska, info = maska_tijela(bgr, izvor, o)
            mjere, razlog = kontrola(maska, info, o)
            kat = "provjeriti" if razlog else "ok"
            brojac[kat] += 1

            ime = put.stem + ".png"
            slike.sacuvaj(izlaz / ("images" if kat == "ok" else "provjeriti") / ime,
                          zamijeni_pozadinu(bgr, maska, o.boja_pozadine, o.sigma_ruba))
            slike.sacuvaj(izlaz / "maske" / ime, maska.astype(np.uint8) * 255)

            n_var = n_unutra = ""
            if izvor == "v1":
                oznaka = ulaz / "labels" / (put.stem + ".txt")
                if oznaka.exists():
                    shutil.copy2(oznaka, izlaz / "labels" / oznaka.name)
                n_var, n_unutra = _varoe_u_maski(oznaka, maska)
                varoa_ukupno += n_var
                varoa_unutra += n_unutra
            pisac.writerow([ime, kat, razlog] + [round(mjere[k], 4) for k in
                                                  ("udio_maske", "visina_maske", "sirina_maske",
                                                   "solidnost", "L_pozadine_prije")] + [n_var, n_unutra])

    poruka = f"Gotovo: {brojac['ok']} ok, {brojac['provjeriti']} provjeriti"
    if izvor == "v1" and varoa_ukupno:
        poruka += f"; grinja u maski: {varoa_unutra}/{varoa_ukupno} ({100 * varoa_unutra / varoa_ukupno:.1f}%)"
    print(poruka)
    return {**brojac, "varoa_ukupno": varoa_ukupno, "varoa_u_maski": varoa_unutra}


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m varoa.pozadina",
                                description="Maska tijela i siva pozadina za izreze 224x224.")
    p.add_argument("izvor", choices=IZVORI)
    p.add_argument("--ulaz", required=True, help="izlaz iz varoa.geometrija")
    p.add_argument("--izlaz", required=True)
    p.add_argument("--prag", type=float, default=Opcije.prag_tamnjenja,
                   help="koliko tijelo mora biti tamnije od pozadine (default 0.20)")
    a = p.parse_args(argv)
    obradi(a.ulaz, a.izlaz, a.izvor, Opcije(prag_tamnjenja=a.prag))


if __name__ == "__main__":
    main()
