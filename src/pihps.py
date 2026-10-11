"""PIHPS (Bank Indonesia) daily traditional-market prices -> monthly mean per CPI city."""
import json
import re

import pandas as pd

from src.data import ROOT

PIHPS_DIR = ROOT / "data" / "raw" / "pihps"
COMMODITIES = {"Beras": "rice", "Daging Ayam": "chicken", "Telur Ayam": "egg",
               "Bawang Merah": "shallot", "Cabai Merah": "chili",
               "Daging Sapi": "beef", "Bawang Putih": "garlic", "Cabai Rawit": "bird_chili",
               "Minyak Goreng": "cooking_oil", "Gula Pasir": "sugar"}
MIN_DAYS = 10  # fewer valid trading days in a month -> monthly mean treated as missing
NOWCAST_DAYS = 5  # first trading days of a month averaged for the nowcast; available by ~the 8th

# CPI city -> PIHPS regency where names differ. DKI Jakarta has a single PIHPS series (Jakarta Pusat);
# Purwokerto is the capital of Kab. Banyumas.
ALIASES = {"DKI JAKARTA": "Kota Jakarta Pusat", "LUBUKLINGGAU": "Kota Lubuk Linggau",
           "PADANGSIDIMPUAN": "Kota Padang Sidempuan", "PALANGKA RAYA": "Kota Palangkaraya",
           "PARE-PARE": "Kota Parepare", "PURWOKERTO": "Kab. Banyumas"}


def _norm(name):
    return re.sub(r"\s*\(.*\)", "", name.upper().replace("KAB. ", "").replace("KOTA ", "")).strip()


def city_mapping(cities, pihps_dir=PIHPS_DIR):
    """{cpi_city: regency_id}. Same-named Kota/Kab. pairs resolve to the Kota (all CPI cities here are kota)."""
    regs = json.loads((pihps_dir / "regencies.json").read_text())
    by_name = {r["regency"]: r["regency_id"] for r in regs}
    by_norm = {}
    for r in sorted(regs, key=lambda r: not r["regency"].startswith("Kota")):  # Kota first
        by_norm.setdefault(_norm(r["regency"]), r["regency_id"])
    return {c: by_name[ALIASES[c]] if c in ALIASES else by_norm[c] for c in cities if c in ALIASES or c in by_norm}


def load_monthly(cities, pihps_dir=PIHPS_DIR):
    """Wide table: city, date, <commodity> monthly mean price (Rp/kg), <commodity>_first mean of the
    first NOWCAST_DAYS priced days (NaN until that many days exist)."""
    rows = []
    for city, reg_id in city_mapping(cities, pihps_dir).items():
        for path in pihps_dir.glob(f"{reg_id}_*.json"):
            for r in json.loads(path.read_text(encoding="utf-8"))["data"]:
                if r["level"] != 1 or r["name"].strip() not in COMMODITIES:
                    continue
                for day, value in r.items():
                    if day not in ("no", "name", "level") and value != "-":
                        rows.append((city, day, COMMODITIES[r["name"].strip()], float(value.replace(",", ""))))
    daily = pd.DataFrame(rows, columns=["city", "day", "commodity", "price"])
    daily["day"] = pd.to_datetime(daily["day"], format="%d/%m/%Y")
    daily["date"] = daily["day"].dt.to_period("M").dt.to_timestamp()
    daily = daily.drop_duplicates(["city", "day", "commodity"]).sort_values("day")
    keys = ["city", "date", "commodity"]
    monthly = daily.groupby(keys)["price"].agg(["mean", "count"])
    monthly.loc[monthly["count"] < MIN_DAYS, "mean"] = float("nan")
    first = daily[daily.groupby(keys).cumcount() < NOWCAST_DAYS].groupby(keys)["price"].agg(["mean", "count"])
    first.loc[first["count"] < NOWCAST_DAYS, "mean"] = float("nan")
    wide = pd.concat([monthly["mean"].unstack("commodity"),
                      first["mean"].unstack("commodity").add_suffix("_first")], axis=1)
    return wide.reset_index().rename_axis(columns=None)
