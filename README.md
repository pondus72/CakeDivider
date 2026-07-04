# CakeDivider

Parametrisk CadQuery-prosjekt for en 3D-printbar kakedeler. Modellen lager
radiale, taperte skjærekanter for 6, 8, 10 eller 12 kakestykker, med
forsterkningsribber, ergonomiske fingergrep og eksport som både full modell og
2 eller 4 sammenlåsende printdeler.

## Egenskaper

- Diameter: 150-400 mm
- Kakestykker: 6, 8, 10 eller 12
- Taperte skjærekanter med tynn nedre egg og tykkere, sterkere topp
- Forsterkningsribber langs hver radialskjærer
- Ergonomiske ovale fingergrep med grunne riller
- Split i 2 eller 4 deler med tab/socket-låser og justerbar clearance
- Eksport til STEP og STL
- GitHub Actions bygger eksportfiler automatisk ved push

## Kom i gang

Installer Python 3.10 eller nyere, opprett et virtuelt miljø og installer
avhengighetene:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

På Windows PowerShell bruker du:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Bygg modeller

Standardbygg:

```bash
python scripts/build.py
```

Eksempel med 300 mm diameter, 10 stykker og 2 printdeler:

```bash
python scripts/build.py --diameter 300 --slices 10 --split 2 --output-dir dist/300mm-10-slices
```

Eksempel med 360 mm diameter, 12 stykker og 4 printdeler:

```bash
python scripts/build.py --diameter 360 --slices 12 --split 4 --formats stl step
```

Eksportene får navn som:

```text
cake_divider_260mm_8_slices_full.stl
cake_divider_260mm_8_slices_full.step
cake_divider_260mm_8_slices_split4_part01.stl
cake_divider_260mm_8_slices_split4_part01.step
```

## Parametre

| Parameter | Standard | Beskrivelse |
| --- | ---: | --- |
| `--diameter` | `260` | Ytre diameter i mm. Gyldig område er 150-400. |
| `--slices` | `8` | Antall kakestykker: 6, 8, 10 eller 12. |
| `--split` | `4` | Antall sammenlåsende deler: 2 eller 4. |
| `--blade-height` | `18` | Høyde på skjærevegger i mm. |
| `--blade-thickness` | `2.8` | Tykkelse øverst på skjæreveggen i mm. |
| `--cutting-edge` | `0.65` | Tykkelse på den nedre skjære-eggen i mm. |
| `--clearance` | `0.35` | Klarering i tab/socket-låsene i mm. |
| `--formats` | `stl step` | Eksportformat. Bruk `stl`, `step` eller begge. |

## Designnotater

Modellen bygges først som en komplett kakedeler med senternav, ytterring,
radialskjærere og ribber. De printbare delene lages deretter ved å klippe
fullmodellen i sektorformede deler. Hver del får hann-tapper på den ene
splitflaten og tilsvarende hunnspor på den neste, slik at alle delene kan
settes sammen rundt hele sirkelen.

Skjæreveggene er loftet fra en smal nedre egg til en bredere topp. Det gir en
mer printbar og sterkere geometri enn en helt flat, knivtynn vegg.

## 3D-printing

Anbefalte startverdier:

- Materiale: PETG eller mattrygg PLA
- Lagtykkelse: 0,20 mm
- Perimetere: 3-4
- Infill: 20-35 %
- Orientering: skjæreegg ned mot byggeplaten hvis sliceren og første lag gir
  god nok detalj, ellers snu delen og bruk støtte der det trengs
- Etterarbeid: puss lett over skjæreegg og låser, og vask grundig før bruk

Hvis låsene blir for stramme, øk `--clearance` til 0,45-0,55 mm. Hvis de blir
for løse, reduser verdien til 0,20-0,30 mm.

## GitHub Actions

Workflowen i `.github/workflows/build-stl.yml` kjører ved push,
pull request og manuell start. Den bygger fire representative konfigurasjoner
og laster opp STEP/STL-filene som artifacts:

- 180 mm, 6 stykker, split 2
- 260 mm, 8 stykker, split 4
- 300 mm, 10 stykker, split 2
- 360 mm, 12 stykker, split 4

Du kan endre matrisen i workflowen for å bygge andre diametre eller
stykketall automatisk.
