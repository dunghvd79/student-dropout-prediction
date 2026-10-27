-- Bước 16: nhật ký mỗi lần chạy pipeline định kỳ + chỉ số giám sát.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id       VARCHAR(40) PRIMARY KEY,           -- run_<yyyymmddThhmmss>
    trigger      VARCHAR(20) NOT NULL,              -- manual / scheduled
    started_at   TIMESTAMPTZ NOT NULL,
    finished_at  TIMESTAMPTZ,
    status       VARCHAR(10) NOT NULL,              -- RUNNING / SUCCESS / FAILED
    failed_step  VARCHAR(30),
    seconds      NUMERIC(8, 1),
    steps        JSONB NOT NULL DEFAULT '[]',       -- [{step, status, seconds, exit_code}]
    metrics      JSONB,                             -- kết quả monitor (PSI, thiếu dữ liệu, phân bố rủi ro…)
    alerts       TEXT[] NOT NULL DEFAULT '{}'
);
