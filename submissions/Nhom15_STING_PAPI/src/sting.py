"""STING (STatistical INformation Grid) rút gọn, cài đặt bằng NumPy.

Tham khảo: Wang, Yang & Muntz (1997), "STING: A Statistical Information Grid
Approach to Spatial Data Mining", VLDB.

Lưới phân cấp: mức ``l`` chia mỗi chiều thành ``factor ** l`` đoạn bằng nhau.
Mỗi ô lưu count, mean, std, min, max theo từng chiều. Cụm là thành phần liên
thông của các ô dày (count >= min_count); điểm ở ô không dày nhận nhãn -1.

>>> import numpy as np
>>> from sting import STING
>>> X = np.random.default_rng(0).normal(size=(100, 2))
>>> labels = STING(n_levels=3, factor=4, min_count=5).fit(X).cluster(level=2)
"""
from __future__ import annotations

import itertools
import pickle
import warnings
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from os import PathLike

import numpy as np

__all__ = ["Cell", "STING"]

_MAX_GRID_CELLS = 2**62


@dataclass
class Cell:
    """Một ô lưới tại một mức phân cấp."""

    level: int
    index: tuple[int, ...]
    bounds_min: np.ndarray
    bounds_max: np.ndarray
    count: int = 0
    mean: np.ndarray | None = None
    std: np.ndarray | None = None
    min_: np.ndarray | None = None
    max_: np.ndarray | None = None


class STING:
    """Lưới thống kê phân cấp cho phân cụm nhiều chiều."""

    def __init__(
        self,
        n_levels: int = 4,
        factor: int = 2,
        min_count: int | None = None,
        significance_z: float | None = None,
    ) -> None:
        """``min_count=None`` -> ``max(1, round(0.02 * n))``; ``significance_z=None`` tắt kiểm định z."""
        if n_levels < 1:
            raise ValueError("n_levels phải >= 1")
        if factor < 2:
            raise ValueError("factor phải >= 2")
        if min_count is not None and min_count < 0:
            raise ValueError("min_count phải >= 0")
        self.n_levels = int(n_levels)
        self.factor = int(factor)
        self.min_count = min_count
        self.significance_z = significance_z

    def fit(self, X: np.ndarray) -> STING:
        """Xây lưới và thống kê từng ô; gọi lại cluster() trước predict()."""
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or X.shape[0] == 0:
            raise ValueError("X phải là mảng 2 chiều (n_samples, n_dims) không rỗng")
        if not np.all(np.isfinite(X)):
            raise ValueError("X chứa NaN/inf; xử lý trước khi fit")

        for name in ("label_of_", "n_clusters_", "cluster_level_", "_cell_comp_"):
            self.__dict__.pop(name, None)

        n, d = X.shape
        self.n_samples_, self.n_dims_ = n, d

        lo = X.min(axis=0)
        hi = X.max(axis=0)
        width = hi - lo
        width[width == 0.0] = 1.0
        self.bounds_min_, self.bounds_max_ = lo, np.maximum(hi, lo + width)

        self.min_count_ = (
            int(self.min_count)
            if self.min_count is not None
            else max(1, int(round(0.02 * n)))
        )

        self.cells_: dict[int, dict[tuple[int, ...], Cell]] = {}
        self._point_idx_: dict[int, np.ndarray] = {}
        self._flat_: dict[int, np.ndarray] = {}

        max_res = self.factor ** (self.n_levels - 1)
        grid_cells = max_res ** d
        if max_res > _MAX_GRID_CELLS or grid_cells > _MAX_GRID_CELLS:
            raise ValueError(
                f"lưới quá lớn (res={max_res}, số ô={grid_cells}); "
                f"giảm n_levels, factor hoặc số chiều (giới hạn {_MAX_GRID_CELLS} ô)"
            )

        for level in range(self.n_levels):
            res = self.factor ** level
            idx, flat = self._assign(X, res)
            self._point_idx_[level] = idx
            self._flat_[level] = flat
            self.cells_[level] = self._accumulate(X, flat, res, level)
        return self

    def cluster(self, level: int | None = None, connectivity: int = 1) -> np.ndarray:
        """Nhãn cụm của từng điểm tại mức ``level``; -1 là nhiễu.

        connectivity=1: ô kề mặt; connectivity=số chiều: gồm cả ô kề góc.
        """
        if not hasattr(self, "cells_"):
            raise RuntimeError("Hãy gọi fit(X) trước khi cluster()")
        if level is None:
            level = self.n_levels - 1
        if not (0 <= level < self.n_levels):
            raise ValueError(
                f"level phải thuộc [0, {self.n_levels - 1}], nhận {level}"
            )
        if connectivity < 1:
            raise ValueError(
                "connectivity phải >= 1 (1 = kề mặt/4 hướng; số chiều = kề cả góc/8 hướng)"
            )
        res = self.factor ** level

        dense_set = {
            key
            for key, cell in self.cells_[level].items()
            if self._is_dense(cell, level)
        }
        if self.significance_z is not None and not dense_set:
            warnings.warn(
                "significance_z loại mọi ô dày → k=0 (toàn bộ điểm nhận -1); "
                "hãy giảm significance_z hoặc min_count.",
                stacklevel=2,
            )

        label_of: dict[tuple[int, ...], int] = {}
        comp = 0
        for start in sorted(dense_set):
            if start in label_of:
                continue
            stack = [start]
            label_of[start] = comp
            while stack:
                cur = stack.pop()
                for nb in self._neighbors(cur, res, connectivity):
                    if nb in dense_set and nb not in label_of:
                        label_of[nb] = comp
                        stack.append(nb)
            comp += 1

        cell_to_comp = {
            int(np.ravel_multi_index(key, (res,) * self.n_dims_)): cid
            for key, cid in label_of.items()
        }
        labels = np.array(
            [cell_to_comp.get(int(f), -1) for f in self._flat_[level]], dtype=int
        )

        self.label_of_ = label_of
        self.n_clusters_ = comp
        self.cluster_level_ = level
        self._cell_comp_ = cell_to_comp
        return labels

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Nhãn cụm cho điểm mới (sau fit + cluster).

        Trả -1 nếu ô chứa điểm không thuộc cụm nào, điểm nằm ngoài vùng dữ liệu
        huấn luyện, hoặc chứa NaN/inf.
        """
        if not hasattr(self, "_cell_comp_"):
            raise RuntimeError("Hãy gọi fit(X) rồi cluster() trước khi predict()")
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if X.ndim != 2 or X.shape[1] != self.n_dims_:
            raise ValueError(f"X cần đúng {self.n_dims_} chiều, nhận shape={X.shape}")
        in_support = self._in_training_support(X)
        res = self.factor ** self.cluster_level_
        preds = np.full(X.shape[0], -1, dtype=int)
        if np.any(in_support):
            _, flat = self._assign(X[in_support], res)
            preds[in_support] = [
                self._cell_comp_.get(int(f), -1) for f in flat
            ]
        return preds

    def save(self, path: str | PathLike[str]) -> None:
        """Lưu model bằng pickle."""
        with open(path, "wb") as fh:
            pickle.dump(self, fh)

    @classmethod
    def load(cls, path: str | PathLike[str]) -> STING:
        """Nạp model từ save(); chỉ nạp file tin cậy (pickle)."""
        with open(path, "rb") as fh:
            obj = pickle.load(fh)
        if not isinstance(obj, cls):
            raise TypeError("File không chứa đối tượng STING")
        return obj

    def query_rect(
        self,
        rect: Sequence[Sequence[float]] | np.ndarray,
        level: int | None = None,
    ) -> dict[str, int | np.ndarray | None]:
        """Thống kê gộp của các ô nằm trọn trong ``rect`` = [(lo0, hi0), ...]."""
        lo, hi, level = self._validate_query(rect, level, caller="query_rect()")
        matched = [
            cell
            for cell in self.cells_[level].values()
            if np.all(cell.bounds_min >= lo) and np.all(cell.bounds_max <= hi)
        ]
        return self._merge_cells(matched)

    def query_top_down(
        self,
        rect: Sequence[Sequence[float]] | np.ndarray,
        confidence: float = 0.95,
        level: int | None = None,
    ) -> dict[str, int | np.ndarray | None]:
        """Truy vấn vùng từ trên xuống (Wang 1997), tỉa nhánh có xác suất nằm trong ``rect`` thấp."""
        lo, hi, target_level = self._validate_query(rect, level, caller="query_top_down()")
        if not (0.0 < confidence <= 1.0):
            raise ValueError(f"confidence phải thuộc (0, 1], nhận {confidence}")

        root = self.cells_[0].get((0,) * self.n_dims_)
        frontier: list[Cell] = [root] if root is not None else []
        visited_cells = 0
        pruned_cells = 0

        for lvl in range(target_level + 1):
            next_frontier: list[Cell] = []
            visited_cells += len(frontier)
            for cell in frontier:
                if (
                    np.any(cell.bounds_max < lo)
                    or np.any(cell.bounds_min > hi)
                    or np.any(cell.max_ < lo)
                    or np.any(cell.min_ > hi)
                ):
                    pruned_cells += 1
                    continue
                inside = np.all(cell.bounds_min >= lo) and np.all(cell.bounds_max <= hi)
                if lvl < target_level:
                    p_one = self._cell_rect_prob(cell, lo, hi)
                    p_any = 1.0 if p_one >= 1.0 else (1.0 - (1.0 - p_one) ** cell.count)
                    if not inside and p_any < (1.0 - confidence):
                        pruned_cells += 1
                        continue
                    prefix = cell.index
                    child_map = self.cells_[lvl + 1]
                    for offsets in itertools.product(range(self.factor), repeat=self.n_dims_):
                        ckey = tuple(p * self.factor + o for p, o in zip(prefix, offsets, strict=True))
                        child = child_map.get(ckey)
                        if child is not None:
                            next_frontier.append(child)
                elif inside:
                    next_frontier.append(cell)
                else:
                    pruned_cells += 1
            frontier = next_frontier

        stats = self._merge_cells(frontier)
        stats["visited_cells"] = visited_cells
        stats["pruned_cells"] = pruned_cells
        stats["leaf_cells_matched"] = len(frontier)
        return stats

    def _validate_query(
        self,
        rect: Sequence[Sequence[float]] | np.ndarray,
        level: int | None,
        *,
        caller: str,
    ) -> tuple[np.ndarray, np.ndarray, int]:
        if not hasattr(self, "cells_"):
            raise RuntimeError(f"Hãy gọi fit(X) trước khi {caller}")
        if level is None:
            level = self.n_levels - 1
        if not (0 <= level < self.n_levels):
            raise ValueError(
                f"level phải thuộc [0, {self.n_levels - 1}], nhận {level}"
            )
        rect_arr = np.asarray(rect, dtype=float)
        if rect_arr.ndim != 2 or rect_arr.shape != (self.n_dims_, 2):
            raise ValueError(
                f"rect cần shape ({self.n_dims_}, 2), nhận {rect_arr.shape}"
            )
        return rect_arr[:, 0], rect_arr[:, 1], level

    def _merge_cells(self, cells: Sequence[Cell]) -> dict[str, int | np.ndarray | None]:
        total = 0
        origin = np.zeros(self.n_dims_)
        mean_offset = np.zeros(self.n_dims_)
        m2 = np.zeros(self.n_dims_)
        mins = np.full(self.n_dims_, np.inf)
        maxs = np.full(self.n_dims_, -np.inf)

        for cell in cells:
            if total == 0:
                origin = cell.mean
            new_total = total + cell.count
            weight = cell.count / new_total

            delta = (cell.mean - origin) - mean_offset
            m2 += cell.count * cell.std ** 2 + total * weight * delta ** 2
            mean_offset += weight * delta
            total = new_total
            mins = np.minimum(mins, cell.min_)
            maxs = np.maximum(maxs, cell.max_)

        if total == 0:
            return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
        return {
            "count": total,
            "mean": origin + mean_offset,
            "std": np.sqrt(m2 / total),
            "min": mins,
            "max": maxs,
        }

    @staticmethod
    def _cell_rect_prob(cell: Cell, lo: np.ndarray, hi: np.ndarray) -> float:
        """Xác suất xấp xỉ theo phân phối chuẩn các chiều ô rơi vào vùng ``[lo, hi]``."""
        import math

        prob = 1.0
        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        for mu, sigma, low, high in zip(cell.mean, cell.std, lo, hi, strict=True):
            if sigma <= 0.0:
                p_dim = 1.0 if low <= mu <= high else 0.0
            else:
                cdf_hi = 0.5 * (1.0 + math.erf((high - mu) * inv_sqrt2 / sigma))
                cdf_lo = 0.5 * (1.0 + math.erf((low - mu) * inv_sqrt2 / sigma))
                p_dim = max(0.0, min(1.0, cdf_hi - cdf_lo))
            prob *= p_dim
        return float(max(0.0, min(1.0, prob)))

    def point_cell_index(self, level: int) -> np.ndarray:
        """Chỉ số ô của mỗi điểm tại ``level``, shape (n, d)."""
        if not hasattr(self, "_point_idx_"):
            raise RuntimeError("Hãy gọi fit(X) trước khi point_cell_index()")
        if not (0 <= level < self.n_levels):
            raise ValueError(
                f"level phải thuộc [0, {self.n_levels - 1}], nhận {level}"
            )
        return self._point_idx_[level].copy()

    def cell_stats(self, level: int) -> list[Cell]:
        """Các ô có dữ liệu tại ``level``, sắp theo chỉ số."""
        if not hasattr(self, "cells_"):
            raise RuntimeError("Hãy gọi fit(X) trước khi cell_stats()")
        if not (0 <= level < self.n_levels):
            raise ValueError(
                f"level phải thuộc [0, {self.n_levels - 1}], nhận {level}"
            )
        return [self.cells_[level][k] for k in sorted(self.cells_[level])]

    def _in_training_support(self, X: np.ndarray) -> np.ndarray:
        """Kiểm tra cực trị đã quan sát từ ô gốc, kể cả model lưu trước đây."""
        root = self.cells_[0][(0,) * self.n_dims_]
        return np.isfinite(X).all(axis=1) & ((X >= root.min_) & (X <= root.max_)).all(axis=1)

    def _assign(self, X: np.ndarray, res: int) -> tuple[np.ndarray, np.ndarray]:
        """Chỉ số ô (theo chiều và phẳng) của từng điểm trên lưới ``res`` ô/chiều."""
        span = self.bounds_max_ - self.bounds_min_
        span[span == 0.0] = 1.0
        idx = np.floor((X - self.bounds_min_) / span * res).astype(np.int64)
        np.clip(idx, 0, res - 1, out=idx)
        flat = np.ravel_multi_index(
            tuple(idx[:, k] for k in range(self.n_dims_)), (res,) * self.n_dims_
        )
        return idx, flat

    def _accumulate(
        self, X: np.ndarray, flat: np.ndarray, res: int, level: int
    ) -> dict[tuple[int, ...], Cell]:
        """Thống kê từng ô bằng một lượt nhóm điểm theo ``flat``."""
        span = self.bounds_max_ - self.bounds_min_
        step = span / res
        cells: dict[tuple[int, ...], Cell] = {}

        order = np.argsort(flat, kind="stable")
        sorted_flat = flat[order]
        boundaries = np.flatnonzero(np.diff(sorted_flat)) + 1
        for group in np.split(order, boundaries):
            key = tuple(int(m) for m in np.unravel_index(int(flat[group[0]]), (res,) * self.n_dims_))
            pts = X[group]
            cells[key] = Cell(
                level=level,
                index=key,
                bounds_min=self.bounds_min_ + np.asarray(key) * step,
                bounds_max=self.bounds_min_ + (np.asarray(key) + 1) * step,
                count=int(pts.shape[0]),
                mean=pts.mean(axis=0),
                std=pts.std(axis=0),
                min_=pts.min(axis=0),
                max_=pts.max(axis=0),
            )
        return cells

    def _is_dense(self, cell: Cell, level: int) -> bool:
        """``count >= min_count``; nếu có ``significance_z`` thì thêm kiểm định z so với ô cha."""
        if cell.count < self.min_count_:
            return False
        if self.significance_z is None or level == 0:
            return True
        parent = self._parent_of(cell)
        if parent is None or parent.count == 0:
            return True
        se = parent.std / np.sqrt(cell.count)
        diff = np.abs(cell.mean - parent.mean)
        return bool(np.any(diff > self.significance_z * se))

    def _parent_of(self, cell: Cell) -> Cell | None:
        """Ô cha ở mức trên; None ở mức 0."""
        if cell.level == 0:
            return None
        pidx = tuple(i // self.factor for i in cell.index)
        return self.cells_[cell.level - 1].get(pidx)

    def _neighbors(
        self, index: tuple[int, ...], res: int, connectivity: int
    ) -> Iterator[tuple[int, ...]]:
        """Các ô kề hợp lệ có tối đa ``connectivity`` tọa độ khác 0."""
        if connectivity == 1:
            for axis, coord in enumerate(index):
                for step in (-1, 1):
                    neighbor = coord + step
                    if 0 <= neighbor < res:
                        yield (*index[:axis], neighbor, *index[axis + 1:])
            return

        for offset in itertools.product((-1, 0, 1), repeat=self.n_dims_):
            if all(o == 0 for o in offset):
                continue
            if sum(1 for o in offset if o != 0) > connectivity:
                continue
            cand = tuple(i + o for i, o in zip(index, offset))
            if all(0 <= c < res for c in cand):
                yield cand
