"""Phân tích STING chiều cao: lưới thích nghi quantile, khai phá subspace CLIQUE và thang thưa lưới.

Các lớp và hàm dùng chung được tách khỏi `src/sting.py` để giữ nguyên cấu hình đóng băng 2D,
đồng thời bảo đảm mọi biên độ chia ô quantile hoặc khai phá không gian con chỉ học trên tập train.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.metrics import silhouette_score

from src.sting import STING, _MAX_GRID_CELLS


def _validate_matrix(X: np.ndarray, name: str = "X") -> np.ndarray:
    arr = np.asarray(X, dtype=float)
    if arr.ndim != 2 or arr.shape[0] == 0 or arr.shape[1] == 0:
        raise ValueError(f"{name} phải là mảng 2 chiều (n_samples, n_dims) không rỗng")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} chứa NaN/inf; cần lọc trước khi gọi fit/transform")
    return arr


@dataclass(frozen=True)
class QuantileWarper:
    """Ánh xạ từng trục từ không gian gốc về thứ hạng tích lũy thực nghiệm [0, 1] theo tập train."""

    train_min: np.ndarray
    train_max: np.ndarray
    sorted_columns: tuple[np.ndarray, ...]

    @classmethod
    def fit(cls, X: np.ndarray) -> QuantileWarper:
        arr = _validate_matrix(X, "X")
        train_min = arr.min(axis=0).copy()
        train_max = arr.max(axis=0).copy()
        cols = tuple(np.sort(arr[:, j]).copy() for j in range(arr.shape[1]))
        return cls(train_min=train_min, train_max=train_max, sorted_columns=cols)

    def in_support(self, X: np.ndarray) -> np.ndarray:
        arr = _validate_matrix(X, "X")
        if arr.shape[1] != len(self.sorted_columns):
            raise ValueError(
                f"số chiều X={arr.shape[1]} khác lúc fit ({len(self.sorted_columns)})"
            )
        return np.all((arr >= self.train_min) & (arr <= self.train_max), axis=1)

    def transform(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Biến đổi X sang tọa độ quantile và trả về kèm mặt nạ trong miền hỗ trợ train."""
        arr = _validate_matrix(X, "X")
        if arr.shape[1] != len(self.sorted_columns):
            raise ValueError(
                f"số chiều X={arr.shape[1]} khác lúc fit ({len(self.sorted_columns)})"
            )
        support = self.in_support(arr)
        out = np.empty_like(arr, dtype=float)
        for j, col_sorted in enumerate(self.sorted_columns):
            n = len(col_sorted)
            left = np.searchsorted(col_sorted, arr[:, j], side="left")
            right = np.searchsorted(col_sorted, arr[:, j], side="right")
            out[:, j] = (left + right) / (2.0 * n)
        return out, support


class QuantileSTING:
    """STING trên không gian chia ô quantile thích nghi học hoàn toàn từ tập train.

    Khi ``min_count=None`` và ``density_multiplier`` được đặt, ngưỡng ô dày được quy đổi
    tỷ lệ với mật độ kỳ vọng dưới phân bố biên đồng nhất: ``ceil(multiplier * n / (factor**level)**d)``.
    """

    def __init__(
        self,
        n_levels: int = 3,
        factor: int = 2,
        min_count: int | None = None,
        density_multiplier: float | None = None,
        density_level: int | None = None,
    ) -> None:
        if n_levels < 1 or factor < 2:
            raise ValueError("n_levels >= 1 và factor >= 2")
        if min_count is not None and min_count < 1:
            raise ValueError("min_count phải >= 1")
        if density_multiplier is not None and density_multiplier <= 0:
            raise ValueError("density_multiplier phải > 0")
        self.n_levels = int(n_levels)
        self.factor = int(factor)
        self.min_count = None if min_count is None else int(min_count)
        self.density_multiplier = (
            None if density_multiplier is None else float(density_multiplier)
        )
        self.density_level = density_level

    def fit(self, X: np.ndarray) -> QuantileSTING:
        arr = _validate_matrix(X, "X")
        n, d = arr.shape
        self.n_samples_, self.n_dims_ = n, d
        self.warper_ = QuantileWarper.fit(arr)
        warped, _ = self.warper_.transform(arr)
        self.warped_train_ = warped

        target_level = (
            self.n_levels - 1 if self.density_level is None else int(self.density_level)
        )
        if not (0 <= target_level < self.n_levels):
            raise ValueError(
                f"density_level phải thuộc [0, {self.n_levels - 1}], nhận {target_level}"
            )
        res = self.factor ** target_level
        expected = float(n) / float(res ** d)
        self.expected_count_ = expected

        if self.min_count is not None:
            effective_mc = self.min_count
        elif self.density_multiplier is not None:
            effective_mc = max(3, int(np.ceil(self.density_multiplier * expected)))
        else:
            effective_mc = max(1, int(round(0.02 * n)))
        self.effective_min_count_ = effective_mc

        self.sting_ = STING(
            n_levels=self.n_levels,
            factor=self.factor,
            min_count=effective_mc,
        ).fit(warped)
        return self

    def cluster(self, level: int | None = None, connectivity: int = 1) -> np.ndarray:
        if not hasattr(self, "sting_"):
            raise RuntimeError("Hãy gọi fit(X) trước khi cluster()")
        labels = self.sting_.cluster(level=level, connectivity=connectivity)
        self.n_clusters_ = int(self.sting_.n_clusters_)
        self.cluster_level_ = int(self.sting_.cluster_level_)
        return labels

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not hasattr(self, "sting_") or not hasattr(self, "n_clusters_"):
            raise RuntimeError("Hãy gọi fit(X) và cluster() trước khi predict()")
        arr = _validate_matrix(X, "X")
        warped, support = self.warper_.transform(arr)
        preds = self.sting_.predict(warped)
        preds = preds.copy()
        preds[~support] = -1
        return preds


class SubspaceCLIQUE:
    """Thuật toán CLIQUE Apriori từ dưới lên phát hiện các đơn vị dày trong subspace k chiều."""

    def __init__(
        self,
        n_bins: int = 4,
        tau: float = 0.05,
        adaptive: bool = False,
        min_points: int | None = None,
        max_dim: int | None = None,
    ) -> None:
        if n_bins < 2:
            raise ValueError("n_bins phải >= 2")
        if not (0.0 < tau <= 1.0):
            raise ValueError("tau phải thuộc (0, 1]")
        if min_points is not None and min_points < 1:
            raise ValueError("min_points phải >= 1")
        if max_dim is not None and max_dim < 1:
            raise ValueError("max_dim phải >= 1")
        self.n_bins = int(n_bins)
        self.tau = float(tau)
        self.adaptive = bool(adaptive)
        self.min_points = None if min_points is None else int(min_points)
        self.max_dim = None if max_dim is None else int(max_dim)

    def _compute_edges(self, col: np.ndarray) -> tuple[float, float, np.ndarray]:
        lo, hi = float(col.min()), float(col.max())
        if self.adaptive:
            edges = np.quantile(col, np.linspace(0.0, 1.0, self.n_bins + 1))
            for idx in range(1, len(edges)):
                if edges[idx] <= edges[idx - 1]:
                    edges[idx] = edges[idx - 1] + 1e-9
        else:
            if hi <= lo:
                edges = np.linspace(lo, lo + 1.0, self.n_bins + 1)
            else:
                edges = np.linspace(lo, hi, self.n_bins + 1)
        return lo, hi, edges

    def _digitize(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        n, d = X.shape
        bins = np.empty((n, d), dtype=int)
        support = np.ones((n, d), dtype=bool)
        for j in range(d):
            lo, hi, edges = self.edges_[j]
            col = X[:, j]
            support[:, j] = (col >= lo) & (col <= hi)
            bins[:, j] = np.clip(np.digitize(col, edges[1:-1], right=False), 0, self.n_bins - 1)
        return bins, support

    def fit(self, X: np.ndarray) -> SubspaceCLIQUE:
        arr = _validate_matrix(X, "X")
        n, d = arr.shape
        self.n_samples_, self.n_dims_ = n, d
        self.train_X_ = arr.copy()
        self.min_points_ = (
            self.min_points if self.min_points is not None else max(2, int(np.ceil(self.tau * n)))
        )
        self.edges_ = tuple(self._compute_edges(arr[:, j]) for j in range(d))
        bins, _ = self._digitize(arr)
        self.train_bins_ = bins

        level1: dict[tuple[tuple[int, ...], tuple[int, ...]], frozenset[int]] = {}
        for j in range(d):
            for b in range(self.n_bins):
                pts = np.flatnonzero(bins[:, j] == b)
                if len(pts) >= self.min_points_:
                    level1[((j,), (b,))] = frozenset(pts.tolist())

        levels: dict[int, dict[tuple[tuple[int, ...], tuple[int, ...]], frozenset[int]]] = {
            1: level1
        }
        dim_cap = d if self.max_dim is None else min(d, self.max_dim)
        k = 1
        while k < dim_cap and levels[k]:
            by_dims: dict[tuple[int, ...], dict[tuple[int, ...], frozenset[int]]] = {}
            for (dims, coords), pts in levels[k].items():
                by_dims.setdefault(dims, {})[coords] = pts
            dims_list = sorted(by_dims.keys())
            next_level: dict[tuple[tuple[int, ...], tuple[int, ...]], frozenset[int]] = {}
            seen_dims: set[tuple[int, ...]] = set()
            for idx_a in range(len(dims_list)):
                d1 = dims_list[idx_a]
                for idx_b in range(idx_a + 1, len(dims_list)):
                    d2 = dims_list[idx_b]
                    if d1[:-1] != d2[:-1]:
                        continue
                    new_dims = d1 + (d2[-1],)
                    if new_dims in seen_dims:
                        continue
                    seen_dims.add(new_dims)
                    sub_dims = tuple(new_dims[:m] + new_dims[m + 1 :] for m in range(k + 1))
                    if any(sd not in by_dims for sd in sub_dims):
                        continue
                    for c1, pts1 in by_dims[d1].items():
                        for c2, pts2 in by_dims[d2].items():
                            if c1[:-1] != c2[:-1]:
                                continue
                            new_coords = c1 + (c2[-1],)
                            if not all(
                                (new_coords[:m] + new_coords[m + 1 :]) in by_dims[sub_dims[m]]
                                for m in range(k + 1)
                            ):
                                continue
                            inter = pts1 & pts2
                            if len(inter) >= self.min_points_:
                                next_level[(new_dims, new_coords)] = inter
            if not next_level:
                break
            k += 1
            levels[k] = next_level

        self.levels_ = levels
        self.dense_by_dims_: dict[tuple[int, ...], dict[tuple[int, ...], frozenset[int]]] = {}
        for units in levels.values():
            for (dims, coords), pts in units.items():
                self.dense_by_dims_.setdefault(dims, {})[coords] = pts
        return self

    def discovered_subspaces(self, min_dim: int = 2) -> list[tuple[int, ...]]:
        if not hasattr(self, "dense_by_dims_"):
            raise RuntimeError("Hãy gọi fit(X) trước khi đọc subspaces")
        return sorted(
            [dims for dims in self.dense_by_dims_ if len(dims) >= min_dim],
            key=lambda item: (len(item), item),
        )

    def extract_subspace(
        self,
        dims: tuple[int, ...] | Iterable[int],
        X_raw: np.ndarray | None = None,
    ) -> dict:
        """Gom cụm các đơn vị dày kề mặt trong không gian con ``dims``."""
        if not hasattr(self, "dense_by_dims_"):
            raise RuntimeError("Hãy gọi fit(X) trước khi extract_subspace()")
        dims_t = tuple(int(v) for v in dims)
        cmap = self.dense_by_dims_.get(dims_t, {})
        n = self.n_samples_
        labels = np.full(n, -1, dtype=int)
        if not cmap:
            return {
                "dims": dims_t,
                "k_dim": len(dims_t),
                "n_dense_units": 0,
                "n_clusters": 0,
                "labels": labels,
                "coverage": 0.0,
                "noise_ratio": 1.0,
                "cluster_sizes": [],
                "silhouette": float("nan"),
                "coord_to_cluster": {},
            }

        unvisited = set(cmap.keys())
        components: list[list[tuple[int, ...]]] = []
        dim_k = len(dims_t)
        while unvisited:
            start = min(unvisited)
            unvisited.remove(start)
            queue = deque([start])
            comp = [start]
            while queue:
                cur = queue.popleft()
                for ax in range(dim_k):
                    for step in (-1, 1):
                        nb = list(cur)
                        nb[ax] += step
                        nb_t = tuple(nb)
                        if nb_t in unvisited:
                            unvisited.remove(nb_t)
                            queue.append(nb_t)
                            comp.append(nb_t)
            components.append(comp)

        comp_scored = sorted(
            [(sum(len(cmap[c]) for c in comp), comp) for comp in components],
            key=lambda item: (-item[0], min(item[1])),
        )
        coord_to_cluster: dict[tuple[int, ...], int] = {}
        for cid, (_, comp) in enumerate(comp_scored):
            for c in comp:
                coord_to_cluster[c] = cid
                for pt_idx in cmap[c]:
                    labels[pt_idx] = cid

        sizes = [int((labels == cid).sum()) for cid in range(len(comp_scored))]
        mask = labels != -1
        cov = float(mask.mean())
        ncl = len(comp_scored)
        X_eval = self.train_X_ if X_raw is None else _validate_matrix(X_raw, "X_raw")
        if ncl >= 2 and int(mask.sum()) > ncl:
            sil = float(silhouette_score(X_eval[mask][:, list(dims_t)], labels[mask]))
        else:
            sil = float("nan")
        return {
            "dims": dims_t,
            "k_dim": dim_k,
            "n_dense_units": len(cmap),
            "n_clusters": ncl,
            "labels": labels,
            "coverage": cov,
            "noise_ratio": 1.0 - cov,
            "cluster_sizes": sizes,
            "silhouette": sil,
            "coord_to_cluster": coord_to_cluster,
        }

    def predict_subspace(
        self,
        dims: tuple[int, ...] | Iterable[int],
        X_new: np.ndarray,
    ) -> np.ndarray:
        """Gán nhãn cho điểm mới trong subspace ``dims`` theo đơn vị dày đã học từ train."""
        info = self.extract_subspace(dims)
        dims_t = info["dims"]
        arr = _validate_matrix(X_new, "X_new")
        if arr.shape[1] != self.n_dims_:
            raise ValueError(f"số chiều X_new={arr.shape[1]} khác lúc fit ({self.n_dims_})")
        bins, support = self._digitize(arr)
        sub_ok = np.all(support[:, list(dims_t)], axis=1)
        c2lbl = info["coord_to_cluster"]
        out = np.full(len(arr), -1, dtype=int)
        for i in range(len(arr)):
            if not sub_ok[i]:
                continue
            coord = tuple(int(bins[i, j]) for j in dims_t)
            if coord in c2lbl:
                out[i] = c2lbl[coord]
        return out


def high_dim_sparsity_grid(
    X: np.ndarray,
    dims_list: Iterable[int],
    n_levels: int,
    factor: int,
    min_count: int,
    level: int,
    max_leaf_cells: int = 10_000_000,
) -> list[dict]:
    """Đo độ thưa lưới STING khi tăng dần số chiều d với cấu hình (n_levels, factor, min_count, level)."""
    arr = _validate_matrix(X, "X")
    max_d = arr.shape[1]
    res = int(factor ** level)
    max_res = int(factor ** (n_levels - 1))
    rows: list[dict] = []
    for d in dims_list:
        d_int = int(d)
        if not (1 <= d_int <= max_d):
            raise ValueError(f"d={d_int} vượt ngoài phạm vi [1, {max_d}]")
        leaf_cells = max_res ** d_int
        level_cells = res ** d_int
        if leaf_cells > min(max_leaf_cells, _MAX_GRID_CELLS):
            rows.append(
                {
                    "d": d_int,
                    "res_per_axis": res,
                    "grid_cells_at_level": int(level_cells),
                    "leaf_cells": int(leaf_cells),
                    "skipped": True,
                    "active_cells": np.nan,
                    "dense_cells": np.nan,
                    "active_cell_ratio": np.nan,
                    "k": np.nan,
                    "noise_ratio": np.nan,
                    "silhouette": np.nan,
                }
            )
            continue
        sub = arr[:, :d_int]
        model = STING(n_levels=n_levels, factor=factor, min_count=min_count).fit(sub)
        labels = model.cluster(level=level, connectivity=1)
        cells = model.cells_[level]
        active = int(sum(1 for cell in cells.values() if cell.count > 0))
        dense = int(len(model.label_of_))
        mask = labels != -1
        if model.n_clusters_ >= 2 and int(mask.sum()) > model.n_clusters_:
            sil = float(silhouette_score(sub[mask], labels[mask]))
        else:
            sil = float("nan")
        rows.append(
            {
                "d": d_int,
                "res_per_axis": res,
                "grid_cells_at_level": int(level_cells),
                "leaf_cells": int(leaf_cells),
                "skipped": False,
                "active_cells": active,
                "dense_cells": dense,
                "active_cell_ratio": active / float(level_cells),
                "k": int(model.n_clusters_),
                "noise_ratio": float((labels == -1).mean()),
                "silhouette": sil,
            }
        )
    return rows


__all__ = [
    "QuantileSTING",
    "QuantileWarper",
    "SubspaceCLIQUE",
    "high_dim_sparsity_grid",
]
