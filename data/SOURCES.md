# Data sources

## `raw/inflasi_v3.csv` — city month-to-month inflation and CPI

| field | value |
|---|---|
| source_name | BPS (Badan Pusat Statistik) — city CPI and month-to-month inflation, 82 cities |
| source_url | https://www.bps.go.id/ (city CPI / inflation tables) |
| retrieval_date | Unknown. Compiled manually by the 2023 Bangkit team; the file was last changed in git on 2023-12-15. Copied unchanged from `CC/inflasi_v3.csv` (SHA-256 `8BC13FBD46D84B354D9346121AC7CDC188939B31759DFF034F0ED51B0B13767C`). |
| geographic_level | city / regency (82) |
| frequency | monthly, 2008-01 to 2023-11 |
| raw_filename | `data/raw/inflasi_v3.csv` |
| columns | `City, Month (Indonesian name), Year, Inflation (m-t-m %), CPI (level)` |

### Processing notes (`src/data.py`)

- `Inflation` is month-to-month headline inflation (checked against CPI ratios). It is the modelling target, so the CPI base-year breaks (2008-06, 2014-01, 2020-01 in this file) never enter the model.
- Placeholder rule 1: `CPI == 0` → city not yet in the BPS sample → `inflation_mtm = NaN`. Affects 16 cities for 2008–2013 (1,152 rows).
- Placeholder rule 2: `Inflation == 0` while CPI changed from the previous month → `NaN`. Affects 6 cities (Pontianak, Banjarmasin, Watampone, Gorontalo, Ternate, Jayapura) for all of 2011 (72 rows). A 0 with flat CPI is kept as a real 0%.
- No imputation. Feature windows containing a missing month are dropped.
- Coverage threshold: ≥ 96 valid months. With BPS API data appended, the 82 legacy cities meet it (minimum 153 months, 2014-01..2026-09). The 68 cities that joined in 2020/2024 do not. See `artifacts/metrics/coverage.csv`.

### Provenance check

The legacy file was compared with the official BPS WebAPI for 2017-01..2023-11: 6,806 overlapping city-months, 99.99% identical (one sign difference: Merauke 2022-05, +0.02 vs -0.02). From 2017 onward the pipeline uses the API values. The legacy file is only used for 2008–2016.

## `raw/bps/var1_<year>.json` — BPS WebAPI, Inflasi Bulanan (M-to-M)

| field | value |
|---|---|
| source_name | BPS WebAPI, variable 1 "Inflasi Bulanan (M-to-M)", domain 0000 |
| source_url | https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/0000/var/1/th/{th_id}/key/{BPS_API_KEY}/ |
| retrieval_date | see `raw/bps/RETRIEVED` (first pull 2026-10-11) |
| geographic_level | 150 kabupaten/kota + INDONESIA (INDONESIA dropped) |
| frequency | monthly, 2017-01 to latest (2026-09 at first pull) |
| raw_filename | `data/raw/bps/var1_2017.json` … `var1_2026.json` (API responses, unmodified) |
| processing_notes | `src/data.py:load_bps`. City = label without the `KOTA ` prefix, which matches the legacy names exactly. Months absent from the API become NaN rows. Of the 150 cities, 82 have history from 2008/2014, 8 start in 2020 and 60 start in 2024. Only cities with ≥ 96 valid months are modelled (82). |

Reproduce: put `BPS_API_KEY=...` in `.env` (git-ignored) and run `python download.py bps`.

## `raw/pihps/<regency_id>_<quarter>.json` — PIHPS daily food prices

| field | value |
|---|---|
| source_name | Bank Indonesia PIHPS Nasional, traditional markets (`price_type_id=1`), daily report (`tipe_laporan=1`) |
| source_url | https://www.bi.go.id/hargapangan/WebSite/TabelHarga/GetGridDataDaerah (the endpoint behind https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalDaerah) |
| retrieval_date | see `raw/pihps/RETRIEVED` (first pull 2026-10-11) |
| geographic_level | regency/city (110 PIHPS regencies) |
| frequency | daily (trading days), 2017-07 to the retrieval date |
| raw_filename | one JSON per regency per quarter, plus `regencies.json` (regency → province) |
| commodities | category averages (level-1 rows): Beras, Daging Ayam, Telur Ayam, Bawang Merah, Cabai Merah |
| processing_notes | `src/pihps.py`. Monthly mean of daily prices, set to NaN when a month has fewer than 10 priced days. Feature = month-on-month % change of that mean. PIHPS's own "Laporan Bulanan" is **not** used because it is the price on the first trading day of the month, not an average. |

City mapping (CPI city → PIHPS regency): names match after removing `Kota`/`Kab.`, and the Kota wins when both exist (Cirebon, Gorontalo, Tasikmalaya). Explicit aliases: DKI JAKARTA → Kota Jakarta Pusat (PIHPS's only DKI series), PURWOKERTO → Kab. Banyumas (Purwokerto is its capital), LUBUKLINGGAU → Kota Lubuk Linggau, PADANGSIDIMPUAN → Kota Padang Sidempuan, PALANGKA RAYA → Kota Palangkaraya, PARE-PARE → Kota Parepare. All 82 modelled cities map.

Reproduce: `python download.py pihps`. It uses 3 parallel requests, one quarter per request (longer ranges get slow server-side), and resumes by skipping files that already exist. A full pull took about 1 hour (4,180 requests, ~100 MB).

## Not used (yet)

JISDOR, BI Rate, BMKG rainfall, BPS rice production, BPS expenditure-group inflation, BI retail sales and World Bank commodity prices. Each new group must go through the ablation in `train.py` and is kept only if it lowers validation MAE.
