#!/usr/bin/env python
"""Build normalized CSVs from Open Development Mekong (ODM) raw downloads.

Sources (downloaded 2026-11-07 into data/raw/odmekong/, license CC BY-SA 4.0
unless noted otherwise in data/raw/odmekong/PROVENANCE.md):

1. poverty/poverty_rate_1998_2016.csv
   "Proportion of poor households by region in Vietnam from 1998 to 2016"
   https://data.vietnam.opendevelopmentmekong.net/dataset/proportion-of-poor-households-by-region-in-vietnam
   -> 6 REGIONS (not provinces), long format.

2. health/mekong_countries_hospitals_dump.csv
   "Health Facilities in Mekong Countries 2020" (ODbL), datastore dump of
   hospital point locations (SRID 4326).
   -> Vietnam hospitals counted per province via point-in-polygon against
      data/raw/boundaries/diaphantinh.geojson (63 provinces).

Run from repo root:  python -E scripts/build_odmekong_external.py
"""

import csv
import hashlib
import json
import struct
import sys
import unicodedata
from pathlib import Path

import pandas as pd  # user site-packages
from shapely.geometry import Point, shape
from shapely.prepared import prep

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "odmekong"
PROCESSED = ROOT / "data" / "processed"
CROSSWALK = ROOT / "data" / "raw" / "mendeley" / "Replication_package" / "data" / "province_crosswalk_63.csv"
PAPI = ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv"
GEO = ROOT / "data" / "raw" / "boundaries" / "diaphantinh.geojson"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fold_ascii(s: str) -> str:
    """Loose ASCII fold for tolerant name matching."""
    d = unicodedata.normalize("NFD", str(s))
    d = "".join(ch for ch in d if not unicodedata.combining(ch))
    return d.replace("đ", "d").replace("Đ", "D").strip().lower()


# Spelling variants observed in mekong_countries_hospitals_dump.csv ("Province"
# values do not exist there; these come from matching boundary ten_tinh values).
# Explicit, documented aliases only — no fuzzy guessing.
TEN_TINH_ALIAS = {
    "Bà Rịa -Vũng Tàu": "Bà Rịa - Vũng Tàu",  # source spacing typo
    "Cần Thơn": "Cần Thơ",                     # source typo (ơn vs ơ)
    "Quản Bình": "Quảng Bình",                 # source typo (ản vs ảng)
}


# ---------------------------------------------------------------- poverty ---
def build_poverty() -> None:
    src = RAW / "poverty" / "poverty_rate_1998_2016.csv"
    # file uses TAB separators despite the .csv extension
    df = pd.read_csv(src, encoding="utf-8", sep="\t")
    year_cols = [c for c in df.columns if str(c).strip().isdigit()]
    years = sorted(int(c) for c in year_cols)
    long = df.melt(
        id_vars=["Name_EN", "Name_VI"],
        value_vars=[str(y) for y in years],
        var_name="year",
        value_name="poverty_rate_pct",
    )
    long["year"] = long["year"].astype(int)
    long = long.rename(columns={"Name_EN": "region_en", "Name_VI": "region_vi"})
    long = long.sort_values(["region_en", "year"]).reset_index(drop=True)
    out = PROCESSED / "external_odm_poverty_region_1998_2016.csv"
    long.to_csv(out, index=False, encoding="utf-8")
    print(f"[poverty] {len(long)} rows ({long['region_en'].nunique()} regions x {long['year'].nunique()} years "
          f"{long['year'].min()}-{long['year'].max()}) -> {out.name}")


# ------------------------------------------------------------------ health --
def parse_ewkb_point(hexs: str):
    b = bytes.fromhex(hexs)
    if b[0] != 1:
        raise ValueError("only little-endian EWKB expected")
    flags = struct.unpack("<I", b[1:5])[0]
    off = 5
    if flags & 0x20000000:  # SRID present
        struct.unpack("<I", b[off:off + 4])
        off += 4
    gtype = flags & 0xFF
    if gtype != 1:
        raise ValueError(f"geometry type {gtype} is not Point")
    x, y = struct.unpack("<dd", b[off:off + 16])
    return x, y


def build_health() -> None:
    src = RAW / "health" / "mekong_countries_hospitals_dump.csv"
    pts = []
    with open(src, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lon, lat = parse_ewkb_point(row["geometry"])
            pts.append({"lon": lon, "lat": lat, "name": row["name"], "osm_id": row["osm_id"]})
    print(f"[health] decoded {len(pts)} hospital points (SRID 4326)")

    gj = json.loads(GEO.read_text(encoding="utf-8"))
    provs = []
    for feat in gj["features"]:
        geom = shape(feat["geometry"])
        provs.append({"ten_tinh": feat["properties"]["ten_tinh"], "geom": geom})
    print(f"[health] boundary polygons: {len(provs)}")

    for p in provs:
        p["prep"] = prep(p["geom"])
    for pt in pts:
        point = Point(pt["lon"], pt["lat"])
        hit = None
        for p in provs:
            if p["prep"].contains(point):
                hit = p["ten_tinh"]
                break
        pt["ten_tinh"] = hit
    n_vn = sum(1 for pt in pts if pt["ten_tinh"])
    print(f"[health] points inside Vietnam polygons: {n_vn} of {len(pts)}")
    for pt in pts:
        if pt["ten_tinh"] in TEN_TINH_ALIAS:
            pt["ten_tinh"] = TEN_TINH_ALIAS[pt["ten_tinh"]]

    counts = {}
    for pt in pts:
        if pt["ten_tinh"]:
            counts[pt["ten_tinh"]] = counts.get(pt["ten_tinh"], 0) + 1

    cw = pd.read_csv(CROSSWALK, encoding="utf-8-sig", dtype={"province_code": str})
    cw["nfc"] = cw["province_vi"].map(lambda s: unicodedata.normalize("NFC", s).strip())
    cw["fold"] = cw["province_vi"].map(fold_ascii)

    unmatched = sorted(set(counts) - set(cw["nfc"]))
    if unmatched:
        for u in unmatched:
            fold_hits = cw.loc[cw["fold"] == fold_ascii(u), "province_vi"].tolist()
            print(f"[health] WARNING ten_tinh '{u}' not NFC-matched; fold matches: {fold_hits}")
        # fall back to fold match where possible
        remap = {}
        for u in unmatched:
            hits = cw.loc[cw["fold"] == fold_ascii(u), "province_vi"].tolist()
            if len(hits) == 1:
                remap[u] = hits[0]
        if remap:
            counts = {remap.get(k, k): v for k, v in counts.items()}
            print(f"[health] fold-remapped: {remap}")
        still = sorted(set(counts) - set(cw["nfc"]))
        if still:
            print(f"[health] UNRESOLVED province names, left as-is: {still}")

    papi = pd.read_csv(PAPI, encoding="utf-8", dtype={"province_code": str})
    papi_map = (
        papi.groupby("province_ascii")["province_code"]
        .agg(lambda s: ",".join(sorted(set(s))))
        .to_dict()
    )
    papi_ascii = set(papi_map)

    rows = []
    papi_unmatched = []
    for _, r in cw.iterrows():
        vi = unicodedata.normalize("NFC", r["province_vi"]).strip()
        rows.append(
            {
                "province_code": str(r["province_code"]).zfill(2),
                "province_ascii": r["province_ascii"],
                "province_vi": r["province_vi"],
                "year": 2020,
                "hospital_count_odm2020": int(counts.get(vi, 0)),
            }
        )
        if r["province_ascii"] not in papi_ascii:
            papi_unmatched.append(r["province_ascii"])
        # papi_province_code assigned below after reindex

    out_df = pd.DataFrame(rows)
    out_df["papi_province_code"] = out_df["province_ascii"].map(
        lambda a: papi_map.get(a, "")
    )
    out_path = PROCESSED / "external_odm_health_63.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8")

    print(f"[health] wrote {len(out_df)} rows (63 provinces, year=2020) -> {out_path.name}")
    print(f"[health] sum of counts: {out_df['hospital_count_odm2020'].sum()}")
    zero = out_df.loc[out_df["hospital_count_odm2020"] == 0, "province_ascii"].tolist()
    print(f"[health] provinces with 0 hospitals in source: {len(zero)} -> {zero}")
    print(f"[health] crosswalk ascii not found in PAPI panel: {papi_unmatched or 'none'}")
    top = out_df.nlargest(5, "hospital_count_odm2020")[["province_ascii", "hospital_count_odm2020"]]
    print("[health] top 5:", top.to_dict("records"))


# -------------------------------------------------------------- provenance --
def print_manifest() -> None:
    files = [
        RAW / "poverty" / "poverty_rate_1998_2016.csv",
        RAW / "health" / "mekong_countries_hospitals_dump.csv",
        RAW / "health_covid" / "quarantine_en.csv",
    ]
    print("--- manifest (name — bytes — sha256) ---")
    for p in files:
        if p.exists():
            print(f"{p.relative_to(ROOT).as_posix()} — {p.stat().st_size} — {sha256_of(p)}")


if __name__ == "__main__":
    build_poverty()
    build_health()
    print_manifest()
