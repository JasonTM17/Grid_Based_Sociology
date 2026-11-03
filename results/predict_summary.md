# Dự đoán cụm PAPI 2024 bằng STING (train 2011–2023)

- Cặp chỉ tiêu: 5.4 Dịch vụ hành chính cấp xã/phường × 6.2 Giáo dục tiểu học công lập
- Cấu hình: STING(L=3, factor=3, min_count=5), cluster level=2; train n=811, test n=61
- Kết quả train: 3 cụm, kích thước [605, 104, 46], nhiễu 7%
- Dự đoán 2024: phủ 82% ({-1: 11, 1: 21, 2: 29}); 29/59 tỉnh đổi cụm so với 2023

## Hồ sơ cụm (train)

|   cluster |   n |   sd_5_4 |   sd_6_2 |
|----------:|----:|---------:|---------:|
|        -1 |  56 |     2.22 |     1.56 |
|         0 | 605 |     1.89 |     1.65 |
|         1 |  46 |     2.47 |     1.4  |
|         2 | 104 |     2.45 |     1.9  |

## Thành phần dự đoán 2024

|   pred_cluster |   n |   sd_5_4_mean |   sd_6_2_mean | vi_du                                                        |
|---------------:|----:|--------------:|--------------:|:-------------------------------------------------------------|
|             -1 |  11 |          2.46 |          1.55 | Lào Cai, Điện Biên, Sơn La, Quảng Ninh, Bắc Ninh, Nam Định   |
|              1 |  21 |          2.47 |          1.44 | Hà Giang, Bắc Kạn, Tuyên Quang, Yên Bái, Hòa Bình, Hải Dương |
|              2 |  29 |          2.45 |          1.94 | Hà Nội, Cao Bằng, Lai Châu, Thái Nguyên, Lạng Sơn, Bắc Giang |

## Chuyển cụm 2023 → 2024 (chỉ tỉnh có đủ 2 chỉ tiêu cả 2 năm)

| pred_cluster_23   |   -1 |   1 |   2 |   All |
|:------------------|-----:|----:|----:|------:|
| -1                |    1 |   3 |   3 |     7 |
| 1                 |    5 |  11 |   7 |    23 |
| 2                 |    4 |   7 |  18 |    29 |
| All               |   10 |  21 |  28 |    59 |

Lưu ý: nhãn 2023 ở đây cũng do model gán (in-sample); các thay đổi sát ranh giới ô lưới có thể nhạy với ngưỡng cố định — không nên diễn giải quá mức các dịch chuyển nhỏ.
