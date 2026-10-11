-- Bước 2: nhật ký mỗi lần nạp dữ liệu thô vào MinIO.
CREATE TABLE IF NOT EXISTS ingestion_log (
    batch_id        VARCHAR(40) PRIMARY KEY,
    source_file     TEXT        NOT NULL,
    bucket          VARCHAR(63),
    object_key      TEXT,
    row_count       INT,
    column_count    INT,
    file_size_bytes BIGINT,
    md5             CHAR(32)    NOT NULL,
    status          VARCHAR(10) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'SKIPPED')),
    message         TEXT,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_log_md5 ON ingestion_log (md5);
