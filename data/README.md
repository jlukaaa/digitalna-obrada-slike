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
├── varoa_dataset/           ← laboratorijski dataset (cfg.putanje.labV1)
│   ├── data.yaml
│   ├── images/{train,val}/
│   └── labels/{train,val}/
├── kosnica_ulaz/            ← sirove slike iz košnice (cfg.putanje.kosnica)
│   ├── 2026-07-28/
│   ├── 2026-08-01/
│   └── ...
├── kosnica_izlaz/           ← izrezi pčela (cfg.putanje.predobrada)
├── modeli/                  ← istrenirane mreže (cfg.putanje.modeli)
└── rezultati/               ← slike rezultata (cfg.putanje.rezultati)
```

Putanje se upisuju u `src/matlab/config_lokalno.m` (uputstvo u glavnom README-u,
sekcija *Pokretanje*). Kod ih čita sa:

```matlab
cfg = ucitajKonfiguraciju();
```

Opis samih podataka: [`docs/dataset.md`](../docs/dataset.md).
