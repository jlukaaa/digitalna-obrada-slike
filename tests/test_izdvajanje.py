import pandas as pd

from conftest import DUZINA_PCELE, ime_slike, nacrtaj_pcelu, pozadina, snimi
from varoa import slike
from varoa.izdvajanje import izdvoji_pcele


def test_pronalazi_pcele_i_preskace_prazne(tmp_path, opcije):
    ulaz = tmp_path / "ulaz"
    prazna = pozadina(1)
    dvije = pozadina(2)
    nacrtaj_pcelu(dvije, 500, 400, 90)
    nacrtaj_pcelu(dvije, 1100, 750, 30)
    na_rubu = pozadina(3)
    nacrtaj_pcelu(na_rubu, 800, 600, 120)
    nacrtaj_pcelu(na_rubu, 60, 600, 90)            # presječena rubom -> odbacuje se
    for i, img in enumerate([prazna, dvije, prazna, na_rubu]):
        snimi(ulaz, ime_slike(i), img)

    izdvoji_pcele(ulaz, tmp_path / "izlaz", opcije)

    s = pd.read_csv(tmp_path / "izlaz" / "slike.csv")
    assert list(s["broj_pcela"]) == [0, 2, 0, 1]
    assert list(s["status"]) == ["prazna", "ok", "prazna", "ok"]

    p = pd.read_csv(tmp_path / "izlaz" / "pcele.csv")
    assert len(p) == 3
    assert p["duzina_px"].between(0.85 * DUZINA_PCELE, 1.15 * DUZINA_PCELE).all()
    for _, red in p.iterrows():
        folder = {"ok": "pcele", "provjeriti": "provjeriti", "mutna": "mutne", "spojene": "spojene"}
        izrez = slike.ucitaj(tmp_path / "izlaz" / folder[red["kategorija"]] / red["izrez"])
        assert izrez.shape == (*opcije.izlazna_velicina, 3)


def test_odbija_postojeci_izlaz(tmp_path, opcije):
    import pytest

    ulaz = tmp_path / "ulaz"
    snimi(ulaz, ime_slike(0), pozadina())
    izdvoji_pcele(ulaz, tmp_path / "izlaz", opcije)
    with pytest.raises(FileExistsError):
        izdvoji_pcele(ulaz, tmp_path / "izlaz", opcije)
