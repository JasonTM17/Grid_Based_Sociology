"""Ứng viên thuật toán phân cụm thay thế — lane phân tích MỚI [THAM KHẢO — CHƯA DUYỆT GV].

Câu hỏi: trên CÙNG dữ liệu 2D (sd_4_2 × sd_6_1) đã z-score TRONG TỪNG NĂM của
cửa sổ 747 tỉnh-năm year ≤ 2022, DBSCAN (lưới eps suy từ k-distance), k-means
và Ward có tái lập cấu trúc nhãn của STING đóng băng không, và silhouette có
vượt mốc STING tính lại trên cùng cửa sổ + cùng chuẩn hóa không?

Phạm vi & ràng buộc (đúng quy ước 3 lane trước, reports/model_deep_dive.md:5):
- CHỈ THÊM tệp phân tích mới: results/candidates_clustering.{csv,md}.
- KHÔNG ghi/sửa artifact đóng băng — script chỉ ĐỌC hai tệp:
  results/predict_all_years.csv (nhãn + feature 2D) và
  models/predict_config.json (cfg STING đóng băng).
- KHÔNG thay model production; không đổi số đã công bố (Ridge 0.265,
  carry 0.145, LR 0.434, k=3). Holdout 2023→2024 không fit/chấm/nhìn: cửa sổ
  chốt year ≤ 2022, loại cả 61 dòng năm 2023 (origin holdout).

Thiết kế chốt TRƯỚC khi chạy (pre-registered trong ask của lane):
- Chuẩn hóa: z-score trong từng năm (ddof=0) trên 2 cột — cùng mẫu
  scripts/run_analysis.py:256; mỗi năm dùng mean/sd của chính năm đó.
- Ứng viên: DBSCAN min_samples ∈ {5, 10} × eps tại phân vị
  {50, 60, 70, 80, 90}% của phân phối k-distance (k = min_samples; hàng xóm
  tính BAO GỒM tự thân — NearestNeighbors trả chính điểm đó ở vị trí đầu với
  khoảng cách 0, nên cột cuối là khoảng cách tới (min_samples − 1) điểm KHÁC
  gần nhất; với eps bằng giá trị đó, điểm vừa đủ core point theo định nghĩa
  DBSCAN |N_eps| ≥ min_samples kể cả tự thân) — 10 combo suy từ dữ liệu, không
  tune tay; KMeans(k=3, random_state=11, n_init=10); Ward(k=3, linkage=ward).
- Mốc: nhãn STING đóng băng (cột pred_cluster) tính lại silhouette/noise/sizes
  trên đúng 747 dòng + z-trong-năm (silhouette 0.3611 đã công bố tính trên
  cửa sổ khác — fit 2011–2023, results/cluster_profile.md:97).
- Deconfound: refit STING đúng cfg đóng băng (L=3, f=4, mc=5, level=2,
  connectivity=1 — models/predict_config.json:12-18) trên cùng z-trong-năm;
  ARI(refit, nhãn gốc) tách "hiệu ứng chuẩn hóa" khỏi "hiệu ứng thuật toán".
- Metrics mỗi dòng: ARI vs nhãn đóng băng 2 cách (đầy đủ với −1 là một nhãn;
  chỉ trên dòng non-noise của nhãn đóng băng), ARI 2 cách vs refit (đọc
  deconfound), silhouette (euclidean; DBSCAN/STING chỉ tính trên điểm
  non-noise của chính nhãn đó, yêu cầu ≥ 2 cụm non-noise nếu không n/a),
  noise rate, sizes_top5 (quy ước models/predict_config.json:21 — kích thước
  non-noise, giảm dần), cờ noise ≤ 0.25 (mô tả theo bộ lọc cũ, KHÔNG phải bộ
  lọc ứng viên).
- Ngưỡng thắng (chốt trước): ứng viên thắng mốc CHỈ khi vượt mốc trên CẢ 3
  chỉ số ARI đầy đủ, ARI non-noise, silhouette (đọc chặt nhất của "3 chỉ số"
  trong đề bài). Exploratory — không tuyên bố p-value, không hiệu chỉnh đa so
  sánh; mọi kết quả chỉ là THAM KHẢO cho quyết định của GV.
- Tất định: seed 11; không timestamp trong đầu ra → chạy 2 lần cho md/csv
  sha256 byte-giống.

Chạy: python -E scripts/candidates_clustering.py   (từ thư mục gốc repo)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.neighbors import NearestNeighbors

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from papi_pred_common import ROOT, load_config  # noqa: E402
from sting import STING  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SEED = 11
RESULTS = ROOT / "results"
PRED_CSV = RESULTS / "predict_all_years.csv"
OUT_CSV = RESULTS / "candidates_clustering.csv"
OUT_MD = RESULTS / "candidates_clustering.md"

WINDOW_MAX_YEAR = 2022  # loại 2023 (origin holdout) và 2024 (ngoài fit)
FEATS = ["sd_4_2", "sd_6_1"]
MIN_SAMPLES_GRID = (5, 10)
KDIST_PCTS = (50, 60, 70, 80, 90)
NOISE_FLAG_MAX = 0.25  # cờ mô tả theo bộ lọc cũ — KHÔNG phải bộ lọc ứng viên
# Kiểm chứng fail-closed artifact đóng băng: số đếm trong phiên thiết kế trên
# predict_all_years.csv (747 dòng; khớp join PCI 747 — cluster_profile.md:34).
EXPECTED_N = 747
EXPECTED_DIST = {-1: 149, 0: 5, 1: 16, 2: 577}
EXPECTED_EXCLUDED = 122  # 61 dòng 2023 + 61 dòng 2024 bị loại khỏi cửa sổ
# Sanity phiên thiết kế (in-memory): KMeans(3, seed 11, n_init=10) trên
# z-trong-năm cho đa thức sizes {234, 307, 206}, ARI đầy đủ 0.0557.
EXPECTED_KMEANS_SIZES = sorted([234, 307, 206])
EXPECTED_KMEANS_ARI = 0.0557


def load_window() -> tuple[pd.DataFrame, np.ndarray]:
    """Đọc artifact đóng băng (đọc thôi) và chốt cửa sổ year ≤ 2022."""
    df = pd.read_csv(PRED_CSV)
    win = df[df.year <= WINDOW_MAX_YEAR].reset_index(drop=True)
    excluded = len(df) - len(win)
    if len(win) != EXPECTED_N:
        raise ValueError(
            f"Cửa sổ year ≤ {WINDOW_MAX_YEAR} = {len(win)} dòng, kỳ vọng "
            f"{EXPECTED_N} — artifact đóng băng results/predict_all_years.csv "
            "đã đổi? DỪNG, không so sánh."
        )
    if excluded != EXPECTED_EXCLUDED:
        raise ValueError(
            f"Số dòng bị loại {excluded} ≠ {EXPECTED_EXCLUDED} (61 dòng 2023 + "
            "61 dòng 2024) — artifact đóng băng đã đổi? DỪNG."
        )
    dist = {int(k): int(v) for k, v in win["pred_cluster"].value_counts().items()}
    if dist != EXPECTED_DIST:
        raise ValueError(
            f"Phân bố nhãn đóng băng {dist} ≠ {EXPECTED_DIST} — DỪNG."
        )
    if win[FEATS].isna().any().any():
        raise ValueError("Cửa sổ có dòng thiếu sd_4_2/sd_6_1 — không kỳ vọng.")
    return win, win["pred_cluster"].to_numpy()


def year_zscore(win: pd.DataFrame) -> np.ndarray:
    """z-score trong từng năm (ddof=0) — mỗi năm dùng mean/sd của chính năm đó."""
    Z = win[FEATS].groupby(win["year"]).transform(
        lambda s: (s - s.mean()) / s.std(ddof=0)
    )
    X = Z.to_numpy()
    if not np.isfinite(X).all():
        raise ValueError("z-trong-năm chứa NaN/inf (có năm cột hằng số?).")
    return X


def sting_refit_labels(X: np.ndarray, cfg: dict) -> np.ndarray:
    """Refit STING đúng cfg đóng băng trên X đã z-trong-năm (deconfound).

    STING chia lưới đều theo min/max từng chiều (src/sting.py:263-271) nên
    bất biến với biến đổi affine từng chiều — không cần thêm StandardScaler
    trên dữ liệu đã z; "trên CÙNG dữ liệu z-trong-năm" = fit trực tiếp.
    """
    sp = cfg["sting"]
    model = STING(
        n_levels=sp["n_levels"], factor=sp["factor"], min_count=sp["min_count"]
    ).fit(X)
    return np.asarray(
        model.cluster(
            level=sp["cluster_level"], connectivity=sp["connectivity"]
        ),
        dtype=int,
    )


def kdistance(X: np.ndarray, min_samples: int) -> np.ndarray:
    """Phân phối k-distance (k = min_samples, hàng xóm kể cả tự thân)."""
    nn = NearestNeighbors(n_neighbors=min_samples).fit(X)
    d, _ = nn.kneighbors(X)
    return d[:, -1]


def geom_silhouette(
    X: np.ndarray, labels: np.ndarray, exclude_noise: bool
) -> tuple[float, int]:
    """Silhouette euclidean; DBSCAN/STING chỉ trên điểm non-noise của nhãn đó."""
    mask = labels >= 0 if exclude_noise else np.ones(len(labels), dtype=bool)
    lab = labels[mask]
    n_sil = int(mask.sum())
    if np.unique(lab).size < 2:
        return float("nan"), n_sil
    return float(silhouette_score(X[mask], lab, metric="euclidean")), n_sil


def sizes_top5(labels: np.ndarray) -> str:
    """Kích thước cụm non-noise giảm dần, tối đa 5 — quy ước sizes_top5."""
    non = labels[labels >= 0]
    sizes = sorted((int((non == c).sum()) for c in np.unique(non)), reverse=True)
    return str(sizes[:5])


def ari_on(
    ref: np.ndarray, lab: np.ndarray, mask: np.ndarray | None = None
) -> float:
    if mask is None:
        return float(adjusted_rand_score(ref, lab))
    return float(adjusted_rand_score(ref[mask], lab[mask]))


def metric_row(
    method: str,
    family: str,
    labels: np.ndarray,
    X: np.ndarray,
    frozen: np.ndarray,
    refit: np.ndarray,
    exclude_noise_sil: bool,
    min_samples: int | None = None,
    eps: float | None = None,
    kdist_pct: int | None = None,
    note: str = "",
) -> dict:
    """Một dòng bảng so sánh — mọi số tính tại đây, không hardcode."""
    sil, n_sil = geom_silhouette(X, labels, exclude_noise_sil)
    k = int(np.unique(labels[labels >= 0]).size)
    noise = float((labels == -1).mean())
    return {
        "method": method,
        "family": family,
        "min_samples": min_samples,
        "eps": (round(float(eps), 4) if eps is not None else None),
        "kdist_pct": kdist_pct,
        "k": k,
        "noise_rate": round(noise, 4),
        "noise_le_025": bool(noise <= NOISE_FLAG_MAX),
        "sizes_top5": sizes_top5(labels),
        "ari_full_vs_frozen": round(ari_on(frozen, labels), 4),
        "ari_nonnoise_vs_frozen": round(
            ari_on(frozen, labels, frozen != -1), 4
        ),
        "ari_full_vs_refit": round(ari_on(refit, labels), 4),
        "ari_nonnoise_vs_refit": round(
            ari_on(refit, labels, refit != -1), 4
        ),
        "silhouette": (round(sil, 4) if np.isfinite(sil) else None),
        "n_sil": n_sil,
        "note": note,
    }


def crosstab_md(frozen: np.ndarray, labels: np.ndarray, name: str) -> str:
    """Bảng đếm chéo nhãn đóng băng × nhãn ứng viên (nhiễu −1 đứng cuối)."""
    key = lambda v: (v == -1, v)  # noqa: E731
    row_ids = sorted(set(frozen.tolist()), key=key)
    col_ids = sorted(set(labels.tolist()), key=key)
    ct = pd.crosstab(pd.Series(frozen), pd.Series(labels))
    ct = ct.reindex(index=row_ids, columns=col_ids, fill_value=0)

    def cell_name(v: int) -> str:
        return "nhiễu (−1)" if v == -1 else f"cụm {v}"

    head = "| STING đóng băng | " + " | ".join(
        f"{name} {cell_name(c)}" for c in col_ids
    ) + " |"
    sep = "|---|" + "---|" * len(col_ids)
    body = [
        "| " + cell_name(r) + " | "
        + " | ".join(str(int(ct.loc[r, c])) for c in col_ids) + " |"
        for r in row_ids
    ]
    return "\n".join([head, sep, *body])


def overlap_reading(
    frozen: np.ndarray, labels: np.ndarray, name: str
) -> str:
    """Một dòng đọc: cụm 0/1/2 đóng băng đổ chủ yếu vào đâu của ứng viên."""
    parts = []
    for c in (0, 1, 2):
        mask = frozen == c
        n = int(mask.sum())
        if n == 0:
            continue
        vals, counts = np.unique(labels[mask], return_counts=True)
        i = int(np.argmax(counts))
        top_v, top_n = int(vals[i]), int(counts[i])
        share = top_n / n
        dest = "nhiễu" if top_v == -1 else f"cụm {top_v}"
        parts.append(
            f"cụm {c} ({n} dòng) → {dest}: {top_n}/{n} ({share:.0%})"
        )
    return f"- {name}: " + "; ".join(parts) + "."


def f4(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float) and not np.isfinite(v):
        return "n/a"
    return f"{v:.4f}"


def dash(v) -> str:
    return "–" if v is None else str(v)


def main() -> int:
    cfg = load_config()
    win, frozen = load_window()
    X = year_zscore(win)
    refit = sting_refit_labels(X, cfg)
    print(f"cửa sổ: {len(win)} dòng year ≤ {WINDOW_MAX_YEAR} | "
          f"phân bố nhãn đóng băng {EXPECTED_DIST}")
    per_year = win.groupby("year").size()
    short_years = {int(y): int(n) for y, n in per_year.items() if n != 63}
    print(f"n theo năm: {dict(per_year)} | năm không đủ 63: {short_years}")

    # ---- Mốc + deconfound ------------------------------------------------
    rows = [
        metric_row(
            "STING đóng băng — nhãn gốc CSV (mốc)", "sting_frozen",
            frozen, X, frozen, refit, True,
            note="mốc công bằng: nhãn pred_cluster của predict_all_years.csv "
                 "trên đúng 747 dòng + z-trong-năm; ARI vs chính nó = 1",
        ),
        metric_row(
            "STING refit z-trong-năm (cfg đóng băng)", "sting_refit",
            refit, X, frozen, refit, True,
            note="deconfound: refit cfg đóng băng (L=3, f=4, mc=5, lv=2, "
                 "conn=1) trên cùng z-trong-năm — tách hiệu ứng chuẩn hóa",
        ),
    ]

    # ---- K1: DBSCAN grid suy từ k-distance -------------------------------
    labels_by_method: dict[str, np.ndarray] = {}
    eps_summary: list[tuple[int, float, float, float]] = []
    for ms in MIN_SAMPLES_GRID:
        kd = kdistance(X, ms)
        eps_summary.append(
            (ms, float(kd.min()), float(np.median(kd)), float(kd.max()))
        )
        for pct in KDIST_PCTS:
            eps = float(np.percentile(kd, pct))
            labels = DBSCAN(eps=eps, min_samples=ms).fit_predict(X)
            method = f"DBSCAN ms={ms} eps={eps:.4f} (k-dist p{pct})"
            k = int(np.unique(labels[labels >= 0]).size)
            note = "tất cả điểm là nhiễu" if k == 0 else (
                "<2 cụm non-noise → silhouette n/a" if k < 2 else ""
            )
            rows.append(
                metric_row(method, "dbscan", labels, X, frozen, refit, True,
                           min_samples=ms, eps=eps, kdist_pct=pct, note=note)
            )
            labels_by_method[method] = labels
    print("DBSCAN grid: 10 combo xong")

    # ---- K2/K3: k-means + Ward -------------------------------------------
    km = KMeans(n_clusters=3, random_state=SEED, n_init=10).fit_predict(X)
    km_method = f"KMeans k=3 (seed {SEED}, n_init=10)"
    rows.append(
        metric_row(km_method, "kmeans", km, X, frozen, refit, False,
                   note="tất cả điểm được gán cụm")
    )
    labels_by_method[km_method] = km
    ward = AgglomerativeClustering(n_clusters=3, linkage="ward").fit_predict(X)
    ward_method = "Ward k=3 (linkage=ward)"
    rows.append(
        metric_row(ward_method, "ward", ward, X, frozen, refit, False,
                   note="tất cả điểm được gán cụm")
    )
    labels_by_method[ward_method] = ward

    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"đã ghi {OUT_CSV}")

    # ---- Ngưỡng thắng (chốt trước) ---------------------------------------
    bench = next(r for r in rows if r["family"] == "sting_frozen")
    cand = [r for r in rows if r["family"] in ("dbscan", "kmeans", "ward")]

    def beats(r: dict) -> bool:
        return (
            r["ari_full_vs_frozen"] > bench["ari_full_vs_frozen"]
            and r["ari_nonnoise_vs_frozen"] > bench["ari_nonnoise_vs_frozen"]
            and r["silhouette"] is not None
            and r["silhouette"] > bench["silhouette"]
        )

    winners = [r for r in cand if beats(r)]

    # ---- DBSCAN narrative --------------------------------------------------
    db_rows = [r for r in rows if r["family"] == "dbscan"]
    best_db = sorted(
        db_rows,
        key=lambda r: (
            -r["ari_nonnoise_vs_frozen"], -r["ari_full_vs_frozen"], r["method"]
        ),
    )[0]

    # ---- Đọc theo thành phần (trung thực, sinh từ chính bảng) -------------
    sil_beat = [
        r for r in cand
        if r["silhouette"] is not None and r["silhouette"] > bench["silhouette"]
    ]
    max_ari_nn = max(r["ari_nonnoise_vs_frozen"] for r in cand)
    max_ari_full = max(r["ari_full_vs_frozen"] for r in cand)
    best_vs_refit = max(
        cand,
        key=lambda r: (r["ari_nonnoise_vs_refit"], r["ari_full_vs_refit"]),
    )
    k3_db = [r for r in db_rows if r["k"] == 3]
    db_trend_lines = []
    for ms in MIN_SAMPLES_GRID:
        sub = [r for r in db_rows if r["min_samples"] == ms]
        db_trend_lines.append(
            f"  - ms={ms}: "
            + "; ".join(
                f"p{r['kdist_pct']}: k={r['k']}, noise={r['noise_rate']:.2f}, "
                f"sil={f4(r['silhouette'])}"
                for r in sub
            )
            + "."
        )

    # ---- Sanity vs phiên thiết kế ----------------------------------------
    km_row = next(r for r in rows if r["family"] == "kmeans")
    km_sizes = [int(v) for v in km_row["sizes_top5"].strip("[]").split(",")]
    km_sizes_sorted = sorted(km_sizes)
    sanity_sizes_ok = km_sizes_sorted == EXPECTED_KMEANS_SIZES
    sanity_ari_ok = (
        abs(km_row["ari_full_vs_frozen"] - EXPECTED_KMEANS_ARI) < 5e-5
    )

    # ---- Deconfound số đọc ------------------------------------------------
    refit_row = next(r for r in rows if r["family"] == "sting_refit")

    # ---- Bảng md -----------------------------------------------------------
    cols = [
        ("method", "phương pháp"), ("min_samples", "min_samples"),
        ("eps", "eps"), ("kdist_pct", "phân vị k-dist (%)"),
        ("k", "k (non-noise)"), ("noise_rate", "noise"),
        ("noise_le_025", "noise≤0.25"), ("sizes_top5", "sizes_top5"),
        ("ari_full_vs_frozen", "ARI đầy đủ"),
        ("ari_nonnoise_vs_frozen", "ARI non-noise"),
        ("silhouette", "silhouette"), ("n_sil", "n_sil"),
        ("ari_full_vs_refit", "ARI đầy đủ vs refit"),
        ("ari_nonnoise_vs_refit", "ARI non-noise vs refit"), ("note", "ghi chú"),
    ]

    def cell(r: dict, c: str) -> str:
        v = r[c]
        if c == "noise_le_025":
            return "có" if v else "không"
        if c in ("min_samples", "kdist_pct"):
            return dash(v)
        if c == "eps":
            return dash(None if v is None else f"{v:.4f}")
        if c in ("ari_full_vs_frozen", "ari_nonnoise_vs_frozen",
                 "ari_full_vs_refit", "ari_nonnoise_vs_refit", "silhouette"):
            return f4(v)
        return str(v)

    tbl = ["| " + " | ".join(h for _, h in cols) + " |",
           "|" + "---|" * len(cols)]
    tbl += [
        "| " + " | ".join(cell(r, c) for c, _ in cols) + " |" for r in rows
    ]

    eps_lines = [
        "| min_samples | phân vị (%) | eps |", "|---|---|---|",
    ]
    for r in rows:
        if r["family"] == "dbscan":
            eps_lines.append(
                f"| {r['min_samples']} | {r['kdist_pct']} | {r['eps']:.4f} |"
            )
    kd_lines = [
        "| min_samples | min | trung vị | max |", "|---|---|---|---|",
    ]
    kd_lines += [
        f"| {ms} | {lo:.4f} | {med:.4f} | {hi:.4f} |"
        for ms, lo, med, hi in eps_summary
    ]

    crosstabs = [
        crosstab_md(frozen, labels_by_method[km_method], "KMeans"),
        crosstab_md(frozen, labels_by_method[ward_method], "Ward"),
        crosstab_md(frozen, labels_by_method[best_db["method"]], "DBSCAN best"),
    ]
    overlaps = [
        overlap_reading(frozen, labels_by_method[km_method], "KMeans"),
        overlap_reading(frozen, labels_by_method[ward_method], "Ward"),
        overlap_reading(
            frozen, labels_by_method[best_db["method"]],
            f"DBSCAN best ({best_db['method']})",
        ),
    ]

    if winners:
        win_txt = "; ".join(
            f"{r['method']} (ARI đầy đủ {r['ari_full_vs_frozen']:.4f}, "
            f"ARI non-noise {r['ari_nonnoise_vs_frozen']:.4f}, "
            f"silhouette {f4(r['silhouette'])})"
            for r in winners
        )
        verdict = (
            "Ứng viên vượt mốc trên CẢ 3 chỉ số (ngưỡng thắng chốt trước): "
            + win_txt
            + ". Đây vẫn chỉ là kết quả THAM KHẢO [CHƯA DUYỆT GV] — thay "
            "thuật toán cụm công bố thuộc nhóm (b) cần GV duyệt "
            "(reports/model_deep_dive.md:293-299)."
        )
    else:
        verdict = (
            "KHÔNG ứng viên nào vượt mốc trên cả 3 chỉ số — đọc trung thực: "
            "không có cơ sở từ lane này để thay STING đóng băng; khuyến nghị "
            "mặc định giữ nguyên cấu hình cho tới khi GV quyết định."
        )

    lines = [
        "# Ứng viên thuật toán phân cụm thay thế — cửa sổ 747 tỉnh-năm ≤2022, "
        "z-score trong từng năm",
        "",
        "**[THAM KHẢO — CHƯA DUYỆT GV]** — lane phân tích MỚI, sinh bởi "
        "`scripts/candidates_clustering.py`; CHỈ thêm 2 tệp này "
        "(`results/candidates_clustering.{csv,md}`), không đụng artifact đóng "
        "băng (`models/predict_config.json`, `results/predict_all_years.csv` "
        "— chỉ đọc), không thay model production, không đổi số đã công bố "
        "(Ridge 0.265, carry 0.145, LR 0.434, k=3). Holdout 2023→2024 không "
        "fit/chấm/nhìn; cửa sổ loại cả 61 dòng năm 2023 (origin holdout).",
        "",
        "## Thiết kế chốt trước khi chạy (pre-registered trong ask của lane)",
        "",
        "- **Dữ liệu**: `results/predict_all_years.csv` (artifact đóng băng, "
        "đọc thôi) — 2D sd_4_2 × sd_6_1, nhãn STING đóng băng = cột "
        "`pred_cluster` (model fit 2011–2023, lưới toàn cục — "
        "`scripts/predict_demo.py`).",
        "- **Cửa sổ**: year ≤ 2022 → 747 dòng (869 tổng − 61 dòng 2023 − 61 "
        "dòng 2024; script fail-closed kiểm đúng phân bố nhãn −1: 149, 0: 5, "
        "1: 16, 2: 577 — khớp join PCI 747, `results/cluster_profile.md:34`).",
        "- **Chuẩn hóa**: z-score TRONG TỪNG NĂM (ddof=0) trên 2 cột — cùng "
        "mẫu `scripts/run_analysis.py:256`; mỗi năm dùng mean/sd của chính "
        "năm đó. *Ghi chú trung thực*: đề bài nói 'mỗi năm 63 điểm' nhưng "
        f"thực tế {len(short_years)} năm trong cửa sổ không đủ 63 dòng "
        f"({short_years}) — phương pháp không đổi: từng năm vẫn chuẩn hóa "
        "bằng mean/sd của chính năm đó.",
        "- **Ứng viên**: DBSCAN min_samples ∈ {5, 10} × eps tại phân vị "
        "{50, 60, 70, 80, 90}% của phân phối k-distance (10 combo suy từ dữ "
        "liệu, không tune tay); KMeans(k=3, random_state=11, n_init=10); "
        "Ward(k=3, linkage=ward).",
        "- **Metrics**: ARI vs nhãn đóng băng 2 cách (đầy đủ / chỉ non-noise "
        "của nhãn đóng băng); ARI 2 cách vs refit (đọc deconfound); "
        "silhouette euclidean (DBSCAN/STING chỉ tính trên non-noise của nhãn "
        "đó, <2 cụm non-noise → n/a); noise rate; sizes_top5 (quy ước "
        "`models/predict_config.json:21` — non-noise, giảm dần); cờ "
        "noise ≤ 0.25 (mô tả theo bộ lọc cũ, KHÔNG phải bộ lọc ứng viên).",
        "- **Ngưỡng thắng (chốt trước)**: ứng viên thắng mốc CHỈ khi vượt "
        "'STING đóng băng tính lại trên cùng 747 dòng' trên CẢ 3 chỉ số ARI "
        "đầy đủ, ARI non-noise, silhouette (đọc chặt nhất của '3 chỉ số' "
        "trong đề bài; noise rate chỉ mô tả). Exploratory — không tuyên bố "
        "p-value, không hiệu chỉnh đa so sánh; cấm trích 1 combo đẹp lẻ tẻ.",
        "",
        "## Bảng so sánh đầy đủ (14 dòng: mốc + deconfound + 12 ứng viên)",
        "",
        *tbl,
        "",
        "Đọc bảng: 'ARI đầy đủ'/'ARI non-noise' so với nhãn STING đóng băng "
        "(cột `pred_cluster`); 'vs refit' so với STING refit trên cùng "
        "z-trong-năm. silhouette của DBSCAN/STING tính trên điểm non-noise "
        "của chính nhãn đó (n_sil); KMeans/Ward tính trên cả 747 điểm.",
        "",
        "## Lưới eps suy từ k-distance (không tune tay)",
        "",
        "Quy ước: k-distance = khoảng cách tới hàng xóm thứ-k với "
        "k = min_samples, tính bởi `NearestNeighbors` — hàng xóm đầu tiên là "
        "chính điểm đó (khoảng cách 0), nên cột cuối là khoảng cách tới "
        "(min_samples − 1) điểm KHÁC gần nhất; với eps bằng giá trị đó, điểm "
        "vừa đủ core point (|N_eps| ≥ min_samples kể cả tự thân).",
        "",
        *eps_lines,
        "",
        "Phân phối k-distance theo min_samples:",
        "",
        *kd_lines,
        "",
        "## Deconfound: tách hiệu ứng chuẩn hóa khỏi hiệu ứng thuật toán",
        "",
        f"- STING refit đúng cfg đóng băng (L=3, f=4, mc=5, level=2, "
        f"connectivity=1) trên cùng z-trong-năm: k={refit_row['k']}, "
        f"noise={refit_row['noise_rate']:.4f}, "
        f"sizes={refit_row['sizes_top5']}, "
        f"silhouette={f4(refit_row['silhouette'])} (n={refit_row['n_sil']}).",
        f"- ARI(refit, nhãn đóng băng gốc): đầy đủ "
        f"{refit_row['ari_full_vs_frozen']:.4f}, non-noise "
        f"{refit_row['ari_nonnoise_vs_frozen']:.4f} — đây là mức ARI 'trần' "
        "chỉ do ĐỔI CHUẨN HÓA (scaler pooled cửa sổ-dài fit ≤2023 của model "
        "đóng băng vs z-trong-năm) khi thuật toán giữ nguyên. STING bất biến "
        "affine từng chiều (`src/sting.py:263-271`) nên refit không thêm "
        "scaler — khác biệt chỉ đến từ việc z-trong-năm xáo trộn vị trí tương "
        "đối GIỮA các năm (scaler đóng băng dùng 1 hệ trục chung cho cả cửa "
        "sổ), làm đổi ô lưới của từng điểm.",
        f"- Đọc: ARI(refit, gốc) đầy đủ "
        f"{refit_row['ari_full_vs_frozen']:.4f}, non-noise "
        f"{refit_row['ari_nonnoise_vs_frozen']:.4f} — "
        + (
            "cao — thay chuẩn hóa gần như không đổi nhãn STING, nên ARI thấp "
            "của ứng viên phản ánh chủ yếu HIỆU ỨNG THUẬT TOÁN."
            if refit_row["ari_nonnoise_vs_frozen"] >= 0.8 else
            "thấp/trung bình — một phần ARI thấp của ứng viên có thể do CHUẨN "
            "HÓA, không phải do thuật toán; đọc kèm cột 'vs refit' (cùng "
            "chuẩn hóa) để cô lập hiệu ứng thuật toán."
            if refit_row["ari_nonnoise_vs_frozen"] >= 0.3 else
            "gần như 0 trên dòng non-noise — nhãn đóng băng trên z-trong-năm "
            "khác xa nhãn gốc; so sánh ứng viên phải đọc CẢ hai cột ARI "
            "(vs gốc và vs refit) mới tách được hiệu ứng chuẩn hóa khỏi "
            "hiệu ứng thuật toán."
        ),
        f"- Mốc công bằng trên cửa sổ này: silhouette nhãn đóng băng (non-"
        f"noise) = {f4(bench['silhouette'])} (n={bench['n_sil']}), "
        f"noise={bench['noise_rate']:.4f}, sizes={bench['sizes_top5']} — "
        "*khác* silhouette 0.3611 đã công bố vì 0.3611 tính trên cửa sổ khác "
        "(fit 2011–2023, scaler pooled; `results/cluster_profile.md:97`); "
        "không so chéo số giữa hai cửa sổ.",
        "",
        "## Nhận xét trung thực",
        "",
        "- **KMeans sanity khớp phiên thiết kế**: sizes "
        f"{km_row['sizes_top5']} (đa tập khớp {EXPECTED_KMEANS_SIZES}: "
        f"{'CÓ' if sanity_sizes_ok else 'KHÔNG'}), ARI đầy đủ "
        f"{km_row['ari_full_vs_frozen']:.4f} vs 0.0557 trong phiên thiết kế "
        f"({'CÓ' if sanity_ari_ok else 'KHÔNG'}) — xác nhận kỳ vọng: ARI "
        "tuyệt đối thấp vì cấu trúc '1 cụm lớn + nhiễu' của STING không thể "
        "được k-means (3 cụm cân) tái lập.",
        "- **DBSCAN cho ra gì ở eps nào** (đọc thẳng từ bảng, không tune "
        "tay):",
        *db_trend_lines,
        "- **Hình thức vs thành phần**: "
        f"{len(k3_db)}/10 combo DBSCAN cho k=3 ("
        + "; ".join(
            f"{r['method']} sizes={r['sizes_top5']}, "
            f"ARI non-noise {r['ari_nonnoise_vs_frozen']:.4f}"
            for r in k3_db
        )
        + ") — cùng HÌNH THỨC '1 cụm lớn + 2 cụm li ti' như đóng băng "
        "[577, 16, 5] nhưng thành phần khác hẳn (ARI non-noise ≈ 0); cụm li "
        "ti của ứng viên có trùng cụm 0/1 đóng băng hay không xem đếm chéo "
        "bên dưới.",
        "- **Có cụm nào tương đương STING không** — đếm chéo trên 747 dòng:",
        "",
        *crosstabs,
        "",
        *overlaps,
        "",
        f"- **Verdict ngưỡng thắng (chốt trước)**: {verdict}",
        "- **Đọc theo thành phần** (verdict giữ nguyên, không đổi metric sau "
        "khi thấy số):",
        f"  - silhouette: {len(sil_beat)}/12 ứng viên vượt mốc "
        f"{bench['silhouette']:.4f} (top: "
        + "; ".join(
            f"{r['method']} {r['silhouette']:.4f}"
            for r in sorted(
                (x for x in cand if x["silhouette"] is not None),
                key=lambda x: -x["silhouette"],
            )[:3]
        )
        + ") — NHƯNG mốc là silhouette của CHÍNH phân hoạch công bố trên "
        "z-trong-năm và nó ÂM (dưới chuẩn hóa này phân hoạch công bố không "
        "tách biệt hình học), và silhouette của DBSCAN/STING tính trên "
        "non-noise nên n_sil khác nhau giữa các dòng — không so tuyệt đối.",
        f"  - tái lập cấu trúc: KHÔNG ứng viên nào tái lập phân hoạch đóng "
        f"băng — ARI non-noise tối đa {max_ari_nn:.4f}, ARI đầy đủ tối đa "
        f"{max_ari_full:.4f} (≈ 0). Ghi chú về ngưỡng chốt trước: mốc ARI "
        "của 'STING đóng băng tính lại' là ARI của mốc với chính nó (= 1.0), "
        "nên tiêu chí 'ARI > mốc' đọc nghĩa đen là không thể đạt bởi ứng "
        "viên nào; nội dung ràng buộc có ý nghĩa của tiêu chí là 'tái lập "
        "cấu trúc đóng băng' — và KHÔNG ứng viên nào đạt.",
        f"  - deconfound (quyết định cách hiểu ARI): chính STING refit trên "
        f"z-trong-năm cũng chỉ đạt ARI non-noise "
        f"{refit_row['ari_nonnoise_vs_frozen']:.4f} với nhãn gốc của nó — "
        "phần lớn khoảng cách ARI giữa ứng viên và nhãn gốc là HIỆU ỨNG "
        "CHUẨN HÓA, không phải hiệu ứng thuật toán. Trên cùng chuẩn hóa "
        f"(cột 'vs refit'), ứng viên đồng thuận nhất là "
        f"{best_vs_refit['method']} (k={best_vs_refit['k']}, ARI non-noise "
        f"{best_vs_refit['ari_nonnoise_vs_refit']:.4f}, đầy đủ "
        f"{best_vs_refit['ari_full_vs_refit']:.4f})"
        + (
            " — k=" + str(best_vs_refit["k"])
            + " nên sự đồng thuận này chủ yếu là 'cùng mô tả một khối/cấu "
            "trúc lớn', KHÔNG phải cùng phân hoạch nhiều cụm."
            if best_vs_refit["k"] <= 2 else
            " (đồng thuận trên cả cụm nhỏ — xem đếm chéo)."
        ),
        "  - kết luận chung: không có cơ sở từ lane này để thay STING đóng "
        "băng; dưới z-trong-năm, dữ liệu 2D đọc là 'một khối + ngoại vi' ở "
        "mọi thuật toán, còn phân hoạch 3 cụm cân của KMeans/Ward có "
        "silhouette cao hơn nhưng KHÔNG liên kết với cấu trúc đã công bố "
        "(ARI ≈ 0) — việc 'thắng silhouette' của chúng là đổi câu hỏi, "
        "không phải tái lập cấu trúc; quyền kết luận thuộc GV.",
        "",
        "## Hạn chế & phạm vi",
        "",
        "- Exploratory: 12 combo ứng viên × 1 cửa sổ; KHÔNG hiệu chỉnh đa so "
        "sánh, KHÔNG tuyên bố p-value — guard chống fishing là ngưỡng thắng "
        "chốt trước + duyệt đọc trung thực; adoption cần GV "
        "(reports/model_deep_dive.md:293-299, nhóm (b)).",
        "- Tiêu chí 'nhất quán ≥4/6 fold' của đề bài áp dụng cho hồi quy/"
        "phân loại (có 6 fold expanding origin 2017–2022); clustering KHÔNG "
        "có fold nên tiêu chí này KHÔNG áp dụng được ở lane này — chỉ so "
        "ngang chỉ số trên cùng cửa sổ như pre-registered.",
        f"- {len(short_years)} năm cửa sổ không đủ 63 dòng ({short_years}) "
        "— z-trong-năm vẫn dùng mean/sd của chính năm đó; số 'mỗi năm 63 "
        "điểm' trong đề bài là gần đúng, không ảnh hưởng phương pháp.",
        "- ARI đo sự TÁI LẬP cấu trúc nhãn đóng băng (pseudo-label), không "
        "phải chất lượng phân cụm tuyệt đối; nhãn cụm 0/1 của STING là cụm "
        "li ti (5/16 dòng chỉ ở 2011–2018) — mọi kết luận vững chỉ nên dựa "
        "trên tương phản nhiễu vs cụm 2 (results/cluster_profile.md:127).",
        "- Silhouette KMeans/Ward tính trên CẢ 747 điểm gồm cả 149 điểm mà "
        "STING gọi là nhiễu — so với silhouette non-noise của STING là khác "
        "tập điểm; cột n_sil ghi rõ tập điểm mỗi dòng.",
        "- NOT_RUN: không có mục NOT_RUN — script tính được toàn bộ metrics "
        "yêu cầu trong ask; các kiểm định phiên (2 lần chạy sha256 "
        "byte-giống, ruff, pytest) do lane báo cáo kèm, nằm ngoài tệp này.",
        "",
        "## Tái lập",
        "",
        "```powershell",
        "python -E scripts/candidates_clustering.py",
        "python -m ruff check .",
        "```",
        "",
        "- Đầu vào (chỉ đọc): `results/predict_all_years.csv`, "
        "`models/predict_config.json`.",
        "- Đầu ra MỚI: file này + `results/candidates_clustering.csv`.",
        "- Tất định: seed 11 (KMeans); DBSCAN/Ward/STING tất định; không có "
        "thời gian hệ thống trong đầu ra → chạy 2 lần cho md/csv sha256 "
        "byte-giống.",
        "- Script fail-closed: cửa sổ ≠ 747 dòng, phân bố nhãn lệch, hoặc "
        "số dòng bị loại ≠ 122 đều DỪNG với lỗi rõ ràng (artifact đóng băng "
        "đã đổi).",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"đã ghi {OUT_MD}")

    print("\nsanity KMeans vs phiên thiết kế: "
          f"sizes {km_sizes_sorted} khớp={sanity_sizes_ok} | "
          f"ARI {km_row['ari_full_vs_frozen']} khớp={sanity_ari_ok}")
    print(f"deconfound ARI(refit, gốc): đầy đủ "
          f"{refit_row['ari_full_vs_frozen']}, non-noise "
          f"{refit_row['ari_nonnoise_vs_frozen']}")
    print(f"mốc silhouette (đóng băng, non-noise, z-trong-năm): "
          f"{bench['silhouette']}")
    print(f"winners theo ngưỡng chốt trước: "
          f"{[r['method'] for r in winners] if winners else 'KHÔNG'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
