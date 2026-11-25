"""Geometrijsko ujednačavanje: laboratorijske slike (V1) i izrezi iz košnice u isti format.

Zajednički format (dogovor, docs/dataset.md):
    224 x 224 px, tijelo vertikalno, glava GORE, dužina tijela = 80% visine (~179 px)

V1 (150x300, zelena pozadina):
    1. maska tijela (nije zeleno, tamnije ili jako obojeno; unutar YOLO okvira pčele)
    2. osa tijela iz momenata maske -> rotacija na vertikalu
    3. glava gore: pruge na zatku (+ šablon, ako je zadan)
    4. JEDNA afina transformacija original -> 224x224 (slika se interpolira samo jednom)
    5. ista transformacija se primjenjuje na YOLO okvire (grinja "putuje" sa slikom)

Košnica: izrezi iz ``izdvoji_pcele`` već imaju tijelo vertikalno, glavu gore i
dužinu 80% visine, pa se samo smanje na 224x224.

Pozadina se ovdje NE mijenja (zelena / drvo) – to je zadatak 3.4.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage
from skimage import measure

from . import sablon as sablon_modul
from . import slike
from .izdvajanje import _smjer_po_prugama

VELICINA = 224
UDIO_DUZINE = 0.80
KLASA_VAROA, KLASA_PCELA = 0, 1


@dataclass
class Okvir:
    """YOLO okvir u pikselima: klasa, centar (cx, cy), širina, visina."""
    klasa: int
    cx: float
    cy: float
    w: float
    h: float

    def uglovi(self) -> np.ndarray:
        x0, x1 = self.cx - self.w / 2, self.cx + self.w / 2
        y0, y1 = self.cy - self.h / 2, self.cy + self.h / 2
        return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)


# =====================================================================
# YOLO oznake
# =====================================================================
def putanja_oznake(slika: Path) -> Path:
    """``.../images/[train/]x.jpg`` -> ``.../labels/[train/]x.txt``."""
    dijelovi = list(Path(slika).with_suffix(".txt").parts)
    i = len(dijelovi) - 1 - dijelovi[::-1].index("images")
    dijelovi[i] = "labels"
    return Path(*dijelovi)


def ucitaj_oznake(putanja: Path, w: int, h: int) -> list[Okvir]:
    if not putanja.exists():
        return []
    okviri = []
    for red in putanja.read_text().splitlines():
        d = red.split()
        if len(d) == 5:
            k, x, y, ow, oh = int(d[0]), *map(float, d[1:])
            okviri.append(Okvir(k, x * w, y * h, ow * w, oh * h))
    return okviri


def snimi_oznake(putanja: Path, okviri: list[Okvir], w: int, h: int) -> None:
    putanja.write_text("".join(
        f"{o.klasa} {o.cx / w:.6f} {o.cy / h:.6f} {o.w / w:.6f} {o.h / h:.6f}\n" for o in okviri))


# =====================================================================
# Maska V1
# =====================================================================
def maska_v1(bgr: np.ndarray, okvir_pcele: Okvir | None = None, prag: float = 0.20) -> np.ndarray:
    """Tijelo pčele na zelenoj pozadini.

    Piksel je tijelo ako NIJE jasno zelen (a* > -8) i ako je bar ``prag``
    tamniji od pozadine ILI jako obojen (narandžasti segmenti zatka).
    Prozirna krila nisu ni tamna ni obojena. Ograničeno elipsom u okviru pčele."""
    h, w = bgr.shape[:2]
    lab = cv2.cvtColor(bgr.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)
    g = slike.siva(bgr)
    s = max(2, min(h, w) // 40)
    rub = np.concatenate([g[:s].ravel(), g[-s:].ravel(), g[:, :s].ravel(), g[:, -s:].ravel()])
    tamno = g < np.median(rub) * (1 - prag)
    obojeno = np.hypot(lab[..., 1], lab[..., 2]) > 20
    pcela = (lab[..., 1] > -8) & (tamno | obojeno)

    o = okvir_pcele or Okvir(KLASA_PCELA, w / 2, h / 2, w * 0.95, h * 0.9)
    elipsa = np.zeros((h, w), np.uint8)
    cv2.ellipse(elipsa, (round(o.cx), round(o.cy)), (max(1, round(o.w / 2)), max(1, round(o.h / 2))),
                0, 0, 360, 1, -1)
    pcela &= elipsa > 0

    r = max(1, round(0.02 * max(h, w)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    m = cv2.morphologyEx(pcela.astype(np.uint8), cv2.MORPH_OPEN, k)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    m = ndimage.binary_fill_holes(m > 0)
    oznake = measure.label(m, connectivity=2)
    if oznake.max() == 0:
        return m
    povrsine = np.bincount(oznake.ravel())
    povrsine[0] = 0
    return oznake == povrsine.argmax()


# =====================================================================
# Normalizacija jedne V1 slike
# =====================================================================
def normalizuj_v1(bgr: np.ndarray, okviri: list[Okvir], sablon: np.ndarray | None = None,
                  velicina: int = VELICINA, udio_duzine: float = UDIO_DUZINE):
    """Vrati (izrez, novi_okviri, info). ``izrez`` je None ako maska nije nađena."""
    pcela = next((o for o in okviri if o.klasa == KLASA_PCELA), None)
    maska = maska_v1(bgr, pcela)
    if maska.sum() < 50:
        return None, [], {"greska": "nema maske"}

    # osa tijela iz momenata (ugao od x-ose, suprotno kazaljci, kao MATLAB)
    m = cv2.moments(maska.astype(np.uint8), binaryImage=True)
    c = (m["m10"] / m["m00"], m["m01"] / m["m00"])
    orijentacija = -np.degrees(0.5 * np.arctan2(2 * m["mu11"], m["mu20"] - m["mu02"]))
    ugao = 90 - orijentacija

    tacke = np.column_stack(np.nonzero(maska)[::-1]).astype(float)   # (x, y)
    A = _sastavi(c, ugao, tacke, velicina, udio_duzine)
    if A is None:                                   # širina > visina: još 90°
        ugao += 90
        A = _sastavi(c, ugao, tacke, velicina, udio_duzine, prisilno=True)

    izrez, m_izr = _primijeni(bgr, maska, A, velicina)

    # glava gore? pruge na zatku
    glava_gore, pouzdanost = _smjer_po_prugama(izrez, m_izr)
    okrenuta = 0
    if not glava_gore:
        A = _rot180(velicina) @ A
        izrez, m_izr = _primijeni(bgr, maska, A, velicina)
        okrenuta, ugao = 1, ugao + 180

    if sablon is not None:                          # šablon je pouzdaniji od pruga
        naopako, pouzdanost = sablon_modul.provjeri_smjer(izrez, sablon)
        if naopako:
            A = _rot180(velicina) @ A
            izrez, m_izr = _primijeni(bgr, maska, A, velicina)
            okrenuta, ugao = 1 - okrenuta, ugao + 180

    novi = [_transformisi_okvir(o, A, velicina) for o in okviri]
    novi = [o for o in novi if o is not None]
    varoe = [o for o in novi if o.klasa == KLASA_VAROA]
    redovi, kolone = np.nonzero(m_izr)
    info = {
        "ugao_stepeni": ugao % 360, "okrenuta_180": okrenuta, "pouzdanost_glave": pouzdanost,
        "skala": float(np.sqrt(abs(np.linalg.det(A[:2, :2])))),
        "duzina_tijela_px": int(redovi.max() - redovi.min() + 1) if redovi.size else 0,
        "broj_varoa": len(varoe),
        "varoa_px": round(float(np.mean([np.sqrt(o.w * o.h) for o in varoe])), 1) if varoe else 0.0,
        "varoa_na_tijelu": all(m_izr[min(velicina - 1, max(0, round(o.cy))),
                                     min(velicina - 1, max(0, round(o.cx)))] for o in varoe),
    }
    return izrez, novi, info


def _sastavi(c, ugao, tacke, velicina, udio, prisilno=False):
    """3x3 afina matrica: rotacija oko centroida -> skala -> centar tijela u sredinu."""
    R = np.vstack([cv2.getRotationMatrix2D(c, ugao, 1.0), [0, 0, 1]])
    rt = (R[:2, :2] @ tacke.T).T + R[:2, 2]
    x0, y0 = rt.min(0)
    x1, y1 = rt.max(0)
    if (x1 - x0) > (y1 - y0) and not prisilno:
        return None
    s = udio * velicina / max(y1 - y0 + 1, 1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    T = np.array([[s, 0, velicina / 2 - s * cx], [0, s, velicina / 2 - s * cy], [0, 0, 1]])
    return T @ R


def _rot180(velicina):
    c = (velicina - 1) / 2
    return np.array([[-1, 0, 2 * c], [0, -1, 2 * c], [0, 0, 1]], float)


def _primijeni(bgr, maska, A, velicina):
    s = np.sqrt(abs(np.linalg.det(A[:2, :2])))
    izvor = bgr
    if s < 0.8:                                     # protiv aliasinga pri smanjivanju
        sigma = 0.5 * (1 / s - 1)
        izvor = cv2.GaussianBlur(bgr, (0, 0), sigma)
    # van originalne slike: boja pozadine (medijan ruba), a ne razvučeni rubni pikseli
    s_rub = max(2, min(bgr.shape[:2]) // 40)
    rub = np.concatenate([bgr[:s_rub].reshape(-1, 3), bgr[-s_rub:].reshape(-1, 3),
                          bgr[:, :s_rub].reshape(-1, 3), bgr[:, -s_rub:].reshape(-1, 3)])
    boja = tuple(float(x) for x in np.median(rub, axis=0))
    izrez = cv2.warpAffine(izvor, A[:2], (velicina, velicina), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=boja)
    m = cv2.warpAffine(maska.astype(np.uint8), A[:2], (velicina, velicina), flags=cv2.INTER_NEAREST,
                       borderValue=0) > 0
    return izrez, m


def _transformisi_okvir(o: Okvir, A, velicina) -> Okvir | None:
    """Uglovi okvira kroz A -> novi osno poravnati okvir, odsječen na kadar."""
    u = (A[:2, :2] @ o.uglovi().T).T + A[:2, 2]
    x0, y0 = np.clip(u.min(0), 0, velicina)
    x1, y1 = np.clip(u.max(0), 0, velicina)
    if x1 - x0 < 1 or y1 - y0 < 1:
        return None                                  # potpuno van kadra
    return Okvir(o.klasa, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0)


# =====================================================================
# Folderi
# =====================================================================
def obradi_v1(ulaz: str | Path, izlaz: str | Path, sablon: str | Path | None = None,
              velicina: int = VELICINA, min_pouzdanost: float = 0.2) -> None:
    """Sve slike iz ``<ulaz>/images`` (sa oznakama iz ``<ulaz>/labels``) u ``<izlaz>``:

        <izlaz>/images/      normalizovane slike, glava gore (sigurno)
        <izlaz>/provjeriti/  nesiguran smjer glave – pregledati ručno
        <izlaz>/labels/      YOLO oznake u novom kadru (za obje grupe)
        <izlaz>/geometrija_v1.csv
    """
    ulaz, izlaz = Path(ulaz), Path(izlaz)
    if (izlaz / "geometrija_v1.csv").exists():
        raise FileExistsError(f'"{izlaz}" već sadrži rezultate – isprazni ga ili izaberi novi.')
    for d in ("images", "provjeriti", "labels"):
        (izlaz / d).mkdir(parents=True, exist_ok=True)
    t = sablon_modul.napravi(sablon) if sablon else None
    fajlovi = slike.listaj(ulaz / "images")
    print(f"V1 slika: {len(fajlovi)} -> {velicina}x{velicina}")

    kolone = ["slika", "kategorija", "ugao_stepeni", "okrenuta_180", "pouzdanost_glave", "skala",
              "duzina_tijela_px", "broj_varoa", "varoa_px", "varoa_na_tijelu"]
    brojac = {"ok": 0, "provjeriti": 0, "greska": 0}
    with open(izlaz / "geometrija_v1.csv", "w", newline="", encoding="utf-8") as f:
        pisac = csv.writer(f)
        pisac.writerow(kolone)
        for put in fajlovi:
            bgr = slike.ucitaj(put)
            h, w = bgr.shape[:2]
            okviri = ucitaj_oznake(putanja_oznake(put), w, h)
            izrez, novi, info = normalizuj_v1(bgr, okviri, t, velicina)
            if izrez is None:
                brojac["greska"] += 1
                pisac.writerow([put.name, "greska"] + [""] * (len(kolone) - 2))
                continue
            min_p = 0.15 if t is not None else min_pouzdanost
            kat = "ok" if info["pouzdanost_glave"] >= min_p else "provjeriti"
            brojac[kat] += 1
            ime = put.stem + ".png"
            slike.sacuvaj(izlaz / ("images" if kat == "ok" else "provjeriti") / ime, izrez)
            snimi_oznake(izlaz / "labels" / (put.stem + ".txt"), novi, velicina, velicina)
            pisac.writerow([ime, kat] + [round(info[k], 3) if isinstance(info[k], float) else info[k]
                                         for k in kolone[2:]])
    print(f"Gotovo: {brojac['ok']} ok, {brojac['provjeriti']} provjeriti, {brojac['greska']} bez maske")


def obradi_kosnicu(ulaz: str | Path, izlaz: str | Path, velicina: int = VELICINA) -> None:
    """Izrezi iz košnice (već normalizovani u izdvoji_pcele) -> velicina x velicina."""
    ulaz, izlaz = Path(ulaz), Path(izlaz)
    izlaz.mkdir(parents=True, exist_ok=True)
    fajlovi = slike.listaj(ulaz)
    for put in fajlovi:
        img = slike.ucitaj(put)
        if img.shape[0] != img.shape[1]:
            raise ValueError(f"{put.name}: izrez nije kvadratan ({img.shape[1]}x{img.shape[0]})")
        mala = cv2.resize(img, (velicina, velicina), interpolation=cv2.INTER_AREA)
        slike.sacuvaj(izlaz / (put.stem + ".png"), mala)
    print(f"Košnica: {len(fajlovi)} izreza -> {velicina}x{velicina} u {izlaz}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m varoa.geometrija",
                                description="Geometrijsko ujednačavanje u format 224x224.")
    sub = p.add_subparsers(dest="izvor", required=True)
    v = sub.add_parser("v1", help="laboratorijske slike (folder sa images/ i labels/)")
    v.add_argument("--ulaz", required=True)
    v.add_argument("--izlaz", required=True)
    v.add_argument("--sablon", help="folder sa V1 izrezima glavom gore ili .npy")
    v.add_argument("--velicina", type=int, default=VELICINA)
    k = sub.add_parser("kosnica", help="izrezi iz izdvoji_pcele")
    k.add_argument("--ulaz", required=True)
    k.add_argument("--izlaz", required=True)
    k.add_argument("--velicina", type=int, default=VELICINA)
    a = p.parse_args(argv)
    if a.izvor == "v1":
        obradi_v1(a.ulaz, a.izlaz, a.sablon, a.velicina)
    else:
        obradi_kosnicu(a.ulaz, a.izlaz, a.velicina)


if __name__ == "__main__":
    main()
