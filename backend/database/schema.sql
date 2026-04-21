-- Schema MySQL cho AI Tool for Automatic Use Case Point Estimation.
-- File này tạo 7 bảng lưu input, lần phân tích, dữ liệu parse, actor, use case, kết quả tính toán và log.
-- Chạy file này một lần trước khi demo chức năng lưu kết quả.

CREATE DATABASE IF NOT EXISTS ucpdb
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ucpdb;

CREATE TABLE IF NOT EXISTS documents (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  input_type VARCHAR(50) NOT NULL,
  original_filename VARCHAR(255) NULL,
  raw_text LONGTEXT NULL,
  source_template_type VARCHAR(100) NULL,
  parsing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
  notes TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_documents_input_type (input_type),
  INDEX idx_documents_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analysis_runs (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  document_id BIGINT UNSIGNED NOT NULL,
  llm_mode VARCHAR(50) NOT NULL DEFAULT 'mock',
  technical_complexity_factor DECIMAL(10, 4) NOT NULL DEFAULT 1.0000,
  environmental_complexity_factor DECIMAL(10, 4) NOT NULL DEFAULT 1.0000,
  productivity_factor DECIMAL(10, 2) NOT NULL DEFAULT 20.00,
  team_size INT NOT NULL DEFAULT 3,
  run_type VARCHAR(50) NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'running',
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP NULL,
  error_message TEXT NULL,
  CONSTRAINT fk_analysis_runs_document
    FOREIGN KEY (document_id) REFERENCES documents(id)
    ON DELETE CASCADE,
  INDEX idx_analysis_runs_document_id (document_id),
  INDEX idx_analysis_runs_status (status),
  INDEX idx_analysis_runs_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS parsed_use_case_documents (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  use_case_id VARCHAR(100) NULL,
  use_case_name VARCHAR(255) NOT NULL,
  actors_json JSON NULL,
  primary_actor VARCHAR(255) NULL,
  secondary_actors_json JSON NULL,
  description TEXT NULL,
  goal TEXT NULL,
  trigger_event TEXT NULL,
  preconditions TEXT NULL,
  postconditions TEXT NULL,
  functional_requirement TEXT NULL,
  main_flow_steps_json JSON NULL,
  alternative_flow_steps_json JSON NULL,
  exception_flow_steps_json JSON NULL,
  priority VARCHAR(100) NULL,
  business_rules TEXT NULL,
  source_template_type VARCHAR(100) NULL,
  notes TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_parsed_docs_run
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
    ON DELETE CASCADE,
  INDEX idx_parsed_docs_run_id (analysis_run_id),
  INDEX idx_parsed_docs_use_case_id (use_case_id),
  INDEX idx_parsed_docs_use_case_name (use_case_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS extracted_actors (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  actor_name VARCHAR(255) NOT NULL,
  actor_type VARCHAR(50) NULL,
  complexity VARCHAR(20) NOT NULL,
  weight_value INT NOT NULL,
  source_text TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_extracted_actors_run
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
    ON DELETE CASCADE,
  INDEX idx_extracted_actors_run_id (analysis_run_id),
  INDEX idx_extracted_actors_name (actor_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS extracted_use_cases (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  use_case_id VARCHAR(100) NULL,
  use_case_name VARCHAR(255) NOT NULL,
  complexity VARCHAR(20) NOT NULL,
  weight_value INT NOT NULL,
  transaction_count INT NULL,
  description TEXT NULL,
  source_kind VARCHAR(50) NULL,
  source_text TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_extracted_use_cases_run
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
    ON DELETE CASCADE,
  INDEX idx_extracted_use_cases_run_id (analysis_run_id),
  INDEX idx_extracted_use_cases_use_case_id (use_case_id),
  INDEX idx_extracted_use_cases_name (use_case_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS calculations (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  uaw DECIMAL(12, 2) NOT NULL,
  uucw DECIMAL(12, 2) NOT NULL,
  uucp DECIMAL(12, 2) NOT NULL,
  tcf DECIMAL(10, 4) NOT NULL,
  ecf DECIMAL(10, 4) NOT NULL,
  ucp DECIMAL(12, 2) NOT NULL,
  productivity_factor DECIMAL(10, 2) NOT NULL,
  effort_hours DECIMAL(12, 2) NOT NULL,
  person_days DECIMAL(12, 2) NOT NULL,
  team_size INT NOT NULL,
  schedule_months DECIMAL(12, 2) NOT NULL,
  sprint_count INT NOT NULL,
  recommended_team_size INT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_calculations_run
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
    ON DELETE CASCADE,
  INDEX idx_calculations_run_id (analysis_run_id),
  INDEX idx_calculations_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS run_logs (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  stage VARCHAR(100) NOT NULL,
  status VARCHAR(50) NOT NULL,
  message TEXT NULL,
  raw_output LONGTEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_run_logs_run
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
    ON DELETE CASCADE,
  INDEX idx_run_logs_run_id (analysis_run_id),
  INDEX idx_run_logs_stage (stage),
  INDEX idx_run_logs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Migration nhẹ cho database đã tạo từ phiên bản cũ.
-- Một số máy đã có bảng documents với raw_text NOT NULL.
-- Khi endpoint /ucp/calculate chỉ tính từ payload actor/use case thì không có raw_text gốc,
-- vì vậy cột này cần cho phép NULL để không chặn việc lưu calculation.
ALTER TABLE documents
  MODIFY raw_text LONGTEXT NULL;
