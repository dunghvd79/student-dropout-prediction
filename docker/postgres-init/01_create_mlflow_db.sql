-- Chạy một lần khi khởi tạo volume PostgreSQL lần đầu.
-- Tách database riêng cho MLflow để bảng của MLflow không lẫn với bảng nghiệp vụ.
CREATE DATABASE mlflow;
