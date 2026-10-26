-- Bước 5: bảng nghiệp vụ trong PostgreSQL (phần dữ liệu TĨNH theo sinh viên + kết quả dự đoán).
-- Dữ liệu biến động theo học kỳ nằm ở MongoDB, collection academic_semesters.

CREATE TABLE IF NOT EXISTS students (
    student_id       VARCHAR(15) PRIMARY KEY,
    age              INT,
    gender           VARCHAR(20),
    first_generation BOOLEAN,
    household_size   INT,
    housing_status   VARCHAR(20),
    family_income    NUMERIC(12, 2),          -- NULL cho sinh viên không khai báo ở kỳ nào
    income_missing   BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS financial_profiles (
    profile_id   SERIAL PRIMARY KEY,
    student_id   VARCHAR(15) NOT NULL UNIQUE REFERENCES students (student_id),
    scholarship  BOOLEAN,
    tuition_base NUMERIC(10, 2),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bước 14 ghi vào bảng này; tạo sẵn để schema đầy đủ ngay từ đầu.
CREATE TABLE IF NOT EXISTS predictions (
    run_id        VARCHAR(40) NOT NULL,
    run_date      TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_version VARCHAR(20),
    student_id    VARCHAR(15) NOT NULL REFERENCES students (student_id),
    semester      INT NOT NULL,
    risk_score    NUMERIC(5, 4),
    risk_level    VARCHAR(12),
    top_reason_1  TEXT,
    top_reason_2  TEXT,
    top_reason_3  TEXT,
    PRIMARY KEY (run_id, student_id)
);
