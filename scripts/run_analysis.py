"""Phase 5 — Phân tích cuối kỳ (STING vs baselines, robustness, bản đồ, evolution).

Tái lập, seed cố định. Chạy từ thư mục gốc dự án:
    python scripts/run_analysis.py

Đầu ra:
  results/cluster_labels.csv   — STING per-year (phương pháp riêng từng năm)
  results/metrics.csv          — STING vs k-means vs DBSCAN (noise tách riêng)
  results/per_year.csv         — k và noise ratio theo năm (trung thực: đa số k=1)
  results/robustness.csv       — PCA d1–d6 toàn panel + nhánh 8 chiều 2018–2024
  results/figs/evolution.png   — heatmap dịch chuyển cụm 2011–2024 (lưới toàn cục)
  results/figs/map_2020.png, map_2024.png — bản đồ centroid tô màu theo cụm
  results/analysis_summary.md  — tóm tắt số liệu cho báo cáo/slide
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sting import STING  # noqa: E402
from papi_pred_common import ROOT, load_config, load_panel  # noqa: E402
from fig_style import (  # noqa: E402
    AX_KINH_DO,
    AX_VI_DO,
    CLUSTER_COLORS,
    CLUSTER_LABELS,
    PALETTE,
    add_source,
    apply_style,
    new_fig,
    save_png,
)

# Dòng nguồn: tên nguồn + ngày tải lấy từ PROVENANCE.md của từng dữ liệu
# (KHÔNG phải ngày render hình).
PAPI_SOURCE = "PAPI — CECODES, VFF-CRT, RTA & UNDP"
PAPI_RETRIEVED = "2026-11-03"  # data/raw/papi/PROVENANCE.md
CENTROID_SOURCE = "Le et al. — Mendeley Data, DOI 10.17632/wbk42j9wc8.1 (CC BY 4.0)"
CENTROID_RETRIEVED = "2026-11-03"  # data/raw/mendeley/PROVENANCE.md

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FIGS = ROOT / "results" / "figs"
RES = ROOT / "results"
SEED = 42


def metric_row(scope, method, k, noise, sil, db, ch, ari, note):
    return {
        "scope": scope, "method": method, "k": k, "noise_ratio": round(noise, 3),
        "silhouette": (round(sil, 3) if sil is not None else None),
        "davies_bouldin": (round(db, 3) if db is not None else None),
        "calinski_harabasz": (round(ch, 1) if ch is not None else None),
        "ari_vs_sting": (round(ari, 3) if ari is not None else None),
        "note": note,
    }


def safe_metrics(X, labels):
    """Metric hình học trên các điểm THUỘC CỤM (loại −1); None nếu <2 cụm."""
    mask = labels >= 0
    k = len(set(labels[mask]))
    if k < 2:
        return None, None, None
    sil = silhouette_score(X[mask], labels[mask])
    db = davies_bouldin_score(X[mask], labels[mask])
    ch = calinski_harabasz_score(X[mask], labels[mask])
    return sil, db, ch


def label_noise_points(ax, fig, sub, nmap, fontsize: float = 5.5) -> None:
    """Đặt nhãn các điểm nhiễu trên bản đồ, chọn vị trí ít chồng chéo nhất.

    Lớp trình bày thuần: với mỗi điểm nhiễu thử 8 ứng viên vị trí quanh
    marker, chấm điểm theo khoảng cách gần nhất tới marker khác và tới nhãn
    đã đặt (tính trong hệ toạ độ point nên bất biến theo DPI), ưu tiên ứng
    viên sớm hơn khi bằng điểm. Không đổi dữ liệu hay thứ tự điểm.
    """
    k = fig.dpi / 72.0  # px hiển thị trên 1 point
    xy = sub[["longitude", "latitude"]].to_numpy()
    centers = ax.transData.transform(xy) / k  # -> point
    r_mark = float(np.sqrt(110 / np.pi)) + 0.6  # bán kính marker (point)
    bb = ax.get_window_extent()
    ax_bb = (bb.x0 / k, bb.y0 / k, bb.x1 / k, bb.y1 / k)
    # 8 ứng viên (dx, dy, ha, va) theo point: phải, trái, trên, dưới, 4 chéo.
    cands = (
        (8, -2, "left", "center"), (-8, -2, "right", "center"),
        (0, 8, "center", "bottom"), (0, -10, "center", "top"),
        (7, 6, "left", "bottom"), (-7, 6, "right", "bottom"),
        (7, -11, "left", "top"), (-7, -11, "right", "top"),
    )
    placed = []  # hộp (x0, x1, y0, y1) các nhãn đã đặt, theo point

    def rect(cx, cy, cand, w, h):
        dx, dy, ha, va = cand
        if ha == "left":
            x0, x1 = cx + dx, cx + dx + w
        elif ha == "right":
            x0, x1 = cx + dx - w, cx + dx
        else:
            x0, x1 = cx + dx - w / 2, cx + dx + w / 2
        if va == "bottom":
            y0, y1 = cy + dy, cy + dy + h
        elif va == "top":
            y0, y1 = cy + dy - h, cy + dy
        else:
            y0, y1 = cy + dy - h / 2, cy + dy + h / 2
        return x0, x1, y0, y1

    def gap_rect(a, b):
        dx = max(b[0] - a[1], a[0] - b[1], 0.0)
        dy = max(b[2] - a[3], a[2] - b[3], 0.0)
        return float(np.hypot(dx, dy))

    def gap_point(r, px, py):
        dx = max(r[0] - px, px - r[1], 0.0)
        dy = max(r[2] - py, py - r[3], 0.0)
        return float(np.hypot(dx, dy))

    lon = sub.longitude.to_numpy()
    lat = sub.latitude.to_numpy()
    clu = sub.cluster.to_numpy()
    code = sub.province_code.to_numpy()
    for i in sorted(range(len(sub)), key=lambda j: (-lat[j], lon[j])):
        if int(clu[i]) != -1:
            continue
        text = nmap.get(int(code[i]), "")
        if not text:
            continue
        w = 0.62 * fontsize * len(text)  # ước lượng bề rộng chữ (point)
        h = 1.7 * fontsize  # đủ chứa dấu tiếng Việt chồng (ế, ị, ữ)
        best, best_score = None, -np.inf
        for rank, cand in enumerate(cands):
            r = rect(centers[i, 0], centers[i, 1], cand, w, h)
            out = (r[0] < ax_bb[0] - 2 or r[1] > ax_bb[2] + 2
                   or r[2] < ax_bb[1] - 2 or r[3] > ax_bb[3] + 2)
            others = (gap_point(r, *centers[j]) - r_mark
                      for j in range(len(centers)) if j != i)
            gap_l = min((gap_rect(r, p) for p in placed), default=99.0)
            # chấm điểm theo khoảng cách hẹp nhất (marker hoặc nhãn đã đặt)
            score = min(min(others), gap_l) - (50.0 if out else 0.0) \
                - 0.01 * rank
            if score > best_score:
                best, best_score = cand, score
        ax.annotate(text, (lon[i], lat[i]), fontsize=fontsize,
                    xytext=(best[0], best[1]), textcoords="offset points",
                    ha=best[2], va=best[3], alpha=0.8)
        placed.append(rect(centers[i, 0], centers[i, 1], best, w, h))


def main() -> int:
    cfg = load_config()
    feats = cfg["features"]
    df = load_panel()
    years = sorted(df.year.unique())
    print(f"features đóng băng: {feats} | năm {years[0]}–{years[-1]}")

    # ================================================================== #
    # 1) Per-year STING (fit riêng từng năm; lưới thô vì mẫu nhỏ)
    # ================================================================== #
    labels_rows = []
    per_year_rows = []
    for y in years:
        sub = df[df.year == y].dropna(subset=feats)
        X = StandardScaler().fit_transform(sub[feats])
        m = STING(n_levels=2, factor=3, min_count=3).fit(X)  # lưới 3×3, mc=3
        lab = m.cluster(level=1, connectivity=1)
        k = m.n_clusters_
        noise = float((lab == -1).mean())
        per_year_rows.append({"year": y, "n": len(sub), "k": k,
                              "noise_ratio": round(noise, 3),
                              "cluster_sizes": str(sorted(
                                  [int((lab == c).sum()) for c in range(k)], reverse=True))})
        for (_, r), c in zip(sub.iterrows(), lab):
            labels_rows.append({"province_code": int(r["province_code"]),
                                "province_vi": r["province_vi"],
                                "year": int(y), "sting_label": int(c)})
    pd.DataFrame(labels_rows).to_csv(RES / "cluster_labels.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(per_year_rows).to_csv(RES / "per_year.csv", index=False, encoding="utf-8-sig")
    print("1) per-year STING: xong ->", RES / "cluster_labels.csv")

    # ================================================================== #
    # 2) Pooled metrics: frozen STING vs k-means vs DBSCAN
    # ================================================================== #
    ptr = df[df.year <= 2023].dropna(subset=feats)
    X = StandardScaler().fit(ptr[feats]).transform(ptr[feats])
    m = STING(n_levels=cfg["sting"]["n_levels"], factor=cfg["sting"]["factor"],
              min_count=cfg["sting"]["min_count"]).fit(X)
    lab_sting = m.cluster(level=cfg["sting"]["cluster_level"],
                          connectivity=cfg["sting"]["connectivity"])
    sizes = sorted([int((lab_sting == c).sum()) for c in range(m.n_clusters_)], reverse=True)
    print(f"2) frozen STING pooled: k={m.n_clusters_} sizes={sizes} noise={(lab_sting == -1).mean():.0%}")
    rows = []
    sil, db, ch = safe_metrics(X, lab_sting)
    rows.append(metric_row("pooled 2011-2023", "STING (frozen)", m.n_clusters_,
                           (lab_sting == -1).mean(), sil, db, ch, None,
                           "k=3: [629,16,5]; noise tách khỏi metric hình học"))

    for k in (2, 3, 4, 5):
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(X)
        sil_k = silhouette_score(X, km.labels_)
        db_k = davies_bouldin_score(X, km.labels_)
        ch_k = calinski_harabasz_score(X, km.labels_)
        rows.append(metric_row("pooled 2011-2023", f"k-means k={k}", k, 0.0, sil_k, db_k, ch_k,
                               adjusted_rand_score(lab_sting, km.labels_), "tất cả điểm được gán cụm"))

    for eps in (0.2, 0.4, 0.6, 0.8, 1.0):
        dbd = DBSCAN(eps=eps, min_samples=5).fit(X)
        lbl = dbd.labels_
        ncl = len(set(lbl)) - (1 if -1 in lbl else 0)
        noise = float((lbl == -1).mean())
        sil_e, db_e, ch_e = safe_metrics(X, lbl)
        rows.append(metric_row("pooled 2011-2023", f"DBSCAN eps={eps}", ncl, noise,
                               sil_e, db_e, ch_e,
                               adjusted_rand_score(lab_sting, lbl),
                               "metric n/a khi <2 cụm" if ncl < 2 else ""))
    pd.DataFrame(rows).to_csv(RES / "metrics.csv", index=False, encoding="utf-8-sig")
    print("   xong ->", RES / "metrics.csv")

    # ================================================================== #
    # 3) Robustness: PCA(d1–d6) toàn panel + 8 chiều 2018–2024
    # ================================================================== #
    robust = []
    X6 = df[[f"d{i}" for i in range(1, 7)]].copy()
    # z trong từng năm (khử bước nhảy do đổi thang đo/phương pháp theo năm)
    X6z = X6.groupby(df["year"]).transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    ok = X6z.notna().all(axis=1)
    pca = PCA(n_components=2, random_state=SEED).fit(X6z[ok])
    var = pca.explained_variance_ratio_
    print(f"3a) PCA d1–d6: var = {var.round(3)} (tổng {var.sum():.0%})")
    Zp = pca.transform(X6z[ok])
    m6 = STING(n_levels=3, factor=3, min_count=5).fit(Zp)
    lab6 = m6.cluster(level=2, connectivity=1)
    sil6, db6, ch6 = safe_metrics(Zp, lab6)

    # ARI giữa 2D frozen và PCA-6D trên giao các dòng (province_code, year) có mặt cả hai
    d2d = ptr.reset_index()[["province_code", "year"]].copy()
    d2d["frozen"] = lab_sting
    d6 = df.loc[ok.index[ok.to_numpy()]][["province_code", "year"]].copy().reset_index(drop=True)
    d6["pca6"] = lab6
    inter = d2d.merge(d6, on=["province_code", "year"])
    ari6 = adjusted_rand_score(inter.frozen, inter.pca6) if len(inter) else float("nan")
    print(f"   giao {len(inter)} điểm chung để so ARI vs 2D")
    robust.append({"branch": "PCA(2) d1–d6, within-year z, pooled", "n": int(ok.sum()),
                   "explained_var_total": round(float(var.sum()), 3),
                   "k": m6.n_clusters_, "noise_ratio": round(float((lab6 == -1).mean()), 3),
                   "silhouette": sil6, "db": db6, "ch": ch6, "ari_vs_2d": round(float(ari6), 3),
                   "verdict": "có cấu trúc" if m6.n_clusters_ >= 2 else "không nhận diện"})

    X8 = df[df.year >= 2018][[f"d{i}" for i in range(1, 9)]].dropna()
    Z8 = X8.groupby(df[df.year >= 2018]["year"].loc[X8.index]).transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    Z8v = Z8.to_numpy()

    def run_8dim(fit_over, level):
        """Một nhánh 8 chiều; OFAT: ``fit_over``/``level`` đổi MỘT tham số so với gốc.

        Gốc (8a) = n_levels=3, factor=2, min_count=10, cluster(level=1).
        Metric hình học tính ngay tại đây — k>=2 thì có số, k<2 thì None.
        """
        params = {"n_levels": 3, "factor": 2, "min_count": 10}  # nhánh gốc 8a
        params.update(fit_over)
        mm = STING(**params).fit(Z8v)
        ll = mm.cluster(level=level, connectivity=1)
        sil, db, ch = safe_metrics(Z8v, ll)
        noise = float((ll == -1).mean())
        row = {"n": len(X8), "explained_var_total": None, "k": mm.n_clusters_,
               "noise_ratio": round(noise, 3), "silhouette": sil, "db": db, "ch": ch,
               "ari_vs_2d": None,
               "verdict": "không nhận diện" if mm.n_clusters_ < 2 or noise > 0.5
               else "có cấu trúc"}
        return mm, ll, row

    m8a, lab8a, row8a = run_8dim({}, 1)
    robust.append({"branch": "8 chiều 2018–2024, within-year z, L=3 f=2 mc=10 lv=1 (gốc OFAT)",
                   **row8a})
    print(f"3b) 8 chiều 2018–2024 (n={len(X8)}): gốc mc=10/lv=1 k={m8a.n_clusters_} "
          f"noise={(lab8a == -1).mean():.0%}")
    ofat_parts = []
    for tag, rest, fit_over, lv in (
        ("f=3", "L=3 mc=10 lv=1", {"factor": 3}, 1),
        ("mc=2", "L=3 f=2 lv=1", {"min_count": 2}, 1),
        ("lv=2", "L=3 f=2 mc=10", {}, 2),
    ):
        _, _, row = run_8dim(fit_over, lv)
        robust.append({"branch": f"8 chiều 2018–2024, within-year z, OFAT {tag} "
                                 f"(còn như gốc: {rest})", **row})
        ofat_parts.append(f"{tag}: k={row['k']}, noise={row['noise_ratio']} → {row['verdict']}")
    print("   OFAT:", " | ".join(ofat_parts))
    pd.DataFrame(robust).to_csv(RES / "robustness.csv", index=False, encoding="utf-8-sig")
    print("   xong ->", RES / "robustness.csv")

    # ================================================================== #
    # 4) Evolution heatmap (nhãn từ lưới TOÀN CỤC — so sánh được các năm)
    # ================================================================== #
    import matplotlib

    matplotlib.use("Agg")
    apply_style()
    import matplotlib.pyplot as plt

    pred = pd.read_csv(RES / "predict_all_years.csv")
    piv = pred.pivot(index="province_vi", columns="year", values="pred_cluster")
    order = piv.sort_values([2024, 2023], na_position="last").index
    piv = piv.loc[order]
    fig, ax = new_fig(target=None, figsize=(11, 17))
    cmap = plt.matplotlib.colors.ListedColormap(
        [PALETTE["gray"], PALETTE["blue"], PALETTE["orange"], PALETTE["green"]]
    )
    cmap.set_bad("white")
    bounds = [-1.5, -0.5, 0.5, 1.5, 2.5]
    norm = plt.matplotlib.colors.BoundaryNorm(bounds, cmap.N)
    ax.imshow(piv.to_numpy(), aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels(list(piv.columns), rotation=0)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(list(piv.index), fontsize=6)
    ax.set_xlabel("Năm")
    ax.set_ylabel("Tỉnh/Thành phố")
    ax.set_title("Dịch chuyển cụm STING 2011–2024 (lưới toàn cục; xám = nhiễu/–1)")
    cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, pad=0.01)
    cbar.set_ticks([-1, 0, 1, 2])
    cbar.set_ticklabels([CLUSTER_LABELS[c] for c in (-1, 0, 1, 2)])
    cbar.set_label("Cụm STING")
    add_source(fig, PAPI_SOURCE, retrieved=PAPI_RETRIEVED)
    # Ô trắng trong lưới là (tỉnh, năm) không có dự đoán — thiếu dữ liệu đầu
    # vào năm đó (không nằm trong predict_all_years.csv); chú giải rõ để
    # người đọc không phải đoán.
    fig.text(0.01, 0.032, "Ô trắng = không có dự đoán (thiếu dữ liệu năm đó)",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save_png(fig, FIGS / "evolution.png", dpi=200)
    plt.close(fig)
    print("4) evolution ->", FIGS / "evolution.png")

    # ================================================================== #
    # 5) Bản đồ centroid tô màu theo cụm (2020, 2024)
    # ================================================================== #
    cent = pd.read_csv(ROOT / "data" / "raw" / "mendeley" / "Replication_package" / "data"
                       / "centroids_63_naturalearth.csv")
    cent["province_code"] = cent["province_code"].astype(int)
    colors = CLUSTER_COLORS  # {-1: xám nhiễu, 0: xanh dương, 1: cam, 2: xanh lá}
    for yr in (2020, 2024):
        labels = dict(zip(pred[pred.year == yr].province_code, pred[pred.year == yr].pred_cluster))
        sub = cent[cent.province_code.isin(labels)].copy()
        sub["cluster"] = sub.province_code.map(labels)
        fig, ax = new_fig(target=None, figsize=(6.2, 9.5))
        for c in sorted(sub.cluster.unique()):
            m = sub.cluster == c
            ax.scatter(sub.longitude[m], sub.latitude[m], s=110,
                       c=colors.get(int(c), "#937860"), edgecolors="black", linewidths=0.6,
                       label=CLUSTER_LABELS.get(int(c), f"cụm {c}"))
        prow = df[df.year == yr][["province_code", "province_vi"]]
        nmap = dict(zip(prow.province_code, prow.province_vi))
        ax.set_title(f"Cụm STING — {yr}")
        ax.legend(loc="lower left", fontsize=7)
        # Đơn vị độ bắt buộc với trục toạ độ địa lý.
        ax.set_xlabel(f"{AX_KINH_DO} (°)")
        ax.set_ylabel(f"{AX_VI_DO} (°)")
        ax.grid(alpha=0.25)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        add_source(fig, f"{PAPI_SOURCE}; toạ độ centroid: {CENTROID_SOURCE}",
                   retrieved=PAPI_RETRIEVED, fontsize=9)
        # Nhãn tỉnh nhiễu: chọn vị trí ít chồng chéo nhất sau khi bố cục chốt
        # (thử 8 hướng quanh marker, chấm điểm theo khoảng cách tới marker/
        # nhãn khác) — chỉ lớp trình bày, không đổi dữ liệu.
        fig.canvas.draw()
        label_noise_points(ax, fig, sub, nmap, fontsize=5.5)
        save_png(fig, FIGS / f"map_{yr}.png", dpi=300)
        plt.close(fig)
        print(f"5) map {yr} ->", FIGS / f"map_{yr}.png")

    # ================================================================== #
    # 6) Tóm tắt
    # ================================================================== #
    lines = []
    lines.append("# Phân tích cuối kỳ — tóm tắt số liệu\n")
    lines.append("## 1) STING theo từng năm (lưới thô 3×3, mc=3; trong-năm z)\n")
    lines.append(pd.DataFrame(per_year_rows).to_markdown(index=False))
    lines.append("\n## 2) Pooled 2011–2023 (frozen): STING vs baselines\n")
    met = pd.read_csv(RES / "metrics.csv")
    lines.append(met.to_markdown(index=False))
    lines.append("\n## 3) Robustness đa chỉ tiêu\n")
    lines.append(pd.DataFrame(robust).to_markdown(index=False))
    lines.append(
        "\n## Ghi chú trung thực\n"
        "- Dữ liệu PAPI cấp tỉnh/năm **rất đồng nhất**: STING per-year đa số cho 1 vùng dày; "
        "cấu trúc tách biệt chỉ xuất hiện ở hai cụm ngoại vi nhỏ (ví dụ cụm 16 và 5 điểm, tổng 21, trong pooled).\n"
        "- Metric hình học tính trên điểm thuộc cụm (loại −1); khi k<2 metric = n/a.\n"
        "- ARIt vs k-means thấp (≈0.07–0.17): hai phương pháp phân vùng khác nhau trên dữ liệu gần như một khối.\n"
        "- STING ≈ DBSCAN(eps=0.2) đồng thuận hơn (ARI≈0.65) — cùng họ mật độ-lưới.\n"
        f"- 8 chiều chỉ 2018–2024, OFAT đổi một tham số mỗi lần so với gốc mc=10/lv=1: "
        f"{'; '.join(ofat_parts)}."
    )
    (RES / "analysis_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("6) summary ->", RES / "analysis_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
