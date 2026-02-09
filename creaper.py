import mysql.connector
import os
import json
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError

# ---------------- CONFIG ----------------

DB_CONFIG = {
    "host": "localhost",
    "user": "your_username",
    "password": "your_password",
    "database": "student_db",
}

BASE_URL = "https://hss.samsodisha.gov.in/newHSS/CollegeWiseApplicantReport_Approve.aspx?Ve2ybNQdDRr6P9jmGBzloH49u6Y1TUAy"

START_YEAR = 2016
END_YEAR = 2026

LOG_DIR = "logs"
ERROR_LOG = os.path.join(LOG_DIR, "institute_errors.log")

# ---------------- UI ----------------


class UI:
    INFO = "\033[94m[  INFO ]\033[0m"
    OK = "\033[92m[SUCCESS]\033[0m"
    WARN = "\033[93m[  WARN ]\033[0m"
    ERR = "\033[91m[ ERROR ]\033[0m"
    HDR = "\033[95m\033[1m"


def log(msg, level=UI.INFO):
    print(f"{level} {msg}")


# ---------------- UTILS ----------------


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def log_error(context, error):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "error": str(error),
    }
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def is_empty(val):
    return val is None or str(val).strip() == ""


# ---------------- DB ----------------


def insert_institutes(cur, conn, rows):
    insert_sql = """
        INSERT INTO institutes_test
        (sams_code, chse_code, district_name, block_ulb, college_name)
        VALUES (%s, %s, %s, %s, %s)
    """

    inserted = skipped = 0

    for r in rows:
        _, sams, chse, district, block, college = r

        if any(is_empty(x) for x in (sams, chse, district, block, college)):
            skipped += 1
            continue

        try:
            cur.execute("SELECT 1 FROM institutes_test WHERE sams_code=%s LIMIT 1", (sams,))
            if cur.fetchone():
                skipped += 1
                continue

            cur.execute(insert_sql, (sams, chse, district, block, college))
            conn.commit()
            inserted += 1

        except mysql.connector.Error as e:
            conn.rollback()
            skipped += 1
            log_error({"action": "insert", "sams": sams}, e)

    return inserted, skipped


# ---------------- SCRAPER ----------------


def extract_table(page):
    data = []

    if not page.locator("#grdView").count():
        return data

    table = page.locator("#grdView").first
    rows = table.locator("tr").all()[1:]

    for row in rows:
        cells = [c.strip() for c in row.locator("td").all_text_contents()]
        if len(cells) < 6:
            continue

        data.append(
            (
                cells[5],
                cells[1],
                cells[2],
                cells[3],
                cells[4],
                cells[5],
            )
        )

    return data


# ---------------- MAIN ----------------


def main():
    ensure_log_dir()
    log("Starting institute scraper", UI.HDR)

    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                log("Opening base URL")
                page.goto(BASE_URL, timeout=90000, wait_until="networkidle")
                page.wait_for_selector("#ddlDistrict", timeout=60000)

                districts = [
                    d.strip()
                    for d in page.locator("#ddlDistrict option").all_text_contents()
                    if d.strip() and "Select" not in d
                ]

                def small_wait():
                    page.wait_for_timeout(200)

                # ---------- ONE-TIME SHOW ALL INITIALIZATION ----------
                log("Initializing 'Show All' (one time)", UI.INFO)

                init_district = districts[0]
                init_year = END_YEAR

                page.select_option("#ddlDistrict", label=init_district)
                small_wait()

                with page.expect_navigation(wait_until="networkidle"):
                    page.select_option("#ddlYear", label=str(init_year))
                small_wait()

                with page.expect_navigation(wait_until="networkidle"):
                    page.click("#btnShow")

                with page.expect_navigation(wait_until="networkidle"):
                    page.locator("#lbtnAll").click()

                log("'Show All' initialized successfully", UI.OK)

                # ---------- NORMAL SCRAPING ----------
                for year in range(END_YEAR, START_YEAR - 1, -1):
                    log(f"\n===== YEAR {year} =====", UI.HDR)

                    for district in districts:
                        log(f"District: {district}")

                        for attempt in range(1, 4):
                            try:
                                page.select_option("#ddlDistrict", label=district)
                                small_wait()

                                with page.expect_navigation(wait_until="networkidle"):
                                    page.select_option("#ddlYear", label=str(year))
                                small_wait()

                                try:
                                    with page.expect_navigation(
                                        wait_until="networkidle"
                                    ):
                                        page.click("#btnShow")
                                except TimeoutError:
                                    pass

                                try:
                                    page.wait_for_selector(
                                        "#grdView .tblItem", timeout=20000
                                    )
                                except TimeoutError:
                                    log("No records", UI.WARN)
                                    break

                                rows = extract_table(page)
                                log(f"Extracted {len(rows)} rows")

                                ins, skip = insert_institutes(cur, conn, rows)
                                log(f"Inserted: {ins}, Skipped: {skip}", UI.OK)

                                break

                            except Exception as e:
                                log(f"Retry {attempt}/3 failed", UI.WARN)
                                log_error(
                                    {
                                        "district": district,
                                        "year": year,
                                        "attempt": attempt,
                                    },
                                    e,
                                )

                browser.close()

    log("Scraping completed successfully", UI.OK)


if __name__ == "__main__":
    main()