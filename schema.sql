-- Optional: manual MySQL setup (the app can also create tables with `python seed.py`)
CREATE DATABASE IF NOT EXISTS placement_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE placement_db;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(10) NOT NULL DEFAULT 'student',
  roll_no VARCHAR(30) UNIQUE,
  department VARCHAR(80),
  cgpa FLOAT,
  phone VARCHAR(20),
  resume_link VARCHAR(255)
);
CREATE TABLE companies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  description TEXT,
  website VARCHAR(200)
);
CREATE TABLE jobs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  title VARCHAR(150) NOT NULL,
  description TEXT,
  eligibility_cgpa FLOAT NOT NULL DEFAULT 0,
  package_lpa FLOAT,
  location VARCHAR(100),
  deadline DATE NOT NULL,
  posted_on DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
CREATE TABLE applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  job_id INT NOT NULL,
  status VARCHAR(15) NOT NULL DEFAULT 'Applied',
  applied_on DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_student_job UNIQUE (student_id, job_id),
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);
