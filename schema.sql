-- =====================================
-- Database creation
-- =====================================

CREATE DATABASE IF NOT EXISTS student_db
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE student_db;


-- =====================================
-- User creation
-- =====================================

CREATE USER IF NOT EXISTS 'your_username'@'localhost'
IDENTIFIED BY 'your_password';


-- =====================================
-- Privileges
-- =====================================

GRANT ALL PRIVILEGES
ON student_db.*
TO 'your_username'@'localhost';

FLUSH PRIVILEGES;


-- =====================================
-- Table: institutes
-- =====================================

CREATE TABLE IF NOT EXISTS `institutes` (
  `institute_id` int NOT NULL AUTO_INCREMENT,
  `sams_code` varchar(50) DEFAULT NULL,
  `chse_code` varchar(50) DEFAULT NULL,
  `district_name` varchar(255) DEFAULT NULL,
  `block_ulb` varchar(255) DEFAULT NULL,
  `college_name` varchar(512) DEFAULT NULL COMMENT 'Authoritative official institute name',
  PRIMARY KEY (`institute_id`),
  UNIQUE KEY `uq_sams_code` (`sams_code`),
  UNIQUE KEY `uq_chse_code` (`chse_code`),
  UNIQUE KEY `uq_institutes_sams` (`sams_code`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;


-- =====================================
-- Table: students
-- =====================================

CREATE TABLE IF NOT EXISTS `students` (
  `reg_no` varchar(255) NOT NULL,
  `exam_roll_no` varchar(255) NOT NULL,
  `student_name` varchar(255) DEFAULT NULL,
  `father_name` varchar(255) DEFAULT NULL,
  `mother_name` varchar(255) DEFAULT NULL,
  `gender` varchar(50) DEFAULT NULL,
  `stream` varchar(255) DEFAULT NULL,
  `year` varchar(50) NOT NULL,
  `district` varchar(255) DEFAULT NULL,
  `college` varchar(255) DEFAULT NULL,
  `institute_id` int NOT NULL,
  `sams_code` varchar(50) NOT NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY `idx_institute_year_roll` (`institute_id`, `year`, `exam_roll_no`),
  KEY `idx_students_sams_year` (`sams_code`, `year`),
  KEY `idx_students_sams_code` (`sams_code`),
  KEY `idx_students_year_stream` (`year`, `stream`),
  KEY `idx_students_district_year` (`district`, `year`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;
