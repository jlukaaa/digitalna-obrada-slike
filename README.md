# Detekcija varoe na pčelama

Projekat iz predmeta **Digitalna obrada slike**.

Cilj je automatski prepoznati pčele zaražene grinjom *Varroa destructor* na slikama
iz košnice, kombinacijom klasične obrade slike i neuronske mreže.

## Ideja

Neuronska mreža se trenira na laboratorijskim slikama pčela, a koristi se na slikama
iz fiksnih kamera u košnici, koje izgledaju potpuno drugačije (pozadina, svjetlo,
oštrina, veličina). Glavni zadatak predobrade je da te dvije vrste slika učini
**što sličnijim**, kako bi mreža učila varou, a ne razlike između domena.

```
Slika iz košnice (3 slike/s)
   │
   ▼
[1] Detekcija pčela        model pozadine, segmentacija, filtriranje
   │
   ▼
[2] Praćenje               ista pčela kroz uzastopne slike
   │
   ▼
[3] Normalizacija          glava gore, ista veličina, siva pozadina, boja
   │
   ▼
[4] Klasifikator (CNN)     varoa / nema vidljive varoe
   │
   ▼
[5] Odluka po pčeli        objedinjavanje kroz više slika iste pčele
```


## Struktura repozitorija

| Folder | Sadržaj |
|---|---|
| `src/matlab/` | MATLAB implementacija |
| `src/python/` | Python implementacija (ako bude potrebna) |
| `tests/` | testovi |
| `docs/` | dokumentacija i izvještaj |
| `docs/slike/` | **samo** vlastiti dijagrami i grafici (bez slika iz dataseta) |
| `scripts/hooks/` | git hookovi (zaštita podataka, zaštita grana) |
| `data/` | prazno u repou; lokalno se tu može držati dataset (ignorisano) |
| `results/` | prazno u repou; dozvoljeni su samo `.csv` fajlovi sa metrikama |

## ⚠️ Podaci

Dataset sadrži **zaštićene slike** i **ne nalazi se u ovom repozitoriju**, niti smije
biti dodan, ni preko Git LFS-a, ni kao prilog u issueu ili Pull Requestu.

| Skup | Opis | Namjena |
|---|---|---|
| Laboratorija V1 | ~700 slika, zelena pozadina, pčele sa varoom | trening (pozitivni primjeri) |
| Košnica | fiksne kamere, 3 slike/s, drvena pozadina | trening (negativni) i test |

Detaljan opis: `docs/dataset.md`. Gdje se dataset nabavlja: `data/README.md`.

## Jednokratno podešavanje

```bash
git clone git@github.com:jlukaaa/digitalna-obrada-slike.git
cd digitalna-obrada-slike
git lfs install
git config core.hooksPath scripts/hooks
```

Hookovi blokiraju commit slika i fajlova iz `data/`, kao i direktan push na `main` i `dev`.

## Pokretanje

### Lokalna konfiguracija (jednom)

Putanje do dataseta su različite na svakom računaru, pa se drže u lokalnom fajlu
koji ne ide u git.

1. Kopiraj `src/matlab/config_primjer.m` u `src/matlab/config_lokalno.m`
2. U kopiji promijeni prvu liniju u `function cfg = config_lokalno()`
3. Upiši svoje putanje – dataset i izlazi moraju biti **van repozitorija**

U kodu:
```matlab
cfg = ucitajKonfiguraciju();
slike = dir(fullfile(cfg.putanje.labV1, 'images', 'train', 'V1_*.jpg'));
```

`ucitajKonfiguraciju` javlja grešku ako fajl ili folder sa datasetom ne postoji,
pravi izlazne foldere ako ih nema i upozorava ako je izlaz unutar repoa.

## Kako radimo

Pravila rada (grane, commitovi, Pull Requestovi, tabla): [CONTRIBUTING.md](CONTRIBUTING.md).

Napredak se prati na [Projects tabli](https://github.com/users/jlukaaa/projects) po fazama:

| Faza | Sadržaj |
|---|---|
| v0.1 | Setup i dataset |
| v0.2 | Detekcija i praćenje pčela |
| v0.3 | Normalizacija i označavanje |
| v0.4 | Klasifikator |
| v0.5 | Evaluacija |
| v1.0 | Izvještaj i predaja |
