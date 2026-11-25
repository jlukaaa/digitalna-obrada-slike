import numpy as np
import pandas as pd

from conftest import ime_slike, nacrtaj_pcelu, pozadina, snimi
from varoa import slike
from varoa.izdvajanje import FOLDERI, izdvoji_pcele
from varoa.pracenje import ispravi_smjer_kretanjem, vrijeme_iz_imena

SMJER = 30.0     # pčela gleda i hoda pod 30° (desno-gore)


def _glava(ugao_stepeni):
    u = np.radians(ugao_stepeni)
    return np.column_stack([np.sin(u), -np.cos(u)])


def _sekvenca(tmp_path, opcije):
    """6 slika (3 u sekundi), jedna pčela hoda glavom naprijed."""
    pomak = np.array([np.cos(np.radians(SMJER)), -np.sin(np.radians(SMJER))]) * 80
    for i in range(6):
        img = pozadina(i)
        cx, cy = np.array([450, 800]) + i * pomak
        nacrtaj_pcelu(img, cx, cy, SMJER)
        snimi(tmp_path / "ulaz", ime_slike(i / 3), img)
    izlaz = tmp_path / "izlaz"
    izdvoji_pcele(tmp_path / "ulaz", izlaz, opcije)
    return izlaz, pomak / np.linalg.norm(pomak)


def test_vrijeme_iz_imena():
    assert vrijeme_iz_imena("slika_C_2026-08-01_07-31-38-906.jpg") == 7 * 3600 + 31 * 60 + 38.906
    assert np.isnan(vrijeme_iz_imena("bez_vremena.jpg"))


def test_glava_u_smjeru_kretanja(tmp_path, opcije):
    izlaz, kretanje = _sekvenca(tmp_path, opcije)
    t = ispravi_smjer_kretanjem(izlaz)

    assert t["trag"].nunique() == 1                     # ista pčela kroz svih 6 slika
    iz_kretanja = t[t["smjer_izvor"] == "kretanje"]
    assert len(iz_kretanja) >= 4
    assert (_glava(iz_kretanja["ugao_stepeni"]) @ kretanje > 0).all()


def test_vraca_namjerno_okrenute_izreze(tmp_path, opcije):
    izlaz, _ = _sekvenca(tmp_path, opcije)
    ispravi_smjer_kretanjem(izlaz)                       # sve sada ispravno

    t = pd.read_csv(izlaz / "pcele.csv")
    ispravni = {}
    for i in (1, 3):                                     # dva izreza namjerno naopako
        r = t.iloc[i]
        f = izlaz / FOLDERI[r["kategorija"]] / r["izrez"]
        ispravni[r["izrez"]] = slike.ucitaj(f)
        slike.sacuvaj(f, np.rot90(ispravni[r["izrez"]], 2).copy())
        t.at[i, "ugao_stepeni"] = (r["ugao_stepeni"] + 180) % 360
    t.to_csv(izlaz / "pcele.csv", index=False)

    rezultat = ispravi_smjer_kretanjem(izlaz)
    assert rezultat["ispravljeno"].sum() == 2
    for ime, slika in ispravni.items():
        r = rezultat[rezultat["izrez"] == ime].iloc[0]
        assert np.array_equal(slike.ucitaj(izlaz / FOLDERI[r["kategorija"]] / ime), slika)

    # ponovno pokretanje ništa ne mijenja
    assert ispravi_smjer_kretanjem(izlaz)["ispravljeno"].sum() == 0
