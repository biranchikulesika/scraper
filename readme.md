# SAMS Odisha Student Data Scraper

This script scrapes student data from the SAMS Odisha HSS (Higher Secondary School) website and stores it in a MySQL database.

## Prerequisites

- Python 3.7+
- A running MySQL server

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/biranchikulesika/scraper.git
    cd scraper
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Playwright browsers:**
    The scraper uses Playwright to control a web browser. You need to install the necessary browser binaries:
    ```bash
    playwright install
    ```

4.  **Configure Database Connection:**
    Update the `DB_CONFIG` dictionary in `scraper.py` with your MySQL database credentials.

    ```python
    DB_CONFIG = {
        "host": "your-mysql-host",
        "user": "your-mysql-user",
        "password": "your-mysql-password",
        "database": "your-mysql-database",
    }
    ```

5.  **Database Schema:**
    The script assumes a table named `students` and `institutes`. You will need to create these tables in your database.

    **`institutes` table:** This table should be pre-populated with the college names, SAMS codes, and a unique `institute_id`by running by running `python creaper.py`. The scraper uses this to look up and associate students with the correct institute.
    ```sql
    CREATE TABLE institutes (
        institute_id INT AUTO_INCREMENT PRIMARY KEY,
        sams_code VARCHAR   (50) UNIQUE,
        chse_code VARCHAR(50) UNIQUE,
        district_name VARCHAR(255),
        block_ulb VARCHAR(255),
        college_name VARCHAR(512) );
    ```

    **`students_test` table:** This is where the scraped student data is stored.
    ```sql
    CREATE TABLE students_test (
        id INT AUTO_INCREMENT PRIMARY KEY,
        reg_no VARCHAR(255),
        exam_roll_no VARCHAR(255),
        student_name VARCHAR(255),
        father_name VARCHAR(255),
        mother_name VARCHAR(255),
        gender VARCHAR(50),
        stream VARCHAR(100),
        year VARCHAR(50),
        district VARCHAR(100),
        college VARCHAR(255),
        institute_id INT,
        sams_code VARCHAR(255),
        updated_at DATETIME,
        UNIQUE KEY unique_student (year, institute_id, reg_no, exam_roll_no),
        FOREIGN KEY (institute_id) REFERENCES institutes(institute_id)
    );
    ```

## Usage

You can run the scraper from the command line, providing arguments to specify which data to scrape.

### Arguments

-   `year`: (Required) The academic year to scrape.
-   `district`: (Optional) A specific district to scrape. If omitted, all districts are scraped.
-   `college`: (Optional) A specific college to scrape. Requires `district` to be specified. If omitted, all colleges in the district are scraped.
-   `stream`: (Optional) A specific stream (e.g., "Arts", "Science"). Requires `college` to be specified. If omitted, all streams in the college are scraped.
-   `--verbose`: (Optional) Show more detailed logs during execution.
-   `--show-browser`: (Optional) Run the browser in non-headless mode, so you can see the automation.

### Examples

-   **Scrape all data for a specific year:**
    ```bash
    python scraper.py 2023
    ```

-   **Scrape all data for a specific district in a year:**
    ```bash
    python scraper.py 2023 Khurda
    ```

-   **Scrape a specific college:**
    ```bash
    python scraper.py 2023 Khurda "Buxi Jagabandhu Bidyadhar Higher Secondary School, Bhubaneswar"
    ```

-   **Scrape a specific stream in a college:**
    ```bash
    python scraper.py 2023 Khurda "Buxi Jagabandhu Bidyadhar Higher Secondary School, Bhubaneswar" Science
    ```

## Logging

The scraper creates a `logs` directory to store information about the scraping process:

-   `db_errors.log`: Logs any errors that occur during database operations (e.g., connection errors, commit failures).
-   `failed_rows.log`: Logs student data rows that failed to be inserted into the database. This is useful for debugging.
-   `college_name_mismatch.log`: Logs cases where the college name from the website doesn't exactly match a name in your `institutes` table, but a match was found through normalization (e.g., ignoring case and special characters). It also logs when no match can be found.
