# data/

Ovaj folder je u repozitoriju **namjerno prazan**.

Dataset sadrži zaštićene slike i **ne smije** ući u git – ni direktno, ni preko Git LFS-a.
`.gitignore` ignoriše sve u `data/` (osim ovog fajla i `.gitkeep`), a `pre-commit` hook
blokira commit bilo čega odavde.

## Gdje se nabavljaju podaci

| Skup | Izvor | Ko daje pristup |
|---|---|---|
| Laboratorijski (V1) | Roboflow export *"varroa – v1"* | *(upisati vlasnika / kontakt)* |
| Košnica | fiksne kamere, slike `slika_<kamera>_<datum>_<vrijeme>.jpg` | *(upisati vlasnika / kontakt)* |

Podaci se **ne dijele dalje** bez dozvole vlasnika.

## Lokalno postavljanje

Podaci stoje **van repozitorija**, bilo gdje na disku. Preporučena struktura:

```
<bilo gdje>/
├── varoa_dataset/           ← laboratorijski dataset (putanje.lab_v1)
│   ├── data.yaml
│   ├── images/{train,val}/
│   └── labels/{train,val}/
├── kosnica_ulaz/            ← sirove slike iz košnice (putanje.kosnica)
│   ├── 2026-07-28/
│   ├── 2026-08-01/
│   └── ...
├── kosnica_izlaz/           ← izrezi pčela (putanje.predobrada)
├── modeli/                  ← istrenirane mreže (putanje.modeli)
└── rezultati/               ← slike rezultata (putanje.rezultati)
```

Putanje se upisuju u `config_lokalno.yaml` u korijenu repoa (uputstvo u glavnom
README-u, sekcija *Pokretanje*). Kod ih čita sa:

```python
from varoa.konfiguracija import ucitaj_konfiguraciju

cfg = ucitaj_konfiguraciju()
```

Opis samih podataka: [`docs/dataset.md`](../docs/dataset.md).
