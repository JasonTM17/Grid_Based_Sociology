"""Kiểm thử thư viện STING (tự viết từ đầu).

Chạy: python -m pytest tests -q
"""
import inspect
import warnings
from pathlib import Path

import numpy as np
import pytest
from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score

from sting import STING


def test_assignment_counts_and_means_known_data():
    """4 điểm ở gốc và 4 điểm ở góc đối diện → 2 ô, count/mean xác định trước."""
    X = np.array([[0.0, 0.0]] * 4 + [[1.0, 1.0]] * 4)
    model = STING(n_levels=2, factor=4, min_count=1).fit(X)

    cell00 = model.cells_[1][(0, 0)]
    cell33 = model.cells_[1][(3, 3)]  # điểm tại cận trên rơi vào ô cuối

    assert cell00.count == 4 and cell33.count == 4
    assert np.allclose(cell00.mean, [0.0, 0.0])
    assert np.allclose(cell33.mean, [1.0, 1.0])


def test_stats_match_numpy_ground_truth():
    """Thống kê từng ô phải khớp tính toán trực tiếp bằng numpy."""
    rng = np.random.default_rng(123)
    X = rng.normal(size=(300, 3))
    model = STING(n_levels=3, factor=3, min_count=5).fit(X)

    for level in range(3):
        idx = model.point_cell_index(level)
        for key, cell in model.cells_[level].items():
            mask = np.all(idx == np.asarray(key), axis=1)
            pts = X[mask]
            assert cell.count == pts.shape[0]
            assert np.allclose(cell.mean, pts.mean(axis=0))
            assert np.allclose(cell.std, pts.std(axis=0))
            assert np.allclose(cell.min_, pts.min(axis=0))
            assert np.allclose(cell.max_, pts.max(axis=0))


def test_boundary_point_goes_to_last_cell():
    """Điểm đúng ở cận trên không bị mất, rơi vào ô cuối cùng."""
    X = np.array([[0.0, 0.0], [1.0, 1.0], [0.25, 0.25]])
    model = STING(n_levels=2, factor=2, min_count=1).fit(X)
    idx = model.point_cell_index(1)  # res = 2
    assert tuple(idx[1]) == (1, 1)
    assert tuple(idx[2]) == (0, 0)
    assert model.cells_[1][(1, 1)].count == 1


def test_two_blobs_recovered():
    """STING phải tách được 2 cụm blob tách biệt trên lưới mịn (ARI >= 0.9)."""
    X, y = make_blobs(
        n_samples=240, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42
    )
    model = STING(n_levels=3, factor=4, min_count=3).fit(X)
    labels = model.cluster(level=2, connectivity=1)
    assert adjusted_rand_score(y, labels) >= 0.9
    assert (labels == -1).mean() <= 0.05  # hầu như không có nhiễu


def test_deterministic():
    """Hai lần chạy trên cùng dữ liệu cho cùng nhãn cụm."""
    X = np.random.default_rng(0).normal(size=(150, 2))
    a = STING(n_levels=3, factor=3, min_count=5).fit(X).cluster()
    b = STING(n_levels=3, factor=3, min_count=5).fit(X).cluster()
    assert np.array_equal(a, b)


def test_all_points_labeled_once():
    """Mọi điểm đều có nhãn (cụm >= 0 hoặc nhiễu -1), độ dài đúng n."""
    X = np.random.default_rng(1).normal(size=(100, 2))
    labels = STING(n_levels=3, factor=2, min_count=10).fit(X).cluster()
    assert labels.shape == (100,)
    assert np.all(labels >= -1)


def test_single_point():
    """Một điểm duy nhất không làm sập thuật toán."""
    model = STING(n_levels=3, factor=2).fit(np.array([[5.0, 5.0]]))
    labels = model.cluster()
    assert labels.shape == (1,)


def test_query_rect_basic():
    """Truy vấn vùng chữ nhật trả về count hợp lệ và mean đúng số chiều."""
    rng = np.random.default_rng(9)
    X = rng.uniform(-5, 5, size=(400, 2))
    model = STING(n_levels=3, factor=4, min_count=1).fit(X)
    res = model.query_rect([(-2, 2), (-2, 2)], level=2)
    assert 0 < res["count"] <= 400
    assert res["mean"].shape == (2,)
    assert res["std"].shape == (2,)


def test_predict_assigns_new_points_to_clusters():
    """predict() gán điểm mới vào cụm của ô chứa nó (dự đoán cho dữ liệu chưa thấy)."""
    X, _ = make_blobs(
        n_samples=240, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42
    )
    model = STING(n_levels=3, factor=4, min_count=3).fit(X)
    model.cluster(level=2, connectivity=1)

    new_points = np.array([[5.9, 6.1], [-6.1, -5.9]])  # gần tâm hai cụm
    pred = model.predict(new_points)

    assert pred.shape == (2,)
    assert -1 not in pred  # không rơi vào nhiễu
    assert pred[0] != pred[1]  # hai điểm thuộc hai cụm khác nhau


def test_predict_before_cluster_raises():
    """Gọi predict() trước cluster() phải báo lỗi rõ ràng."""
    X = np.random.default_rng(0).normal(size=(50, 2))
    model = STING(n_levels=2, factor=4, min_count=2).fit(X)
    with pytest.raises(RuntimeError):
        model.predict(np.array([[0.0, 0.0]]))


def test_predict_out_of_support_returns_noise():
    """Điểm ngoài vùng dữ liệu huấn luyện KHÔNG được kẹp vào ô biên — nhận -1."""
    X, _ = make_blobs(
        n_samples=240, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42
    )
    model = STING(n_levels=3, factor=4, min_count=3).fit(X)
    model.cluster(level=2, connectivity=1)

    far = np.array([[-50.0, -50.0], [0.0, -80.0]])
    assert np.array_equal(model.predict(far), np.array([-1, -1]))

    # điểm trong vùng huấn luyện vẫn dự đoán bình thường
    inside = np.array([[6.0, 6.0]])
    assert model.predict(inside)[0] != -1


def test_save_load_roundtrip(tmp_path):
    """Model lưu ra file rồi nạp lại phải cho kết quả dự đoán y hệt."""
    X, _ = make_blobs(
        n_samples=200, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=7
    )
    model = STING(n_levels=3, factor=4, min_count=3).fit(X)
    labels = model.cluster(level=2, connectivity=1)

    path = tmp_path / "sting_model.pkl"
    model.save(path)
    loaded = STING.load(path)

    assert np.array_equal(loaded.predict(X), labels)
    new_points = np.array([[6.0, 6.0]])
    assert np.array_equal(model.predict(new_points), loaded.predict(new_points))


def test_invalid_init_params_raise():
    """n_levels < 1 và factor < 2 phải báo lỗi ngay khi khởi tạo."""
    with pytest.raises(ValueError):
        STING(n_levels=0, factor=4)
    with pytest.raises(ValueError):
        STING(n_levels=2, factor=1)


def test_fit_rejects_non_2d_input():
    """fit() với mảng 1 chiều phải báo lỗi rõ ràng."""
    model = STING(n_levels=2, factor=4, min_count=2)
    with pytest.raises(ValueError):
        model.fit(np.array([1.0, 2.0, 3.0]))


def test_cluster_before_fit_raises():
    """Gọi cluster() trước fit() phải báo lỗi."""
    model = STING(n_levels=2, factor=4, min_count=2)
    with pytest.raises(RuntimeError):
        model.cluster()


def test_predict_accepts_1d_input():
    """predict() nhận mảng 1 chiều (1 điểm) và reshape tự động."""
    X, _ = make_blobs(n_samples=120, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42)
    model = STING(n_levels=3, factor=4, min_count=3).fit(X)
    model.cluster(level=2, connectivity=1)
    pred = model.predict(np.array([6.0, 6.0]))
    assert pred.shape == (1,)
    assert pred[0] != -1


def test_predict_rejects_wrong_n_dims():
    """predict() với sai số chiều phải báo lỗi."""
    X, _ = make_blobs(n_samples=120, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42)
    model = STING(n_levels=3, factor=4, min_count=3).fit(X)
    model.cluster(level=2, connectivity=1)
    with pytest.raises(ValueError):
        model.predict(np.array([[1.0, 2.0, 3.0]]))


def test_load_rejects_non_sting_pickle(tmp_path):
    """load() với pickle không phải đối tượng STING phải báo TypeError."""
    import pickle

    path = tmp_path / "fake.pkl"
    with open(path, "wb") as fh:
        pickle.dump({"khong": "phai sting"}, fh)
    with pytest.raises(TypeError):
        STING.load(path)


def test_query_rect_default_level_and_empty_region():
    """query_rect không truyền level vẫn chạy; vùng ngoài dữ liệu trả về count=0."""
    rng = np.random.default_rng(9)
    X = rng.uniform(-5, 5, size=(400, 2))
    model = STING(n_levels=3, factor=4, min_count=1).fit(X)
    res = model.query_rect([(-5, 5), (-5, 5)])  # level mặc định, toàn bộ vùng dữ liệu
    assert res["count"] == 400
    empty = model.query_rect([(1000, 1001), (1000, 1001)])
    assert empty["count"] == 0
    assert empty["mean"] is None


def test_significance_z_branch_runs():
    """significance_z kích hoạt kiểm định ô con so với ô cha — nhãn vẫn hợp lệ."""
    X, _ = make_blobs(n_samples=150, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42)
    model = STING(n_levels=3, factor=4, min_count=3, significance_z=0.5).fit(X)
    labels = model.cluster(level=2, connectivity=1)
    assert labels.shape == (len(X),)


def test_cell_stats_and_point_cell_index():
    """cell_stats() trả ô theo thứ tự chỉ số; point_cell_index đúng shape."""
    X, _ = make_blobs(n_samples=100, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42)
    model = STING(n_levels=3, factor=4, min_count=2).fit(X)
    cells = model.cell_stats(level=2)
    keys = [c.index for c in cells]
    assert keys == sorted(keys)
    idx = model.point_cell_index(level=2)
    assert idx.shape == (len(X), 2)


def test_connectivity_2_runs():
    """connectivity=2 (8-hướng kề góc) vẫn gom thành phần liên thông."""
    X, _ = make_blobs(n_samples=150, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42)
    model = STING(n_levels=3, factor=4, min_count=3).fit(X)
    labels = model.cluster(level=2, connectivity=2)
    assert labels.shape == (len(X),)
    assert model.n_clusters_ >= 1


def test_connectivity_semantics():
    """Hai ô dày kề CHÉO: connectivity=1 → 2 cụm riêng; connectivity=2 → gộp 1.

    Khóa tính chất kề mặt/kề góc mà docstring cluster() tuyên bố — một sửa sai
    bỏ qua giới hạn connectivity trong _neighbors() phải làm test này đỏ.
    """
    X = np.array([[0.1, 0.1]] * 3 + [[0.9, 0.9]] * 3)  # ô (0,0) và ô (1,1) chéo nhau
    model = STING(n_levels=2, factor=2, min_count=2).fit(X)

    lab_face = model.cluster(level=1, connectivity=1)
    assert np.all(lab_face >= 0)  # mọi điểm thuộc ô dày
    assert sorted(set(lab_face.tolist())) == [0, 1]  # kề chéo KHÔNG gom: 2 cụm

    lab_diag = model.cluster(level=1, connectivity=2)
    assert np.all(lab_diag >= 0)
    assert sorted(set(lab_diag.tolist())) == [0]  # kề cả góc: gộp thành 1 cụm


def test_cluster_invalid_level():
    """level ngoài [0, n_levels-1] phải ValueError thân thiện (không KeyError thô)."""
    model = STING(n_levels=3, factor=2, min_count=2).fit(
        np.random.default_rng(0).normal(size=(60, 2))
    )
    with pytest.raises(ValueError):
        model.cluster(level=3)  # == n_levels
    with pytest.raises(ValueError):
        model.cluster(level=-1)


def test_connectivity_zero_rejected():
    """connectivity=0 vô nghĩa (không ô nào kề được) → ValueError."""
    model = STING(n_levels=2, factor=2, min_count=2).fit(
        np.random.default_rng(0).normal(size=(60, 2))
    )
    with pytest.raises(ValueError):
        model.cluster(connectivity=0)


def test_query_rect_boundary():
    """Semantics query_rect đã tài liệu hóa: chỉ đếm ô nằm TRON trong vùng.

    Vùng thẳng lưới: count phải khớp đếm trực tiếp bằng numpy. Vùng lệch biên:
    query_rect bỏ điểm ở ô bị cắt biên nên count <= đếm trực tiếp, và sai lệch
    bị chặn trên bởi tổng count các ô cắt biên.
    """
    rng = np.random.default_rng(11)
    X = rng.uniform(-5, 5, size=(500, 2))
    model = STING(n_levels=3, factor=4, min_count=1).fit(X)
    level = 2

    def direct_count(rect):
        rect = np.asarray(rect, dtype=float)
        lo, hi = rect[:, 0], rect[:, 1]
        return int(np.sum(np.all((X >= lo) & (X <= hi), axis=1)))

    def cut_points(rect):
        """Tổng count các ô cắt biên: giao vùng nhưng không nằm trọn trong vùng."""
        rect = np.asarray(rect, dtype=float)
        lo, hi = rect[:, 0], rect[:, 1]
        total = 0
        for cell in model.cells_[level].values():
            fully = np.all(cell.bounds_min >= lo) and np.all(cell.bounds_max <= hi)
            overlaps = np.all(cell.bounds_max > lo) and np.all(cell.bounds_min < hi)
            if overlaps and not fully:
                total += cell.count
        return total

    # (a) vùng thẳng lưới — rect trùng đúng biên của một ô có dữ liệu
    cell = max(model.cells_[level].values(), key=lambda c: c.count)
    rect_aligned = [
        (cell.bounds_min[0], cell.bounds_max[0]),
        (cell.bounds_min[1], cell.bounds_max[1]),
    ]
    res = model.query_rect(rect_aligned, level=level)
    assert res["count"] == direct_count(rect_aligned)

    # (b) vùng lệch biên — dịch 30% bước ô so với lưới 3x3 ô
    res_grid = model.factor ** level
    step = (model.bounds_max_ - model.bounds_min_) / res_grid
    base_lo = model.bounds_min_ + 4 * step
    base_hi = model.bounds_min_ + 7 * step
    shift = 0.3 * step
    rect_off = [
        (base_lo[0] + shift[0], base_hi[0] + shift[0]),
        (base_lo[1] + shift[1], base_hi[1] + shift[1]),
    ]
    res_off = model.query_rect(rect_off, level=level)
    assert res_off["count"] <= direct_count(rect_off)
    assert abs(res_off["count"] - direct_count(rect_off)) <= cut_points(rect_off)


def test_determinism(tmp_path):
    """STING tất định: fit lại cho cùng nhãn; load(model) ≡ refit khi predict."""
    X, _ = make_blobs(
        n_samples=200, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=7
    )
    m1 = STING(n_levels=3, factor=4, min_count=3).fit(X)
    l1 = m1.cluster(level=2, connectivity=1)
    m2 = STING(n_levels=3, factor=4, min_count=3).fit(X)
    l2 = m2.cluster(level=2, connectivity=1)
    assert np.array_equal(l1, l2)

    path = tmp_path / "determinism.pkl"
    m1.save(path)
    loaded = STING.load(path)
    assert np.array_equal(loaded.predict(X), l2)
    assert np.array_equal(loaded.cluster(level=2, connectivity=1), l2)


def test_significance_z_collapses():
    """z rất lớn loại mọi ô dày → k=0, 100% nhiễu, và cluster() cảnh báo rõ ràng.

    Dữ liệu không phương sai (mọi điểm trùng nhau): parent.std = 0 nên điều kiện
    z không bao giờ thỏa với z > 0 — tất định, không phụ thuộc dữ liệu ngẫu nhiên.
    """
    X = np.zeros((20, 2))
    model = STING(n_levels=2, factor=2, min_count=1, significance_z=50).fit(X)
    with pytest.warns(UserWarning, match="significance_z"):
        labels = model.cluster(level=1, connectivity=1)
    assert model.n_clusters_ == 0
    assert np.all(labels == -1)


def test_significance_z_warning_points_at_caller():
    """Cảnh báo k=0 phải trỏ về file gọi cluster() (stacklevel=2), không trỏ vào src/sting.py."""
    X = np.zeros((20, 2))
    model = STING(n_levels=2, factor=2, min_count=1, significance_z=50).fit(X)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        caller_line = inspect.currentframe().f_lineno + 1
        model.cluster(level=1, connectivity=1)

    assert len(caught) == 1, f"cần đúng 1 cảnh báo, nhận {len(caught)}"
    warning = caught[0]
    assert Path(warning.filename).resolve() == Path(__file__).resolve()
    assert warning.lineno == caller_line
    assert warning.category is UserWarning


def test_min_count_negative_rejected():
    """min_count < 0 làm sai ngưỡng ô dày — phải ValueError khi khởi tạo."""
    with pytest.raises(ValueError, match="min_count"):
        STING(n_levels=2, factor=2, min_count=-1)


def test_fit_rejects_excessive_grid_volume():
    """Tham số lưới quá lớn phải báo ValueError rõ, không lỗi NumPy giữa fit."""
    X = np.random.default_rng(0).normal(size=(20, 4))
    model = STING(n_levels=5, factor=16)
    with pytest.raises(ValueError, match="lưới quá lớn"):
        model.fit(X)


def test_fit_rejects_nan_and_inf():
    """fit() từ chối NaN/inf trong X."""
    model = STING(n_levels=2, factor=2, min_count=1)
    base = np.random.default_rng(0).normal(size=(10, 2))
    with pytest.raises(ValueError, match="NaN"):
        model.fit(np.vstack([base, [np.nan, 0.0]]))
    with pytest.raises(ValueError, match="NaN"):
        model.fit(np.vstack([base, [0.0, np.inf]]))


def test_fit_rejects_empty_samples():
    """fit() với n_samples=0 phải ValueError."""
    model = STING(n_levels=2, factor=2, min_count=1)
    with pytest.raises(ValueError, match="không rỗng"):
        model.fit(np.empty((0, 2)))


def test_predict_non_finite_returns_noise_without_warning():
    """predict(): hàng NaN/inf nhận -1, không gọi _assign (không RuntimeWarning)."""
    X, _ = make_blobs(
        n_samples=120, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42
    )
    model = STING(n_levels=3, factor=4, min_count=3).fit(X)
    model.cluster(level=2, connectivity=1)
    bad = np.array([[np.nan, 0.0], [0.0, np.inf], [6.0, 6.0]])
    pred = model.predict(bad)
    assert list(pred[:2]) == [-1, -1]
    assert pred[2] != -1
