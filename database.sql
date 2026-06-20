CREATE DATABASE IF NOT EXISTS resume_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE resume_ai;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL DEFAULT '',
  display_name VARCHAR(100) NOT NULL DEFAULT '',
  role VARCHAR(20) NOT NULL DEFAULT 'user',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  last_login_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  actor_user_id INT NULL,
  actor_username VARCHAR(100) NOT NULL DEFAULT '',
  action VARCHAR(100) NOT NULL,
  target_type VARCHAR(50) NOT NULL DEFAULT '',
  target_id INT NULL,
  detail_json LONGTEXT,
  ip_address VARCHAR(64) NOT NULL DEFAULT '',
  result VARCHAR(50) NOT NULL DEFAULT 'success',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_actor (actor_user_id),
  INDEX idx_audit_action (action),
  CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS job_profiles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  name VARCHAR(120) NOT NULL,
  category VARCHAR(100) NOT NULL DEFAULT '',
  target_position VARCHAR(120) NOT NULL DEFAULT '',
  description LONGTEXT,
  requirement_summary LONGTEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_job_profile_user (user_id),
  INDEX idx_job_profile_status (status),
  CONSTRAINT fk_job_profile_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS batch_tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  job_profile_id INT NULL,
  zip_filename VARCHAR(255) NOT NULL,
  total_files INT NOT NULL DEFAULT 0,
  success_count INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  summary_json LONGTEXT,
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_batch_user (user_id),
  INDEX idx_batch_job_profile (job_profile_id),
  CONSTRAINT fk_batch_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_batch_job_profile FOREIGN KEY (job_profile_id) REFERENCES job_profiles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS analysis_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  batch_task_id INT NULL,
  job_profile_id INT NULL,
  original_filename VARCHAR(255) NOT NULL,
  target_position VARCHAR(255) NOT NULL DEFAULT '',
  job_description LONGTEXT,
  total_score FLOAT NOT NULL DEFAULT 0,
  scores_json LONGTEXT,
  sections_json LONGTEXT,
  diagnosis_json LONGTEXT,
  suggestions_json LONGTEXT,
  match_result_json LONGTEXT,
  analysis_mode VARCHAR(50) NOT NULL DEFAULT 'offline',
  status VARCHAR(50) NOT NULL DEFAULT 'success',
  error_message LONGTEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_record_user (user_id),
  INDEX idx_record_batch (batch_task_id),
  INDEX idx_record_job_profile (job_profile_id),
  CONSTRAINT fk_record_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_record_batch FOREIGN KEY (batch_task_id) REFERENCES batch_tasks(id),
  CONSTRAINT fk_record_job_profile FOREIGN KEY (job_profile_id) REFERENCES job_profiles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS uploaded_files (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  analysis_record_id INT NULL,
  batch_task_id INT NULL,
  original_filename VARCHAR(255) NOT NULL,
  stored_path LONGTEXT NOT NULL,
  file_type VARCHAR(50) NOT NULL,
  file_size INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_file_user (user_id),
  INDEX idx_file_record (analysis_record_id),
  CONSTRAINT fk_file_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_file_record FOREIGN KEY (analysis_record_id) REFERENCES analysis_records(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reports (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  analysis_record_id INT NULL,
  batch_task_id INT NULL,
  report_type VARCHAR(50) NOT NULL DEFAULT 'single',
  format VARCHAR(20) NOT NULL,
  stored_path LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_report_user (user_id),
  INDEX idx_report_record (analysis_record_id),
  CONSTRAINT fk_report_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_report_record FOREIGN KEY (analysis_record_id) REFERENCES analysis_records(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO users (username, password_hash, display_name, role, status) VALUES ('guest', '', '游客', 'user', 'active');
