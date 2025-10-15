import sys

from selenium import webdriver
from selenium.common import TimeoutException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from datetime import datetime
from PIL import Image
import pytesseract
import time
import os
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def get_captcha(captcha_el, driver):

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", captcha_el)
    time.sleep(0.3)

    captcha_path = "captcha_element.png"
    captcha_el.screenshot(captcha_path)
    print("Saved captcha element screenshot to", captcha_path)

    img = Image.open(captcha_path)

    gray = img.convert("L")
    bw = gray.point(lambda x: 0 if x < 160 else 255, "1")

    raw_text = pytesseract.image_to_string(bw, config="--psm 7")

    try:
        os.remove(captcha_path)
        print("Deleted temporary file:", captcha_path)
    except OSError as e:
        print(f"Error deleting file {captcha_path}: {e}")

    return raw_text.strip()


def scrape_cause_list(state_name, dist, court_comp, court, date, case_type):

    # Initializing driver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)

    driver.get("https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/index&app_token=8c86faff375c072979d3b39239b94478fd94a2a54ecc415cd67aab81aae217be#")

    # Wait for the state dropdown to appear
    wait = WebDriverWait(driver, 25)
    state_dropdown = wait.until(ec.presence_of_element_located((By.ID, "sess_state_code")))

    # Closing the pop-up
    close_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-close[data-bs-dismiss='modal'][aria-label='Close']")
    driver.execute_script("arguments[0].click();", close_btn)

    # Selecting state
    state = driver.find_element(By.ID, "sess_state_code")
    select_state = Select(state)
    select_state.select_by_visible_text(state_name)

    # Selecting district
    wait.until(lambda d: len(Select(d.find_element(By.ID, "sess_dist_code")).options) > 1)
    district = driver.find_element(By.ID, "sess_dist_code")
    select_district = Select(district)
    select_district.select_by_visible_text(dist)

    # Selecting court complex
    wait.until(lambda d: len(Select(d.find_element(By.ID, "court_complex_code")).options) > 1)
    court_complex = driver.find_element(By.ID, "court_complex_code")
    select_court_complex = Select(court_complex)
    select_court_complex.select_by_visible_text(court_comp)

    #Selecting court name
    WebDriverWait(driver, 10)
    wait.until(lambda d: len(Select(d.find_element(By.NAME, "CL_court_no")).options) > 1)
    court_name = driver.find_element(By.NAME, "CL_court_no")
    select_court_name = Select(court_name)
    select_court_name.select_by_visible_text(court)

    # Setting date
    WebDriverWait(driver, 10)
    wait.until(ec.presence_of_element_located((By.ID, "causelist_date")))
    desired_date = datetime.today().strftime(date)
    date_input = driver.find_element(By.ID, "causelist_date")
    date_input.clear()
    date_input.send_keys(desired_date)

    wait = WebDriverWait(driver, 15)


    # Captcha handling
    WebDriverWait(driver, 20)
    captcha_el = wait.until(ec.presence_of_element_located((By.ID, "captcha_image")))
    captcha = get_captcha(captcha_el, driver)
    captcha_input = driver.find_element(By.ID, "cause_list_captcha_code")
    captcha_input.clear()
    captcha_input.send_keys(captcha)

    # Selecting case type i.e. Civil or criminal
    civil_button = driver.find_element(By.CSS_SELECTOR, "button[onclick=\"submit_causelist('civ')\"]")
    criminal_button = driver.find_element(By.CSS_SELECTOR, "button[onclick=\"submit_causelist('cri')\"]")
    WebDriverWait(driver, 10)

    # Closing the pop-up
    try:
        close_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-close[data-bs-dismiss='modal'][aria-label='Close']")
        if close_btn:
            driver.execute_script("arguments[0].click();", close_btn)
    except ElementNotInteractableException as e:
        print(e)


    if case_type == "civil":
        civil_button.click()
    else:
        criminal_button.click()

    # Error handling in case of Invalid captcha
    try:
        WebDriverWait(driver, 10).until(
            lambda d: (
                    d.find_elements(By.ID, "dispTable") or
                    "Invalid" in d.find_element(By.ID, "validateError").text
            )
        )

        error_elem = driver.find_element(By.ID, "validateError")
        error_text = error_elem.text.strip()

        if "Invalid" in error_text:
            print("Invalid Captcha Detected — Please try again.")
            driver.quit()
            sys.exit(1)

        print("Captcha accepted, proceeding...")

    except Exception as e:
        print(f"Session Timeout - Please try again.")
        driver.quit()
        sys.exit(1)


    # CAUSE LIST SCRAPING
    table = WebDriverWait(driver, 20).until(
        ec.presence_of_element_located((By.ID, "dispTable"))
    )

    cases_data = []
    cases_data_json = []
    rows = table.find_elements(By.XPATH, ".//tbody/tr")

    print("Scraping cause list")

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) == 4:
            # Column 1: Sr No
            sr_no = cols[0].text.strip()

            # Column 2: Case info (contains <a> and text)
            case_col = cols[1]
            case_link_elem = case_col.find_element(By.TAG_NAME, "a")
            onclick_attr = case_link_elem.get_attribute("onclick")

            # Extract the first parameter (case_id) from onclick using regex
            import re
            match = re.search(r"viewHistory\('([^']+)'", onclick_attr)
            case_id = match.group(1) if match else None

            # Extract visible case title text (e.g. "Sessions Case/378/2025")
            case_text = case_col.text.replace("View", "").strip()

            # Other columns
            party_name = cols[2].text.strip()
            advocate = cols[3].text.strip()

            # Add structured data
            cases_data.append([
                sr_no,
                case_text,
                case_id,
                party_name,
                advocate
            ])

            cases_data_json.append({
                "Sr_No": sr_no,
                "Case_Title": case_text,
                "Case_ID": case_id,
                "Party_Name": party_name,
                "Advocate": advocate
            })


    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Saving data to json
    json_filename = f"data/case_data_{timestamp}.json"
    os.makedirs("data", exist_ok=True)
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(cases_data_json, f, indent=4, ensure_ascii=False)
            print("Cause list saved as JSON file successfully.")
    except Exception as e:
        print(f"Error saving to JSON file: {e}")


    pdf_filename = f"data/case_data_{timestamp}.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = list()

    # Title
    elements.append(Paragraph("<b>District Court Cause List</b>", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Table header + data
    data = [["Sr No", "Case_Title", "Case", "Party Name", "Advocate"]] + cases_data

    table = Table(data, repeatRows=1, colWidths=[50, 150, 150, 300, 200])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
    ]))

    elements.append(table)
    doc.build(elements)
    print("Cause list saved as PDF file successfully.")

    driver.quit()


if __name__ == "__main__":
    scrape_cause_list("Maharashtra",
                      "Thane",
                      "Thane, District and Sessions Court",
                      "14-Rajendra Mansing Rathod-Ad-hoc Dist. Judge 3 and Addl. Sessions Judge Thane",
                      "15-10-2025",
                      "criminal"
                      )