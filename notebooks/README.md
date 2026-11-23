# notebooks/

Jupyter notebooki za eksperimente.

## ⚠️ Pravila (zaštićeni podaci)

Notebook čuva sve izlaze **unutar `.ipynb` fajla** – i slike pčela koje prikaže.
Zato:

- **nbstripout** briše sve izlaze pri commitu – mora biti uključen
  (`nbstripout --install`, jednom po računaru, vidi README).
- `pre-commit` hook dodatno blokira commit notebooka u kojem je ostala slika.
- U git ide samo **kod**. Rezultati u brojevima idu u `results/*.csv`,
  a figure sa pčelama samo lokalno (`cfg["putanje"]["rezultati"]`).

## Imenovanje

`<broj-issuea>_<kratki-opis>.ipynb`, npr. `16_mjere_domena.ipynb`

Kod koji se ponavlja u više notebooka seli se u paket `src/python/varoa/`.
