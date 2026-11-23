# Dataset

> ⚠️ Dataset sadrži **zaštićene slike** i ne nalazi se u repozitoriju.
> Ovaj dokument opisuje podatke **samo brojevima i riječima** – bez ijedne slike.
> Gdje se podaci nabavljaju i kako se postavljaju lokalno: [`data/README.md`](../data/README.md).

## Pregled

Projekat koristi dva izvora slika koji se jako razlikuju:

| | Laboratorija (V1) | Košnica |
|---|---|---|
| Namjena | pozitivni primjeri (varoa) | negativni primjeri + test |
| Pozadina | jednolična zelena | drvo (tekstura, boja slična pčeli) |
| Pčela po slici | jedna, centrirana | više, bilo gdje u kadru |
| Dužina pčele | ~222 px | ~500–530 px |
| Osvjetljenje | ujednačeno, neutralno | toplo/žuto, sjene, odsjaji |
| Oštrina | blago mutno (kompresija) | zamućenje od pokreta, različito po danu |
| Oznake | okvir oko varoe i oko pčele (YOLO) | nema – označava se ručno |

Glavni zadatak predobrade je da ove dvije vrste slika dovede u **isti prostor**, tako da
se razlikuju samo po pčeli i prisustvu varoe (vidi [Dogovor](#dogovor)).

## Laboratorijski dataset

Izvor: Roboflow export *"varroa – v1"* (22.04.2025.), format **YOLO v5**.

```
varoa_dataset/
├── data.yaml            klase: 0 = varoa, 1 = bee
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/           jedan .txt po slici
    └── val/
```

**Anotacije** – jedna linija po objektu, koordinate normalizovane na [0, 1]:
```
<klasa> <x_centar> <y_centar> <širina> <visina>
0 0.547 0.312 0.193 0.083     ← varoa (~29×25 px)
1 0.500 0.502 1.000 0.740     ← cijela pčela (~150×222 px)
```

| Grupa | Prefiks | Broj slika | Pozadina | Pčele | Koristi se |
|---|---|---|---|---|---|
| V1 | `V1_` | ~700 train + ~700 val | zelena | tamnije | ✅ da |
| V2 | `V2_` | ~3500 | siva | zlatne / svijetle | ❌ rezerva |

- Ukupno u exportu: 5144 slika
- Rezolucija V1: **150×300 px**
- **Augmentacija nije rađena** – sufiks `.rf.<hash>` je samo ime fajla, ne kopija
- **Sve pčele imaju varou** – zdravih pčela u laboratorijskom skupu nema
- Orijentacija: pomiješano (glava gore / glava dolje)
- Test skup u exportu ne postoji

**Zašto ne V2:** zlatne pčele se po boji jako razlikuju od pčela iz košnice. Pošto su svi
negativni primjeri iz košnice (tamne pčele), mreža bi naučila *"zlatna pčela = varoa"*
umjesto same grinje. V2 ostaje rezerva i za eventualni shortcut test.

## Slike iz košnice

Fiksna kamera, **3 slike u sekundi**. Ime fajla sadrži kameru, datum i vrijeme:
```
slika_<kamera>_<YYYY-MM-DD>_<HH-MM-SS-mmm>.jpg
slika_C_2026-08-01_07-31-38-906.jpg
```

Obrađena 4 dana, po ~600 uzastopnih slika (~3,3 min snimka):

| Dan | Kamera | Praznih slika | Izreza pčela | Tragova (pčela) | Oštrina (medijan) |
|---|---|---|---|---|---|
| 2026-07-28 | C | 271 | 487 | 245 | 1040 |
| 2026-08-01 | C | 109 | 964 | 356 | 1415 |
| 2026-08-12 | C | 127 | 907 | 185 | 1125 |
| 2026-08-31 | A ⚠️ | 86 | 923 | 261 | 536 |

- Dužina pčele stabilna na svim danima: **~500–530 px**
- Kamera se ne pomjera → pozadina se dobija medijanom uzastopnih slika
- Dobar (oštar, dobro okrenut) izrez jedne pčele traje kratko, ~2–3 s
- Iz 2400 slika: **~390 različitih pčela** sa bar jednim dobrim izrezom
- ⚠️ Dan 08-31 ima prefiks `slika_A_` (ostali `slika_C_`) – vjerovatno druga kamera;
  znatno mutniji od ostalih

**Problemi:** zamućenje od pokreta, spojene pčele (~10% detekcija), noge i krila,
odsjaji, pčele koje dugo miruju, dijelovi pčela na rubu kadra.

## Dogovor

Potvrđeno 22.11.2026. (oba člana tima):

1. **Pozitivni primjeri:** samo V1 (~1400). V2 rezerva.
2. **Negativni primjeri:** izrezi pčela iz košnice – samo dobri izrezi (oštri, sigurno
   okrenuti), **jedan po pčeli** (tragu), ručno pregledani da nema vidljive varoe.
3. **Zajednički format:** 224×224 px, tijelo 80% visine, glava gore, **siva pozadina**.
4. **Podjela V1:** 70 / 15 / 15, u **blokovima uzastopnih brojeva** (moguće su
   susjedne slike iz istog videa – ne smiju biti u različitim skupovima).
5. **Podjela košnice:** po **danu** – train i val iz jednih dana, test iz drugog dana.
6. **Test skup:** V1 test dio + ručno označene pčele iz košnice sa testnog dana,
   **uključujući pčele sa varoom iz košnice**. Bez njih test mjeri razliku
   laboratorija/košnica, a ne varou.
7. **Omjer klasa u treningu:** ~1 : 1.

## Ručno označavanje (košnica)

Klase za pčele iz košnice:

| Klasa | Značenje |
|---|---|
| `bez_varoe` | varoa nije vidljiva (ne znači da pčela nije zaražena – grinja može biti s donje strane) |
| `varoa` | varoa jasno vidljiva |
| `ne_moze_se_procijeniti` | mutno, okrenuto, djelimično van kadra |

## Pravila za zaštićene podatke

- Slike, izrezi pčela, predikcije i istrenirani modeli **nikad** ne ulaze u repozitorij.
- U issue, PR i komentare se **ne stavljaju** slike pčela.
- U repozitorij smiju samo **brojevi** (`.csv` u `results/`) i vlastiti dijagrami (`docs/slike/`).
- Lokalne putanje se podešavaju u `config_lokalno.yaml` (vidi README).

## Otvorena pitanja

- [ ] Je li dan 2026-08-31 snimljen kamerom A? Ako jeste – test je i na kameri koju model nije vidio.
- [ ] Jesu li V1 slike kadrovi iz videa (skoro iste susjedne slike)? Provjeriti na par blokova.
- [ ] Koliko pčela sa varoom ima u slikama iz košnice?
