"""Chuẩn trình bày hình thống nhất cho toàn bộ repo.

Module CHỈ cung cấp palette, rcParams và helper trình bày — không thay đổi
logic tính toán, không chạm dữ liệu. Các script vẽ hình gọi helper ở lớp
trình bày; script hiện có không bắt buộc sửa cùng lúc.

Cách dùng trong script/notebook::

    import matplotlib
    matplotlib.use("Agg")          # trước khi import pyplot
    import sys; sys.path.insert(0, "scripts")
    from matplotlib import pyplot as plt
    from fig_style import (style_context, new_fig, add_source, save_png,
                           AX_KINH_DO, AX_VI_DO, CLUSTER_COLORS, CLUSTER_LABELS)

    with style_context():
        fig, ax = new_fig()                     # 6.5 x 4.3 inch (cột docx)
        ...
        ax.set_xlabel(AX_KINH_DO)               # thay cho "longitude"
        add_source(fig, "PAPI — CECODES, VFF-CRT, RTA & UNDP",
                   retrieved="2026-11-03")      # ngày lấy từ PROVENANCE.md
        fig.tight_layout(rect=(0, 0.05, 1, 1))  # chừa lề dưới cho dòng nguồn
        save_png(fig, "results/figs/ten_hinh.png", dpi=200)

Quy ước palette cụm giữ NGUYÊN ngữ nghĩa đang dùng trong repo
(``external_validation.py:59-60``: xám=nhiễu, xanh dương=cụm 0, cam=cụm 1,
xanh lá=cụm 2) nhưng đổi sang giá trị hex Okabe–Ito để an toàn người mù màu.
"""

from __future__ import annotations

import contextlib
import textwrap
from pathlib import Path
from typing import Iterator, Optional, Union

import matplotlib as mpl
from cycler import cycler

__all__ = [
    "PALETTE",
    "COLOR_CYCLE",
    "CLUSTER_COLORS",
    "CLUSTER_LABELS",
    "AX_KINH_DO",
    "AX_VI_DO",
    "UNIT_LABELS",
    "DEFAULT_DPI",
    "MIN_DPI",
    "FIG_SIZE_IN",
    "SOURCE_FONTSIZE",
    "RC",
    "apply_style",
    "style_context",
    "new_fig",
    "add_source",
    "save_png",
]

# ---------------------------------------------------------------- palette --
# Okabe–Ito (CVD-safe), tối đa 6 màu. Thứ tự hue trùng với palette cụm cũ
# của repo (xám / xanh dương / cam / xanh lá) để hình cũ và mới cùng ngữ nghĩa.
PALETTE = {
    "gray": "#999999",   # xám — điểm nhiễu (nhãn -1)
    "blue": "#0072B2",   # xanh dương — cụm 0
    "orange": "#E69F00",  # cam — cụm 1
    "green": "#009E73",   # xanh lá — cụm 2
    "sky": "#56B4E9",     # xanh da trời — chuỗi phụ thứ 4
    "purple": "#CC79A7",  # hồng tím — chuỗi phụ thứ 5
}
# Vòng màu mặc định: chuỗi dữ liệu trước, xám (nhiễu) sau cùng.
COLOR_CYCLE = [
    PALETTE["blue"], PALETTE["orange"], PALETTE["green"],
    PALETTE["sky"], PALETTE["purple"], PALETTE["gray"],
]
# Đổi nhãn cụm -> màu. Khớp ngữ nghĩa với external_validation.py:60.
CLUSTER_COLORS = {
    -1: PALETTE["gray"],
    0: PALETTE["blue"],
    1: PALETTE["orange"],
    2: PALETTE["green"],
}
# Nhãn tiếng Việt cho cụm; khớp ngữ nghĩa external_validation.py:59
# (viết thường "cụm {k}" như hình hiện có, giữ dấu gạch ngang en-dash).
CLUSTER_LABELS = {-1: "nhiễu (–1)", 0: "cụm 0", 1: "cụm 1", 2: "cụm 2"}

# Nhãn trục tiếng Việt thay cho "longitude"/"latitude" (run_analysis.py:246-247).
AX_KINH_DO = "Kinh độ"
AX_VI_DO = "Vĩ độ"

# Đơn vị/thang đo đã đối chiếu với dữ liệu:
# - "papi": thang 1-10 của d1..d8 xác nhận theo data/processed/
#   papi_panel_scale_metadata.csv (cột thang_2011_2020/thang_2021_2024).
#   CHỈ dùng cho d1..d8; các cột sd_* CHƯA đối chiếu workbook, không gắn thang.
# - "pci": thang 0-100 như external_validation.py:165.
UNIT_LABELS = {
    "papi": "thang điểm 1–10",
    "pci": "thang 0–100",
}

# ------------------------------------------------------------ kích thước --
DEFAULT_DPI = 200
MIN_DPI = 200  # chuẩn repo: PNG lưu ra phải >= 200 DPI
# "docx":  6.5 inch rộng — khớp lề khổ A4 của reports/final_report.docx.
# "slide": 9 x 5.0625 inch — tỉ lệ 16:9 cho slides/final.pptx.
FIG_SIZE_IN = {
    "docx": (6.5, 4.3),
    "slide": (9.0, 5.0625),
}
SOURCE_FONTSIZE = 8  # dòng nguồn nhỏ hơn chú thích nhưng vẫn đọc được khi in

# --------------------------------------------------------------- rcParams --
RC = {
    "font.family": "sans-serif",
    # DejaVu Sans đi kèm matplotlib, phủ đủ ký tự tiếng Việt (kiểm chứng
    # bằng hình mẫu); các phông sau chỉ là dự phòng khi có sẵn.
    "font.sans-serif": ["DejaVu Sans", "Segoe UI", "Arial", "Noto Sans"],
    "font.size": 10,
    "figure.titlesize": 13,
    "figure.titleweight": "bold",
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "legend.title_fontsize": 10,
    "legend.frameon": False,
    "axes.edgecolor": "#444444",
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "axes.prop_cycle": cycler(color=COLOR_CYCLE),
    "savefig.dpi": DEFAULT_DPI,
    "savefig.facecolor": "white",
}

_RC_KEYS = tuple(RC)


def apply_style() -> None:
    """Áp rcParams chuẩn cho toàn bộ phiên (gọi một lần đầu script)."""
    mpl.rcParams.update(RC)


@contextlib.contextmanager
def style_context() -> Iterator[None]:
    """Áp rcParams chuẩn trong phạm vi ``with``; khôi phục khi ra khỏi khối."""
    old = {k: mpl.rcParams[k] for k in _RC_KEYS}
    mpl.rcParams.update(RC)
    try:
        yield
    finally:
        mpl.rcParams.update(old)


# ---------------------------------------------------------------- helper ---
def new_fig(
    target: Optional[str] = "docx", **subplots_kw: object
) -> tuple["mpl.figure.Figure", "mpl.axes.Axes"]:
    """Tạo figure kích thước chuẩn; trả về ``(fig, ax)`` như ``plt.subplots``.

    ``target``: ``"docx"`` (6.5 x 4.3 inch), ``"slide"`` (16:9) hoặc ``None``
    (kích thước mặc định matplotlib — dùng cho hình dọc như bản đồ tỉnh).
    """
    import matplotlib.pyplot as plt  # import muộn để không chọn backend sớm

    if target is None:
        return plt.subplots(**subplots_kw)
    if target not in FIG_SIZE_IN:
        raise ValueError(
            f"target={target!r} phải là một trong {sorted(FIG_SIZE_IN)} hoặc None"
        )
    return plt.subplots(figsize=FIG_SIZE_IN[target], **subplots_kw)


def add_source(
    fig: "mpl.figure.Figure",
    source: str,
    retrieved: Optional[str] = None,
    extra: Optional[str] = None,
    *,
    wrap_width: int = 100,
    fontsize: float = SOURCE_FONTSIZE,
    x: float = 0.01,
    y: float = 0.008,
    color: str = "#555555",
) -> None:
    """Ghi dòng nguồn chuẩn ở góc trái-dưới hình.

    Định dạng: ``'Nguồn: <nguồn dữ liệu> — tải <ngày>[ — <extra>]'``.
    ``retrieved`` PHẢI lấy từ PROVENANCE.md của dữ liệu (ví dụ PAPI tải
    2026-11-03 theo data/raw/papi/PROVENANCE.md) — helper không tự điền
    ngày render để không làm giả provenance. Nếu người gọi truyền Axes
    thay vì Figure, helper tự suy ra Figure.

    Nên gọi TRƯỚC ``tight_layout`` và chừa lề dưới, ví dụ
    ``fig.tight_layout(rect=(0, 0.05, 1, 1))`` để chữ không đè nhãn trục.
    """
    if hasattr(fig, "get_figure"):  # Axes -> Figure
        fig = fig.get_figure()
    parts = [f"Nguồn: {source}"]
    if retrieved:
        parts.append(f"tải {retrieved}")
    if extra:
        parts.append(extra)
    text = " — ".join(parts)
    wrapped = "\n".join(
        line
        for chunk in text.split("\n")
        for line in (textwrap.wrap(chunk, wrap_width) or [""])
    )
    fig.text(x, y, wrapped, ha="left", va="bottom", fontsize=fontsize, color=color)


def save_png(
    fig: "mpl.figure.Figure",
    path: Union[str, Path],
    target: Optional[str] = None,
    dpi: int = DEFAULT_DPI,
    bbox_inches: Union[str, None] = "tight",
    **savefig_kw: object,
) -> Path:
    """Lưu PNG chuẩn: DPI >= 200; mặc định ``bbox_inches="tight"``.

    Tight bbox giữ lại toàn bộ tiêu đề/nhãn/dòng nguồn (không bị cắt mép như
    hình kiểm thử đầu tiên); canh lề đã do ``tight_layout`` lo, nên kích thước
    thực chỉ lệch nhẹ quanh preset. Truyền ``bbox_inches=None`` nếu cần đúng
    tuyệt đối số pixel theo inch x DPI.

    ``target="docx"``/``"slide"`` sẽ resize figure theo preset trước khi lưu;
    ``target=None`` (mặc định) giữ nguyên — kích thước chuẩn nên được đặt lúc
    tạo figure qua :func:`new_fig` để không bóp méo hình dọc (bản đồ).
    Trả về đường dẫn đã lưu.
    """
    if dpi < MIN_DPI:
        raise ValueError(f"dpi={dpi} < {MIN_DPI}: chuẩn của repo là >= {MIN_DPI} DPI")
    if target is not None:
        if target not in FIG_SIZE_IN:
            raise ValueError(
                f"target={target!r} phải là một trong {sorted(FIG_SIZE_IN)} hoặc None"
            )
        fig.set_size_inches(*FIG_SIZE_IN[target])
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi, format="png", bbox_inches=bbox_inches, **savefig_kw)
    return out
