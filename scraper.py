import mysql.connector
import time
import argparse
import os
import json
import re
from datetime import datetime
import sys
import traceback
from playwright.sync_api import sync_playwright, TimeoutError, Error as PlaywrightError

# ================= CONFIG =================

DB_CONFIG = {
    "host": "localhost",
    "user": "biranchi",
    "password": "biranchi",
    "database": "student_db",
}

BASE_URL = "https://hss.samsodisha.gov.in/newHSS/ReportCollegeWiseStudentDetails_Approved.aspx?MYx4BuYeE1G1NjtO83XBep3DRVEn1aNZYsg5QGBtTGc="

LOG_DIR = "logs"
DB_ERRORS_LOG = os.path.join(LOG_DIR, "db_errors.log")
FAILED_ROWS_LOG = os.path.join(LOG_DIR, "failed_rows.log")
COLLEGE_MISMATCH_LOG = os.path.join(LOG_DIR, "college_name_mismatch.log")


# ================= UI / UTILS =================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_status(message, status="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    ts_str = f"{Colors.CYAN}[{timestamp}]{Colors.ENDC}"

    if status == "INFO":
        label = f"{Colors.BLUE}[INFO]{Colors.ENDC} "
    elif status == "SUCCESS":
        label = f"{Colors.GREEN}[DONE]{Colors.ENDC} "
    elif status == "WARNING":
        label = f"{Colors.WARNING}[WARN]{Colors.ENDC} "
    elif status == "ERROR":
        label = f"{Colors.FAIL}[ERR ]{Colors.ENDC} "
    elif status == "HEADER":
        print(f"\n{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
        return
    else:
        label = f"{Colors.BLUE}[{status}]{Colors.ENDC}"

    print(f"{ts_str} {label} {message}")

def log(msg, level="INFO"):
    """Compatibility wrapper for execute_task logging."""
    print_status(msg, level if level in ["INFO", "ERROR", "WARNING", "SUCCESS"] else "INFO")

def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)

def write_json_line(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=str) + "\n")

def normalize_name(name):
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9 ]+", "", name)
    name = re.sub(r"\s+", " ", name)
    return name

def find_matching_options(available_options, search_term, field_name="Option"):
    """
    Returns a list of options from available_options that match the search_term.
    """
    clean_options = [opt.strip() for opt in available_options if opt.strip() and "--Select--" not in opt and "Select " not in opt]

    if not search_term:
        return clean_options

    search_lower = search_term.lower().strip()

    # 1. Try Exact Match
    exact_matches = [opt for opt in clean_options if opt.lower() == search_lower]
    if exact_matches:
        return exact_matches

    # 2. Try Partial Match
    partial_matches = [opt for opt in clean_options if search_lower in opt.lower()]

    if not partial_matches:
        print_status(f"Could not find {field_name} matching '{search_term}'.", "WARNING")
        return []

    return partial_matches


# ================= DISCOVERY =================

def discover_and_populate_tasks(page, args):
    """
    Navigates dropdowns to find new combinations and return a list of tasks.
    Returns a list of tuples: (year, district, college, stream)
    """
    print_status("Starting discovery of scraping tasks...", "HEADER")

    # --- 1. Year ---
    try:
        page.wait_for_selector("#ddlYear", timeout=30000)
    except:
        print_status("Failed to load initial page.", "ERROR")
        return []

    raw_years = page.locator("#ddlYear option").all_text_contents()

    # Support comma-separated years and ranges
    years_to_scan = []
    missing_years = []
    if args.year:
        tokens = [t.strip() for t in str(args.year).split(",") if t.strip()]
        for token in tokens:
            if ".." in token:
                parts = token.split("..")
                if len(parts) != 2:
                    print_status(f"Invalid year range '{token}'; expected format START..END.", "WARNING")
                    continue
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                except ValueError:
                    print_status(f"Invalid numbers in year range '{token}'.", "WARNING")
                    continue
                if start > end:
                    start, end = end, start
                for y in range(start, end + 1):
                    matches = find_matching_options(raw_years, str(y), "Year")
                    if matches:
                        years_to_scan.extend(matches)
                    else:
                        missing_years.append(str(y))
            else:
                matches = find_matching_options(raw_years, token, "Year")
                if matches:
                    years_to_scan.extend(matches)
                else:
                    missing_years.append(token)

        if missing_years:
            print_status(f"Could not find Year(s): {sorted(list(set(missing_years)))[:10]}...", "WARNING")

        years_to_scan = list(dict.fromkeys(years_to_scan))
    else:
        years_to_scan = find_matching_options(raw_years, args.year, "Year")

    if not years_to_scan:
        return []

    tasks = []
    for year in years_to_scan:
        print_status(f"Scanning Year: {year}", "HEADER")
        try:
            page.select_option("#ddlYear", label=year)
            time.sleep(1)
        except Exception as e:
            print_status(f"Failed to select year {year}: {e}", "WARNING")
            continue

        # --- 2. District ---
        page.wait_for_load_state("networkidle")
        raw_districts = page.locator("#ddlDistrict option").all_text_contents()
        districts_to_scan = find_matching_options(raw_districts, args.district, "District")

        for district in districts_to_scan:
            print_status(f"  > District: {district}", "INFO")
            try:
                page.select_option("#ddlDistrict", label=district)
                time.sleep(2)
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception as e:
                print_status(f"    Failed to select district {district}: {e}", "WARNING")
                continue

            # --- 3. College ---
            raw_colleges = []
            for attempt in range(3):
                try:
                    page.wait_for_selector("#ddlCollege", state="attached", timeout=10000)
                    raw_colleges = page.locator("#ddlCollege option").all_text_contents()
                    break
                except PlaywrightError as e:
                    if "Execution context was destroyed" in str(e) or "Navigating" in str(e):
                        print_status("    Page reloading detected, retrying college extraction...", "WARNING")
                        time.sleep(2)
                        continue
                    else:
                        print_status(f"    Error reading colleges: {e}", "ERROR")
                        break

            colleges_to_scan = find_matching_options(raw_colleges, args.college, "College")

            if args.college and not colleges_to_scan:
                continue

            print_status(f"    Found {len(colleges_to_scan)} matching colleges.", "INFO")

            for college in colleges_to_scan:
                try:
                    page.select_option("#ddlCollege", label=college)
                    time.sleep(2)
                    page.wait_for_load_state("networkidle", timeout=30000)
                except Exception as e:
                    print_status(f"    Failed to select college {college}: {e}", "WARNING")
                    continue

                # --- 4. Stream ---
                raw_streams = []
                for attempt in range(3):
                    try:
                        page.wait_for_selector("#ddlStream", state="attached", timeout=10000)
                        raw_streams = page.locator("#ddlStream option").all_text_contents()
                        break
                    except PlaywrightError as e:
                        if "Execution context" in str(e):
                            time.sleep(2)
                            continue
                        break

                streams_to_scan = find_matching_options(raw_streams, args.stream, "Stream")

                if streams_to_scan:
                    for stream in streams_to_scan:
                        tasks.append((year, district, college, stream))

    print_status("    Discovery phase complete.", "SUCCESS")
    return tasks


# ================= DB LOOKUP =================

def resolve_institute(cursor, college_name):
    # Exact match
    cursor.execute(
        "SELECT institute_id, sams_code, college_name FROM institutes WHERE college_name=%s",
        (college_name,),
    )
    row = cursor.fetchone()
    if row:
        return row[0], row[1]

    # Normalized fallback
    cursor.execute("SELECT institute_id, sams_code, college_name FROM institutes")
    site_norm = normalize_name(college_name)

    for iid, sams, db_name in cursor.fetchall():
        if normalize_name(db_name) == site_norm:
            write_json_line(
                COLLEGE_MISMATCH_LOG,
                {
                    "type": "NORMALIZED_MATCH",
                    "site_college_name": college_name,
                    "db_college_name": db_name,
                    "sams_code": sams,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            return iid, sams

    write_json_line(
        COLLEGE_MISMATCH_LOG,
        {
            "type": "NO_MATCH",
            "site_college_name": college_name,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    return None, None


# ================= EXECUTION =================

def print_task_summary(total, inserted, failed):
    if total == 0:
        print_status("No records found (Empty Table).", "WARNING")
    else:
        msg = f"Extracted: {total:<4} | Saved: {inserted:<4} | Failed: {failed:<4}"
        if failed > 0:
            print_status(msg, "WARNING")
        else:
            print_status(msg, "SUCCESS")

def execute_task(page, cursor, conn, task):
    year, district, college, stream = task

    # 1. Year
    page.select_option("#ddlYear", label=year)

    # 2. District
    page.select_option("#ddlDistrict", label=district)
    time.sleep(1)
    page.wait_for_load_state("networkidle")

    # 3. College
    page.select_option("#ddlCollege", label=college)
    time.sleep(1)
    page.wait_for_load_state("networkidle")

    # 4. Stream & Show
    page.select_option("#ddlStream", label=stream)
    page.click("#btnShow")

    try:
        page.wait_for_selector("#grdRptStd", timeout=20000)
    except TimeoutError:
        log(f"Table not found (Timeout waiting for #grdRptStd)", "INFO")
        print_task_summary(0, 0, 0)
        return

    if page.locator("#lbtnAll").count():
        log("Expanding all records...", "INFO")
        with page.expect_navigation(wait_until="networkidle"):
            page.click("#lbtnAll")

    institute_id, sams_code = resolve_institute(cursor, college)
    if not institute_id:
        log(f"Institute not found in DB for {college}", "ERROR")
        return

    rows = page.locator("#grdRptStd tr").all()[1:]
    batch = []

    for r in rows:
        c = r.locator("td").all_inner_texts()
        if len(c) < 7:
            continue
        batch.append(
            (
                c[1].strip(),  # reg_no
                c[2].strip(),  # exam_roll_no
                c[3].strip(),  # student_name
                c[4].strip(),  # father_name
                c[5].strip(),  # mother_name
                c[6].strip(),  # gender
                stream,
                year,
                district,
                college,
                institute_id,
                sams_code,
            )
        )

    if not batch:
        print_task_summary(0, 0, 0)
        return

    dedup = {}
    for r in batch:
        key = f"{r[7]}||{r[10]}||{r[0]}||{r[1]}"
        dedup[key] = r

    stmt = """
        INSERT INTO students_test
        (reg_no, exam_roll_no, student_name, father_name, mother_name,
         gender, stream, year, district, college, institute_id, sams_code, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        ON DUPLICATE KEY UPDATE
        student_name=VALUES(student_name),
        father_name=VALUES(father_name),
        mother_name=VALUES(mother_name),
        gender=VALUES(gender),
        stream=VALUES(stream),
        district=VALUES(district),
        college=VALUES(college),
        updated_at=NOW()
    """

    inserted = 0
    failed = 0
    failed_rows = []

    rows = list(dedup.values())
    for r in rows:
        try:
            cursor.execute(stmt, r)
            rc = cursor.rowcount
            if rc == 1:
                inserted += 1
        except Exception as e:
            failed += 1
            failed_rows.append(
                {
                    "error": str(e),
                    "row": r,
                    "college": college,
                    "stream": stream,
                    "timestamp": datetime.utcnow().isoformat(),
                    "trace": traceback.format_exc(),
                }
            )

    try:
        conn.commit()
    except Exception as e:
        log(f"DB Commit failed: {e}", "ERROR")

    if failed_rows:
        for fr in failed_rows:
            write_json_line(FAILED_ROWS_LOG, fr)

    print_task_summary(len(rows), inserted, failed)


# ================= MAIN =================

def main():
    start_time = time.time()  # Start the global timer

    parser = argparse.ArgumentParser(description="Odisha HSS Scraper")
    parser.add_argument("year", nargs="?", default=None)
    parser.add_argument("district", nargs="?", default=None)
    parser.add_argument("college", nargs="?", default=None)
    parser.add_argument("stream", nargs="?", default=None)
    parser.add_argument("--show-browser", action="store_true", help="Launch browser visible")
    args = parser.parse_args()

    ensure_log_dir()

    print_status("Initializing Scraper...", "HEADER")

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
    except mysql.connector.Error as e:
        print_status(f"DB Connect Error: {e}", "ERROR")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.show_browser)
        page = browser.new_page()

        try:
            print_status(f"Navigating to website...", "INFO")
            page.goto(BASE_URL, timeout=90000)
            page.wait_for_selector("#ddlYear", timeout=60000)
        except Exception as e:
            print_status(f"Failed to load website: {e}", "ERROR")
            browser.close()
            return

        tasks = discover_and_populate_tasks(page, args)

        if not tasks:
            print_status("No tasks found matching criteria.", "WARNING")
            return

        print_status(f"Queue contains {len(tasks)} tasks.", "HEADER")

        for i, task in enumerate(tasks, 1):
            year, district, college, stream = task
            print_status(f"Processing Task {i} of {len(tasks)}", "HEADER")
            print(f"    {Colors.BOLD}Target  :{Colors.ENDC} {college}")
            print(f"    {Colors.BOLD}Stream  :{Colors.ENDC} {stream}")
            print(f"    {Colors.BOLD}Context :{Colors.ENDC} {district} | {year}\n")

            try:
                execute_task(page, cursor, conn, task)
            except Exception as e:
                print_status(f"Task Crashed: {e}", "ERROR")
                try:
                    page.goto(BASE_URL, timeout=30000)
                    page.wait_for_selector("#ddlYear", timeout=30000)
                except:
                    pass

    try:
        cursor.close()
        conn.close()
    except:
        pass

    elapsed = time.time() - start_time
    m, s = divmod(elapsed, 60)
    h, m = divmod(m, 60)

    print_status(f"Scraping Session Finished. Total Time: {int(h)}h {int(m)}m {int(s)}s", "SUCCESS")

if __name__ == "__main__":
    main()
