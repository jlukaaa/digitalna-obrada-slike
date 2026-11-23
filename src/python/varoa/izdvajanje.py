"""Izdvajanje pojedinačnih pčela iz slika fiksne kamere u košnici.

Za svaku sliku iz ulaznog foldera:

1. pronađe pčele (pčele su tamnije od drvene pozadine)
2. preskoči slike bez pčela (zapiše ih u ``slike.csv``)
3. svaku pčelu izreže, zarotira tako da je tijelo vertikalno i glava GORE,
   i skalira na zadanu dužinu tijela
4. razvrsta izrez u ``pcele/``, ``provjeriti/``, ``mutne/`` ili ``spojene/``

Pozadina se procjenjuje na jedan od dva načina:

- ``'vremenski'`` – medijan više slika iz istog bloka (fiksna kamera; pčele
  se kreću, pa medijan daje praznu pozadinu)
- ``'tophat'``    – morfološko zatvaranje jedne slike (radi i za 1 sliku)
- ``'auto'``      – ``'vremenski'`` ako ima dovoljno slika, inače ``'tophat'``

Izlaz::

    <izlaz>/pcele/<slika>_pcela01.png   normalizovani izrezi
    <izlaz>/provjeriti/                  nesiguran smjer glave
    <izlaz>/mutne/                       zamućenje od pokreta
    <izlaz>/spojene/                     više pčela u jednoj maski
    <izlaz>/debug/                       pregled detekcija (opciono)
    <izlaz>/pcele.csv                    podaci o svakom izrezu
    <izlaz>/slike.csv                    broj pčela po slici

Prenijeto iz MATLAB prototipa (faza 2); logika i parametri su isti.
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage
from skimage import measure

from . import sablon as sablon_modul
from . import slike

KOLONE_PCELE = [
    "izrez", "kategorija", "izvor", "x_centar", "y_centar", "duzina_px", "sirina_px",
    "ugao_stepeni", "okrenuta_180", "pouzdanost_glave", "ostrina", "skala",
    "solidnost", "povrsina_rel",
]
FOLDERI = {"ok": "pcele", "provjeriti": "provjeriti", "mutna": "mutne", "spojene": "spojene"}


@dataclass
class Opcije:
    """Parametri izdvajanja. Podrazumijevane vrijednosti su podešene za kameru C."""

    # izlaz
    izlazna_velicina: tuple[int, int] = (640, 640)  # (visina, širina) izreza
    udio_duzine: float = 0.80          # dužina tijela / visina izreza
    # kamera
    duzina_pcele: float = 492          # očekivana dužina pčele u px na ORIGINALNOJ slici
    min_duzina: float = 0.7            # prihvaćeno: 0.7x ... 1.6x očekivane dužine
    max_duzina: float = 1.6
    max_odnos_sirine_i_duzine: float = 0.75
    # spojene pčele i dijelovi pčela
    min_solidnost: float = 0.65        # ispod = spojene
    min_povrsina: float = 0.5          # ispod = dio pčele (odbacuje se)
    max_povrsina: float = 2.0          # iznad = spojene
    # detekcija
    prag_tamnjenja: float = 0.35       # koliko je pčela tamnija od pozadine (relativno)
    udio_debljine_noge: float = 0.03   # radijus otvaranja (uklanja noge) kao udio dužine
    radna_skala: float = 0.25          # detekcija radi na smanjenoj slici (brzina)
    udio_isjecka: float = 2.2          # stranica isječka / dužina pčele
    odbaci_na_rubu: bool = True        # pčele koje dodiruju rub slike su djelimične
    pozadina: str = "auto"             # 'auto' | 'vremenski' | 'tophat'
    velicina_bloka: int = 600          # slika po bloku za vremensku pozadinu
    slika_za_medijan: int = 25
    min_slika_za_vremenski: int = 15
    korak: int = 1                     # obradi svaku k-tu sliku
    # kvalitet
    min_ostrina: float = 600           # Tenengrad na tijelu; ispod -> mutne/
    sacuvaj_mutne: bool = True
    min_pouzdanost_glave: float = 0.2  # prag kad se smjer određuje po prugama
    sablon_glave: str | Path | None = None   # folder sa pčelama glavom gore ili .npy
    min_pouzdanost_sablona: float = 0.15
    # debug
    sacuvaj_debug: bool = True
    debug_i_prazne: bool = False
    _sablon: np.ndarray | None = field(default=None, repr=False)


# =====================================================================
def izdvoji_pcele(ulaz: str | Path, izlaz: str | Path, opcije: Opcije | None = None) -> dict:
    """Izdvoji pčele iz svih slika u folderu ``ulaz`` u folder ``izlaz``."""
    o = opcije or Opcije()
    ulaz, izlaz = Path(ulaz), Path(izlaz)
    if (izlaz / "pcele.csv").exists():
        raise FileExistsError(
            f'Izlazni folder "{izlaz}" već sadrži rezultate. Isprazni ga ili izaberi '
            f"novi, da se stari i novi izrezi ne pomiješaju."
        )
    o._sablon = sablon_modul.napravi(o.sablon_glave) if o.sablon_glave else None

    fajlovi = slike.listaj(ulaz)
    n = len(fajlovi)
    if n == 0:
        raise FileNotFoundError(f'U folderu "{ulaz}" nema slika.')

    for ime in list(FOLDERI.values()) + (["debug"] if o.sacuvaj_debug else []):
        (izlaz / ime).mkdir(parents=True, exist_ok=True)

    nacin = o.pozadina
    if nacin == "auto":
        nacin = "vremenski" if n >= o.min_slika_za_vremenski else "tophat"
    print(f"Slika: {n} | model pozadine: {nacin}")

    s = o.radna_skala
    pov_ocekivana = np.pi / 4 * o.duzina_pcele * (0.35 * o.duzina_pcele)
    blok, pozadina_bloka = -1, None
    ukupno = praznih = obradjeno = 0
    t0 = time.time()

    with open(izlaz / "pcele.csv", "w", newline="", encoding="utf-8") as fp, \
         open(izlaz / "slike.csv", "w", newline="", encoding="utf-8") as fs:
        wp = csv.writer(fp)
        wp.writerow(KOLONE_PCELE)
        ws = csv.writer(fs)
        ws.writerow(["slika", "broj_pcela", "odbaceno", "status"])

        for i in range(0, n, o.korak):
            obradjeno += 1
            put = fajlovi[i]
            try:
                slika = slike.ucitaj(put)
            except OSError:
                ws.writerow([put.name, 0, 0, "greska_citanja"])
                continue
            mala = cv2.resize(slika, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            g = slike.siva(mala)

            # ---- model pozadine ----
            if nacin == "vremenski":
                b = i // o.velicina_bloka
                if b != blok:
                    blok = b
                    pozadina_bloka = _vremenska_pozadina(fajlovi, b, o, g.shape)
                pozadina = pozadina_bloka
            else:
                pozadina = _tophat_pozadina(g, max(3, round(o.duzina_pcele * 0.35 * s)))

            # ---- maska: relativno potamnjenje (otporno na sjene i trake svjetla) ----
            maska = (pozadina - g) / np.maximum(pozadina, 1) > o.prag_tamnjenja
            r_noge = max(1, round(o.duzina_pcele * o.udio_debljine_noge * s))
            m8 = maska.astype(np.uint8)
            m8 = cv2.morphologyEx(m8, cv2.MORPH_OPEN, _disk(r_noge))   # noge, antene
            m8 = cv2.morphologyEx(m8, cv2.MORPH_CLOSE, _disk(r_noge))
            maska = ndimage.binary_fill_holes(m8 > 0)
            min_px = max(1, round((o.duzina_pcele * s) ** 2 * 0.03))
            oznake = measure.label(maska, connectivity=2)
            oznake = _ukloni_male(oznake, min_px)

            if oznake.max() == 0:
                ws.writerow([put.name, 0, 0, "prazna"])
                praznih += 1
                if o.sacuvaj_debug and o.debug_i_prazne:
                    _sacuvaj_debug(izlaz / "debug", put, mala, oznake, [])
                continue

            h_r, w_r = g.shape
            prihvaceni, odbaceno, brojac = [], 0, 0
            for p in measure.regionprops(oznake):
                duzina = p.axis_major_length / s
                sirina = p.axis_minor_length / s
                if (duzina < o.min_duzina * o.duzina_pcele or duzina > o.max_duzina * o.duzina_pcele
                        or sirina / max(duzina, 1e-9) > o.max_odnos_sirine_i_duzine):
                    odbaceno += 1
                    continue
                r0, c0, r1, c1 = p.bbox
                if o.odbaci_na_rubu and (r0 < 1 or c0 < 1 or r1 > h_r - 1 or c1 > w_r - 1):
                    odbaceno += 1
                    continue
                pov_rel = (p.area / s**2) / pov_ocekivana
                if pov_rel < o.min_povrsina:      # dio pčele
                    odbaceno += 1
                    continue

                izrez, info = _normalizuj_pcelu(slika, oznake == p.label, p, s, o)
                if izrez is None:
                    odbaceno += 1
                    continue

                # kategorija: spojene / mutne / nesiguran smjer / ok
                if p.solidity < o.min_solidnost or pov_rel > o.max_povrsina:
                    kat = "spojene"
                elif info["ostrina"] < o.min_ostrina:
                    if not o.sacuvaj_mutne:
                        odbaceno += 1
                        continue
                    kat = "mutna"
                elif info["pouzdanost"] < (o.min_pouzdanost_sablona if o._sablon is not None
                                          else o.min_pouzdanost_glave):
                    kat = "provjeriti"
                else:
                    kat = "ok"

                brojac += 1
                ime = f"{put.stem}_pcela{brojac:02d}.png"
                slike.sacuvaj(izlaz / FOLDERI[kat] / ime, izrez)
                cy, cx = p.centroid
                wp.writerow([
                    ime, kat, put.name, f"{cx / s:.1f}", f"{cy / s:.1f}", f"{duzina:.1f}",
                    f"{sirina:.1f}", f"{info['ugao']:.2f}", info["okrenuta"],
                    f"{info['pouzdanost']:.3f}", f"{info['ostrina']:.2f}", f"{info['skala']:.4f}",
                    f"{p.solidity:.3f}", f"{pov_rel:.2f}",
                ])
                prihvaceni.append(p.label)

            ukupno += brojac
            if brojac == 0:
                praznih += 1
            ws.writerow([put.name, brojac, odbaceno, "ok" if brojac else "prazna"])
            if o.sacuvaj_debug and (brojac or o.debug_i_prazne):
                _sacuvaj_debug(izlaz / "debug", put, mala, oznake, prihvaceni)
            if obradjeno % 50 == 0:
                print(f"  {i + 1} / {n} slika, {ukupno} pčela")

    print(f"Gotovo: {obradjeno} obrađenih slika, {praznih} praznih, {ukupno} pčela izdvojeno. "
          f"({time.time() - t0:.0f} s)")
    return {"broj_slika": obradjeno, "praznih": praznih, "broj_pcela": ukupno,
            "nacin_pozadine": nacin, "izlaz": izlaz}


# =====================================================================
def _normalizuj_pcelu(slika, maska_radna, p, s, o):
    """Izrez oko pčele -> rotacija (tijelo vertikalno) -> glava gore -> skala."""
    # orijentacija iz momenata maske: ugao velike ose od x-ose, suprotno kazaljci
    # (kao MATLAB regionprops 'Orientation')
    m = cv2.moments(maska_radna.astype(np.uint8), binaryImage=True)
    theta = 0.5 * np.arctan2(2 * m["mu11"], m["mu20"] - m["mu02"])  # y prema dolje
    orijentacija = -np.degrees(theta)

    stranica = 2 * round(o.udio_isjecka * p.axis_major_length / s / 2) + 1
    cy, cx = p.centroid
    isjecak = _izrezi_sa_dopunom(slika, (cx / s, cy / s), stranica)
    stranica_r = 2 * round(o.udio_isjecka * p.axis_major_length / 2) + 1
    maska_isj = _izrezi_sa_dopunom(maska_radna.astype(np.uint8), (cx, cy), stranica_r)
    maska_isj = cv2.resize(maska_isj, (stranica, stranica), interpolation=cv2.INTER_NEAREST)

    # rotacija: velika osa -> vertikalno (pozitivan ugao = suprotno kazaljci)
    ugao = 90 - orijentacija
    rot, rot_m = _rotiraj(isjecak, maska_isj, ugao)
    rot_m = _najveca_komponenta(rot_m)
    if not rot_m.any():
        return None, None
    redovi, kolone = np.nonzero(rot_m)
    visina = redovi.max() - redovi.min() + 1
    if kolone.max() - kolone.min() + 1 > visina:    # zaštita
        rot, rot_m = np.rot90(rot).copy(), np.rot90(rot_m).copy()
        ugao += 90
        redovi, kolone = np.nonzero(rot_m)
        visina = redovi.max() - redovi.min() + 1

    # glava gore ili dolje? (pruge na zatku)
    glava_gore, pouzdanost = _smjer_po_prugama(rot, rot_m)
    okrenuta = 0
    if not glava_gore:
        rot, rot_m = np.rot90(rot, 2).copy(), np.rot90(rot_m, 2).copy()
        okrenuta = 1
        ugao += 180
        redovi, kolone = np.nonzero(rot_m)

    # skala: dužina tijela = udio_duzine * visina izlaza
    vis_izl, sir_izl = o.izlazna_velicina
    skala = o.udio_duzine * vis_izl / visina
    rot_s = cv2.resize(rot, None, fx=skala, fy=skala, interpolation=cv2.INTER_CUBIC)
    centar = ((kolone.min() + kolone.max()) / 2 * skala, (redovi.min() + redovi.max()) / 2 * skala)
    izrez = _izrezi_pravougaonik(rot_s, centar, (vis_izl, sir_izl))

    # oštrina: Tenengrad SAMO na tijelu, na izrezu smanjenom na 1/4
    m_s = cv2.resize(rot_m.astype(np.uint8), None, fx=skala, fy=skala,
                     interpolation=cv2.INTER_NEAREST)
    m_izr = _izrezi_pravougaonik(m_s, centar, (vis_izl, sir_izl))
    m_izr = cv2.erode(m_izr, _disk(5))
    g4 = slike.siva(cv2.resize(izrez, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA))
    m4 = cv2.resize(m_izr, (g4.shape[1], g4.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    gx = cv2.Sobel(g4, cv2.CV_64F, 1, 0, ksize=3, borderType=cv2.BORDER_REPLICATE)
    gy = cv2.Sobel(g4, cv2.CV_64F, 0, 1, ksize=3, borderType=cv2.BORDER_REPLICATE)
    e = gx**2 + gy**2
    ostrina = float(e[m4].mean()) if m4.any() else float(e.mean())

    # provjera smjera šablonom (ako je zadan) – pouzdanije od pruga
    if o._sablon is not None:
        naopako, pouzdanost = sablon_modul.provjeri_smjer(izrez, o._sablon)
        if naopako:
            izrez = np.rot90(izrez, 2).copy()
            okrenuta = 1 - okrenuta
            ugao += 180

    return izrez, {"ugao": ugao % 360, "okrenuta": okrenuta, "pouzdanost": pouzdanost,
                   "ostrina": ostrina, "skala": skala}


def _smjer_po_prugama(rot, rot_m):
    """Zadak ima pruge -> profil svjetline duž tijela jako oscilira.
    Polovina sa više "prugaste energije" je zadak, glava je na drugom kraju."""
    g = slike.siva(rot)
    redovi = np.nonzero(rot_m.any(axis=1))[0]
    r1, r2 = redovi[0], redovi[-1]
    h = r2 - r1 + 1
    profil = np.full(h, np.nan)
    for j in range(h):
        kol = np.nonzero(rot_m[r1 + j])[0]
        if kol.size == 0:
            continue
        w = kol.size  # samo srednja trećina širine (bez krila i rubova)
        sredina = kol[max(0, round(w / 3) - 1):max(1, round(2 * w / 3))]
        profil[j] = g[r1 + j, sredina].mean()
    ok = ~np.isnan(profil)
    if not ok.any():
        return True, 0.0
    profil = np.interp(np.arange(h), np.nonzero(ok)[0], profil[ok])

    prozor = max(3, round(h / 6))
    trend = np.convolve(profil, np.ones(prozor) / prozor, mode="same")
    detalj = profil - trend
    rub, pola = round(0.05 * h), round(h / 2)
    e_gore = float(np.sum(detalj[rub:pola] ** 2))
    e_dolje = float(np.sum(detalj[pola:h - rub] ** 2))
    return e_dolje >= e_gore, abs(e_dolje - e_gore) / max(e_dolje + e_gore, 1e-12)


def _tophat_pozadina(g, r):
    """Morfološko zatvaranje diskom radijusa r (uklanja tamne pčele -> pozadina).
    Radi se na 4x manjoj slici (pozadina je glatka), pa je ~250x brže."""
    f = 4 if r >= 12 else 1
    if f == 1:
        return cv2.morphologyEx(g.astype(np.float32), cv2.MORPH_CLOSE, _disk(r)).astype(np.float64)
    mala = cv2.resize(g.astype(np.float32), None, fx=1 / f, fy=1 / f, interpolation=cv2.INTER_AREA)
    mala = cv2.morphologyEx(mala, cv2.MORPH_CLOSE, _disk(max(1, round(r / f))))
    return cv2.resize(mala, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_LINEAR).astype(np.float64)


def _vremenska_pozadina(fajlovi, blok, o, oblik):
    """Medijan do o.slika_za_medijan slika iz bloka (+ susjedni ako ih je malo)."""
    n = len(fajlovi)
    od = blok * o.velicina_bloka
    do = min(n, (blok + 1) * o.velicina_bloka)
    if do - od < o.min_slika_za_vremenski:
        od, do = max(0, od - o.velicina_bloka), min(n, do + o.velicina_bloka)
    idx = np.unique(np.round(np.linspace(od, do - 1, min(o.slika_za_medijan, do - od))).astype(int))
    stek = np.empty((len(idx), *oblik))
    for j, k in enumerate(idx):
        mala = cv2.resize(slike.ucitaj(fajlovi[k]), None, fx=o.radna_skala, fy=o.radna_skala,
                          interpolation=cv2.INTER_AREA)
        stek[j] = slike.siva(mala)[: oblik[0], : oblik[1]]
    return np.median(stek, axis=0)


# ---- pomoćne funkcije --------------------------------------------------
def _disk(r: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def _ukloni_male(oznake: np.ndarray, min_px: int) -> np.ndarray:
    povrsine = np.bincount(oznake.ravel())
    mali = np.nonzero(povrsine < min_px)[0]
    mali = mali[mali > 0]
    if mali.size:
        oznake = oznake.copy()
        oznake[np.isin(oznake, mali)] = 0
        oznake = measure.label(oznake > 0, connectivity=2)
    return oznake


def _izrezi_sa_dopunom(img, centar, stranica):
    """Kvadratni isječak oko centra (x, y); van slike dopunjeno ponavljanjem ruba."""
    pola = (stranica - 1) // 2
    cx, cy = round(centar[0]), round(centar[1])
    dop = stranica
    p = cv2.copyMakeBorder(img, dop, dop, dop, dop, cv2.BORDER_REPLICATE)
    return p[cy - pola + dop: cy + pola + dop + 1, cx - pola + dop: cx + pola + dop + 1].copy()


def _izrezi_pravougaonik(img, centar, velicina):
    hh, ww = velicina
    dop = max(hh, ww)
    p = cv2.copyMakeBorder(img, dop, dop, dop, dop, cv2.BORDER_REPLICATE)
    y0 = round(centar[1] - hh / 2) + dop
    x0 = round(centar[0] - ww / 2) + dop
    return p[y0: y0 + hh, x0: x0 + ww].copy()


def _rotiraj(img, maska, ugao):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D(((w - 1) / 2, (h - 1) / 2), ugao, 1.0)
    rot = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    rot_m = cv2.warpAffine(maska, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
    return rot, rot_m > 0


def _najveca_komponenta(m):
    oznake = measure.label(m, connectivity=2)
    if oznake.max() <= 1:
        return oznake > 0
    povrsine = np.bincount(oznake.ravel())
    povrsine[0] = 0
    return oznake == povrsine.argmax()


def _sacuvaj_debug(folder, put, mala, oznake, prihvaceni):
    """Zeleno = prihvaćena pčela, žuto = odbačen objekat."""
    img = mala.copy()
    for lab in range(1, oznake.max() + 1):
        konture, _ = cv2.findContours((oznake == lab).astype(np.uint8), cv2.RETR_EXTERNAL,
                                      cv2.CHAIN_APPROX_SIMPLE)
        boja = (0, 255, 0) if lab in prihvaceni else (0, 255, 255)
        cv2.drawContours(img, konture, -1, boja, 2)
    slike.sacuvaj(Path(folder) / f"{put.stem}_debug.jpg", img)
