"""Download raw source data as returned by the source. Usage: python download.py bps|pihps

Responses are saved untouched under data/raw/<source>/; parsing lives in src/. Re-running skips
files that already exist (delete a file to refresh it).
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parent / "data" / "raw"
HEADERS = {"User-Agent": "Mozilla/5.0"}

BPS_API = "https://webapi.bps.go.id/v1/api/list/model"
BPS_VARS = {1: "Inflasi Bulanan (M-to-M), kabupaten/kota"}

PIHPS_API = "https://www.bi.go.id/hargapangan/WebSite/TabelHarga"
# file suffix -> categories. The second set was added later, so it lives in its own files and the first pull stays valid.
PIHPS_COMMODITIES = {"": "cat_1,cat_2,cat_4,cat_5,cat_7",  # beras, daging ayam, telur ayam, bawang merah, cabai merah
                     "_b": "cat_3,cat_6,cat_8,cat_9,cat_10"}  # daging sapi, bawang putih, cabai rawit, minyak goreng, gula pasir
PIHPS_START = "2017-07-01"  # city-level series start around 2017-11


def fetch_json(url, timeout=180, retries=4):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as r:
                return json.load(r)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(10 * (attempt + 1))


def bps_key():
    key = os.environ.get("BPS_API_KEY")
    env = Path(__file__).resolve().parent / ".env"
    if not key and env.exists():
        pairs = dict(l.split("=", 1) for l in env.read_text().splitlines() if "=" in l and not l.startswith("#"))
        key = pairs.get("BPS_API_KEY", "").strip().strip("\"'")
    if not key:
        sys.exit("BPS_API_KEY is not set (environment or .env)")
    return key


def download_bps():
    key, out = bps_key(), RAW / "bps"
    out.mkdir(parents=True, exist_ok=True)
    for var in BPS_VARS:
        years = fetch_json(f"{BPS_API}/th/lang/ind/domain/0000/var/{var}/key/{key}/")["data"][1]
        for y in years:
            path = out / f"var{var}_{y['th']}.json"
            # the current year is always refreshed so new months arrive
            if path.exists() and int(y["th"]) < date.today().year:
                continue
            data = fetch_json(f"{BPS_API}/data/lang/ind/domain/0000/var/{var}/th/{y['th_id']}/key/{key}/")
            path.write_text(json.dumps(data, ensure_ascii=False))
            print("saved", path.name)
    (out / "RETRIEVED").write_text(date.today().isoformat())


def download_pihps(workers=3):
    out = RAW / "pihps"
    out.mkdir(parents=True, exist_ok=True)
    regencies = []
    for prov in fetch_json(f"{PIHPS_API}/GetRefProvince")["data"]:
        for reg in fetch_json(f"{PIHPS_API}/GetRefRegency?price_type_id=1&ref_prov_id={prov['id']}")["data"]:
            regencies.append({"regency_id": reg["id"], "regency": reg["name"].strip(),
                              "province_id": prov["id"], "province": prov["name"]})
    (out / "regencies.json").write_text(json.dumps(regencies, indent=1))

    # Long ranges get slow server-side; one quarter per request keeps each call ~2-3 s.
    quarters = pd.date_range(PIHPS_START, date.today(), freq="QS")
    jobs = [(r, q, sfx, cats) for sfx, cats in PIHPS_COMMODITIES.items() for r in regencies for q in quarters]

    def one(job):
        r, q, sfx, cats = job
        path = out / f"{r['regency_id']}_{q:%Y-%m}{sfx}.json"
        if path.exists() and q + pd.offsets.QuarterEnd() < pd.Timestamp(date.today()):
            return
        end = min(q + pd.offsets.QuarterEnd(), pd.Timestamp(date.today()))
        params = (f"price_type_id=1&comcat_id={cats}&province_id={r['province_id']}"
                  f"&regency_id={r['regency_id']}&market_id=&tipe_laporan=1"
                  f"&start_date={q:%Y-%m-%d}&end_date={end:%Y-%m-%d}")
        path.write_text(json.dumps(fetch_json(f"{PIHPS_API}/GetGridDataDaerah?{params}"), ensure_ascii=False))

    print(f"{len(regencies)} regencies x {len(quarters)} quarters x {len(PIHPS_COMMODITIES)} commodity sets")
    with ThreadPoolExecutor(workers) as ex:
        for i, _ in enumerate(ex.map(one, jobs), 1):
            if i % 100 == 0:
                print(f"{i}/{len(jobs)}", flush=True)
    (out / "RETRIEVED").write_text(date.today().isoformat())


if __name__ == "__main__":
    {"bps": download_bps, "pihps": download_pihps}[sys.argv[1]]()
