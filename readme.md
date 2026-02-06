# SAMS Odisha HSS Data Scraper

A robust, two-stage automated scraping system designed to extract Higher Secondary School (HSS) and student information from the SAMS Odisha portal. The system uses Playwright for browser automation and stores data in a structured MySQL database.

## 📌 Project Overview

The scraping process is divided into two mandatory phases:
1.  **Institute Scraping (`creaper.py`):** Collects a master list of all colleges, SAMS codes, and CHSE codes across Odisha.
2.  **Student Scraping (`scraper.py`):** Performs a deep-dive scrape of student details (Registration No, Roll No, etc.) based on the institutes discovered in phase one.

---

## 🛠️ Prerequisites

* **Python:** Version 3.7 or higher.
* **MySQL Server:** A running instance (local or remote).
* **Browsers:** Playwright requires specific browser binaries.

---

## ⚙️ Installation & Setup

### 1. Clone and Install
```bash
# Clone the repository
git clone https://github.com/biranchikulesika/scraper.git

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install

```

### 2. Database Configuration

You must update the database credentials in **both** `creaper.py` and `scraper.py`. Open the files and locate the `DB_CONFIG` dictionary:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "your_username",
    "password": "your_password",
    "database": "student_db",
}

```

### 3. Initialize Database Schema

Run the provided `schema.sql` in your MySQL environment to create the database, user, and necessary table structures (`institutes` and `students`).

---

## 🚀 Usage Guide

### Step 1: Populate Institutes (Mandatory First Step)

Before scraping student data, you must build the institute reference table. `scraper.py` relies on this table to resolve `institute_id` foreign keys.

Run the "Creaper":

```bash
python creaper.py

```

* **What it does:** Iterates through all districts from 2016 to 2026 and saves every unique college into the `institutes` table.
* **Wait time:** This can take a while as it navigates the entire state directory.

---

### Step 2: Scrape Student Data

Once the `institutes` table is populated, use `scraper.py` to get student details.

#### Command Syntax:

```bash
python scraper.py [year] [district] [college] [stream] [--show-browser]

```

#### Argument Details:

| Argument | Description | Example |
| --- | --- | --- |
| `year` | **Required.** Single year, comma-separated list, or range (`..`). | `2024` or `2022,2023` or `2020..2024` |
| `district` | **Optional.** Filter by a specific district name. | `Khurda` |
| `college` | **Optional.** Filter by a specific college name (requires District). | `"BJB Higher Secondary School"` |
| `stream` | **Optional.** Filter by "Arts", "Science", "Commerce", etc. | `Science` |
| `--show-browser` | **Optional.** Runs the scraper with a visible browser window. | `--show-browser` |

#### Practical Examples:

```bash
# Scrape all students in Odisha for the year 2024
python scraper.py 2024

# Scrape a range of years for a specific district
python scraper.py 2022..2024 Koraput

# Scrape a specific stream in one college
python scraper.py 2024 Khurda "Buxi Jagabandhu Bidyadhar Higher Secondary School" Science

```

---

### Step 3: Bulk Execution (Bash Script)

If you want to automate multiple years or districts in a loop, use the provided shell script:

1. Edit `students_scraper_shell_script.sh` to set your `DISTRICT` and `YEAR` range.
2. Run:
```bash
chmod +x students_scraper_shell_script.sh
./students_scraper_shell_script.sh

```



---

## 📂 Logging & Troubleshooting

Check the `logs/` directory for detailed execution reports:

* **`db_errors.log`**: Issues with MySQL connection or query execution.
* **`failed_rows.log`**: Student records that couldn't be saved (contains raw data for manual retry).
* **`college_name_mismatch.log`**: Critical log showing if a college name on the website didn't match the `institutes` table.
* **`institute_errors.log`**: Errors specifically generated during the `creaper.py` run.

### Common Errors:

* **TimeoutError:** The SAMS website is slow. The script has built-in retries, but check your internet connection.
* **Database Mismatch:** If `scraper.py` says "Institute not found," ensure you ran `creaper.py` successfully first.
* **District or College** are spelt different in some cases. Please refer to [SAMS Odisha Portal](https://hss.samsodisha.gov.in/newHSS/ReportCollegeWiseStudentDetails_Approved.aspx?MYx4BuYeE1G1NjtO83XBep3DRVEn1aNZYsg5QGBtTGc=) for the exact spelling. Or you can run the `creaper`, it will gather all the districts names along with college names. Which you then can use as parameters in `scraper.py`.