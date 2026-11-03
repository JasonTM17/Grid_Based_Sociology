"""STING – STatistical INformation Grid (cài đặt từ đầu, không dùng thư viện ngoài).

Tham khảo: Wang, Yang & Muntz (1997), "STING: A Statistical Information Grid
Approach to Spatial Data Mining", Proc. of VLDB.

Ý tưởng chính
-------------
1. Không gian dữ liệu được chia thành lưới phân cấp: mức ``l`` chia mỗi chiều
   thành ``factor ** l`` đoạn bằng nhau (mức 0 = một ô duy nhất).
2. Mỗi ô lưu thống kê độc lập theo từng chiều: count, mean, std, min, max.
3. Dữ liệu được quét một lần cho mỗi mức → chi phí O(n) theo số điểm.
4. Phân cụm: gom các ô "dày" (count >= min_count) liền kề thành cụm; điểm
   thuộc ô không dày nhận nhãn -1 (nhiễu).

Ví dụ
-----
>>> import numpy as np
>>> from sting import STING
>>> X = np.random.default_rng(0).normal(size=(100, 2))
>>> model = STING(n_levels=3, factor=4, min_count=5).fit(X)
>>> labels = model.cluster(level=2)
"""
from __future__ import annotations

import itertools
import pickle
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

__all__ = ["Cell", "STING"]


@dataclass
class Cell:
    """Một ô lưới tại một mức phân cấp."""

    level: int
    index: Tuple[int, ...]          # chỉ số ô theo từng chiều
    bounds_min: np.ndarray          # cận dưới (mỗi chiều)
    bounds_max: np.ndarray          # cận trên (mỗi chiều)
    count: int = 0
    mean: Optional[np.ndarray] = None
    std: Optional[np.ndarray] = None
    min_: Optional[np.ndarray] = None
    max_: Optional[np.ndarray] = None


class STING:
    """Lưới thống kê phân cấp cho phân cụm không gian nhiều chiều."""

    def __init__(
        self,
        n_levels: int = 4,
        factor: int = 2,
        min_count: Optional[int] = None,
        significance_z: Optional[float] = None,
    ) -> None:
        if n_levels < 1:
            raise ValueError("n_levels phải >= 1")
        if factor < 2:
            raise ValueError("factor phải >= 2")
        self.n_levels = int(n_levels)
        self.factor = int(factor)
        self.min_count = min_count
        self.significance_z = significance_z

    # ------------------------------------------------------------------ #
    # Huấn luyện: xây lưới phân cấp và thống kê từng ô
    # ------------------------------------------------------------------ #
    def fit(self, X: np.ndarray) -> "STING":
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or X.shape[0] == 0:
            raise ValueError("X phải là mảng 2 chiều (n_samples, n_dims) không rỗng")

        n, d = X.shape
        self.n_samples_, self.n_dims_ = n, d

        lo = X.min(axis=0)
        hi = X.max(axis=0)
        width = hi - lo
        width[width == 0.0] = 1.0  # chiều hằng số: nới giả để chia được lưới
        self.bounds_min_, self.bounds_max_ = lo, lo + width

        self.min_count_ = (
            int(self.min_count)
            if self.min_count is not None
            else max(1, int(round(0.02 * n)))
        )

        self.cells_: Dict[int, Dict[Tuple[int, ...], Cell]] = {}
        self._point_idx_: Dict[int, np.ndarray] = {}
        self._flat_: Dict[int, np.ndarray] = {}

        for level in range(self.n_levels):
            res = self.factor ** level
            idx, flat = self._assign(X, res)
            self._point_idx_[level] = idx
            self._flat_[level] = flat
            self.cells_[level] = self._accumulate(X, flat, res, level)
        return self

    # ------------------------------------------------------------------ #
    # Phân cụm
    # ------------------------------------------------------------------ #
    def cluster(self, level: Optional[int] = None, connectivity: int = 1) -> np.ndarray:
        """Gán nhãn cụm cho từng điểm tại mức lưới ``level``.

        connectivity = 1: chỉ gom ô kề mặt (4 hướng trong 2D);
        connectivity = số chiều: gom cả ô kề góc (8 hướng trong 2D).
        Điểm thuộc ô không dày nhận nhãn -1 (nhiễu).
        """
        if not hasattr(self, "cells_"):
            raise RuntimeError("Hãy gọi fit(X) trước khi cluster()")
        if level is None:
            level = self.n_levels - 1
        res = self.factor ** level

        dense_set = {
            key
            for key, cell in self.cells_[level].items()
            if self._is_dense(cell, level)
        }

        # Gom thành phần liên thông trên các ô dày (DFS lặp, thứ tự ổn định).
        label_of: Dict[Tuple[int, ...], int] = {}
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

        # Gán nhãn cho từng điểm theo ô chứa nó.
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

    def predict(self, X) -> np.ndarray:
        """Dự đoán cụm cho các điểm MỚI sau khi đã fit() + cluster().

        Điểm mới được gán vào cụm của ô chứa nó tại mức lưới dùng trong cluster();
        nhận -1 nếu ô đó không thuộc cụm nào (nhiễu hoặc ô chưa từng có dữ liệu).
        """
        if not hasattr(self, "_cell_comp_"):
            raise RuntimeError("Hãy gọi fit(X) rồi cluster() trước khi predict()")
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if X.ndim != 2 or X.shape[1] != self.n_dims_:
            raise ValueError(f"X cần đúng {self.n_dims_} chiều, nhận shape={X.shape}")
        res = self.factor ** self.cluster_level_
        _, flat = self._assign(X, res)
        return np.array([self._cell_comp_.get(int(f), -1) for f in flat], dtype=int)

    def save(self, path) -> None:
        """Lưu model đã huấn luyện thành file local (pickle)."""
        with open(path, "wb") as fh:
            pickle.dump(self, fh)

    @classmethod
    def load(cls, path) -> "STING":
        """Nạp model đã lưu bằng save() — dự đoán không cần huấn luyện lại."""
        with open(path, "rb") as fh:
            obj = pickle.load(fh)
        if not isinstance(obj, cls):
            raise TypeError("File không chứa đối tượng STING")
        return obj

    # ------------------------------------------------------------------ #
    # Truy vấn & tiện ích
    # ------------------------------------------------------------------ #
    def query_rect(self, rect, level: Optional[int] = None) -> dict:
        """Thống kê tổng hợp vùng chữ nhật (chỉ gồm các ô nằm trọn trong vùng).

        rect: danh sách [(lo0, hi0), (lo1, hi1), ...] theo từng chiều.
        """
        if level is None:
            level = self.n_levels - 1
        rect = np.asarray(rect, dtype=float)
        lo, hi = rect[:, 0], rect[:, 1]

        total = 0
        sum_ = np.zeros(self.n_dims_)
        sumsq = np.zeros(self.n_dims_)
        mins = np.full(self.n_dims_, np.inf)
        maxs = np.full(self.n_dims_, -np.inf)

        for cell in self.cells_[level].values():
            if np.all(cell.bounds_min >= lo) and np.all(cell.bounds_max <= hi):
                total += cell.count
                sum_ += cell.mean * cell.count
                sumsq += (cell.std ** 2 + cell.mean ** 2) * cell.count
                mins = np.minimum(mins, cell.min_)
                maxs = np.maximum(maxs, cell.max_)

        if total == 0:
            return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
        mean = sum_ / total
        var = np.maximum(sumsq / total - mean ** 2, 0.0)
        return {
            "count": int(total),
            "mean": mean,
            "std": np.sqrt(var),
            "min": mins,
            "max": maxs,
        }

    def point_cell_index(self, level: int) -> np.ndarray:
        """Chỉ số ô (theo từng chiều) của mỗi điểm tại mức `level` — shape (n, d)."""
        return self._point_idx_[level].copy()

    def cell_stats(self, level: int):
        """Danh sách các ô có dữ liệu tại mức `level`, sắp xếp theo chỉ số."""
        return [self.cells_[level][k] for k in sorted(self.cells_[level])]

    # ------------------------------------------------------------------ #
    # Nội bộ
    # ------------------------------------------------------------------ #
    def _assign(self, X: np.ndarray, res: int) -> Tuple[np.ndarray, np.ndarray]:
        """Tính chỉ số ô của từng điểm tại lưới `res` ô/chiều."""
        span = self.bounds_max_ - self.bounds_min_
        idx = np.floor((X - self.bounds_min_) / span * res).astype(np.int64)
        np.clip(idx, 0, res - 1, out=idx)  # điểm ở biên trên cùng vào ô cuối
        flat = np.ravel_multi_index(
            tuple(idx[:, k] for k in range(self.n_dims_)), (res,) * self.n_dims_
        )
        return idx, flat

    def _accumulate(self, X: np.ndarray, flat: np.ndarray, res: int, level: int):
        """Tính thống kê từng ô từ nhóm điểm theo `flat` (một lượt O(n))."""
        span = self.bounds_max_ - self.bounds_min_
        step = span / res
        cells: Dict[Tuple[int, ...], Cell] = {}

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
        """Ô dày nếu đủ số điểm; tùy chọn thêm kiểm định ý nghĩa so với ô cha."""
        if cell.count < self.min_count_:
            return False
        if self.significance_z is None or level == 0:
            return True
        parent = self._parent_of(cell)
        if parent is None or parent.count == 0:
            return True
        se = parent.std / np.sqrt(cell.count)
        diff = np.abs(cell.mean - parent.mean)
        with np.errstate(divide="ignore", invalid="ignore"):
            return bool(np.any(diff > self.significance_z * se))

    def _parent_of(self, cell: Cell) -> Optional[Cell]:
        if cell.level == 0:
            return None
        pidx = tuple(i // self.factor for i in cell.index)
        return self.cells_[cell.level - 1].get(pidx)

    def _neighbors(self, index: Tuple[int, ...], res: int, connectivity: int):
        """Sinh chỉ số các ô kề hợp lệ (số tọa độ khác 0 <= connectivity)."""
        for offset in itertools.product((-1, 0, 1), repeat=self.n_dims_):
            if all(o == 0 for o in offset):
                continue
            if sum(1 for o in offset if o != 0) > connectivity:
                continue
            cand = tuple(i + o for i, o in zip(index, offset))
            if all(0 <= c < res for c in cand):
                yield cand
