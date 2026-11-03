"""Kiểm thử thư viện STING (tự viết từ đầu).

Chạy: python -m pytest tests -q
"""
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
