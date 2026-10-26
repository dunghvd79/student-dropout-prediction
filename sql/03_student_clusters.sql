-- Bước 8A: kết quả phân cụm sinh viên (dùng cho dashboard B15). Tính lại toàn bộ mỗi lần chạy.
CREATE TABLE IF NOT EXISTS student_clusters (
    student_id   VARCHAR(15) PRIMARY KEY REFERENCES students (student_id),
    cluster_id   INT         NOT NULL,
    cluster_name VARCHAR(80) NOT NULL
);
