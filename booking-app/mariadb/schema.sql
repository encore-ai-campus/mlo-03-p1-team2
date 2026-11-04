CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(36) PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  password_hash CHAR(64) NOT NULL,
  salt CHAR(32) NOT NULL,
  mbti CHAR(4) NOT NULL,
  consent TINYINT NOT NULL,
  consented_at VARCHAR(40) NOT NULL,
  created_at VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS sessions (
  token_hash CHAR(64) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  expires_at VARCHAR(40) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS performances (
  id VARCHAR(100) PRIMARY KEY,
  title TEXT NOT NULL,
  data LONGTEXT NOT NULL,
  sort_order INT NOT NULL,
  CHECK (JSON_VALID(data))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS reservations (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  performance_id VARCHAR(100) NOT NULL,
  performance_title TEXT NOT NULL,
  category TEXT NOT NULL,
  venue TEXT NOT NULL,
  performance_date VARCHAR(10) NOT NULL,
  session_time VARCHAR(10) NOT NULL,
  seat_grade VARCHAR(8) NOT NULL CHECK (seat_grade IN ('STANDARD','PREMIUM')),
  quantity INT NOT NULL CHECK (quantity BETWEEN 1 AND 4),
  unit_price INT NOT NULL,
  amount INT NOT NULL CHECK (amount >= 0),
  mbti CHAR(4) NOT NULL,
  status VARCHAR(10) NOT NULL CHECK (status IN ('REQUESTED','CONFIRMED','CANCELLED')),
  request_key CHAR(36) NOT NULL,
  created_at VARCHAR(40) NOT NULL,
  updated_at VARCHAR(40) NOT NULL,
  cancelled_at VARCHAR(40),
  UNIQUE (user_id, request_key),
  INDEX reservations_user (user_id, created_at),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (performance_id) REFERENCES performances(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS payments (
  id VARCHAR(36) PRIMARY KEY,
  reservation_id VARCHAR(36) NOT NULL UNIQUE,
  amount INT NOT NULL CHECK (amount >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'KRW',
  status VARCHAR(10) NOT NULL CHECK (status IN ('PENDING','COMPLETED','CANCELLED')),
  requested_at VARCHAR(40) NOT NULL,
  completed_at VARCHAR(40),
  cancelled_at VARCHAR(40),
  updated_at VARCHAR(40) NOT NULL,
  FOREIGN KEY (reservation_id) REFERENCES reservations(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS events (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  mbti CHAR(4) NOT NULL,
  performance_id VARCHAR(100) NOT NULL,
  reservation_id VARCHAR(36),
  type VARCHAR(40) NOT NULL,
  created_at VARCHAR(40) NOT NULL,
  INDEX events_analysis (performance_id, type, created_at),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (performance_id) REFERENCES performances(id),
  FOREIGN KEY (reservation_id) REFERENCES reservations(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS status_history (
  id VARCHAR(36) PRIMARY KEY,
  reservation_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  entity VARCHAR(20) NOT NULL,
  from_status VARCHAR(10),
  to_status VARCHAR(10) NOT NULL,
  created_at VARCHAR(40) NOT NULL,
  INDEX history_reservation (reservation_id, created_at),
  FOREIGN KEY (reservation_id) REFERENCES reservations(id),
  FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS api_write_lock (
  id INT PRIMARY KEY CHECK (id=1)
) ENGINE=InnoDB;

INSERT INTO api_write_lock (id) VALUES (1) ON DUPLICATE KEY UPDATE id=VALUES(id);
