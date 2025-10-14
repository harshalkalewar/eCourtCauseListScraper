# eCourt Cause List Scraper

A Python scraper using Selenium to extract daily cause lists from the Indian eCourts portal for specific districts and courts. The extracted data is saved both as a structured JSON file and a formatted PDF report.


## Features

    Selenium Automation: Navigates the eCourts portal to select State, District, Court Complex, and Court.

    Dynamic Date Input: Accepts a specific date for scraping the cause list.

    Captcha Handling: Uses Pillow and pytesseract for basic OCR to read and input the displayed captcha.

    Dual Output Format: Saves the extracted case data to:

        JSON: For easy data consumption and analysis.

        PDF: For a nicely formatted, printable report using reportlab.

## Prerequisites

Before running the scraper, you must have the following installed:

    Python 3.x
    Google Chrome Browser

## Installation

1. Install python dependencies 
````
    pip install -r requirements.txt
````

## Usage

1. Configuration

The scraper is controlled via the arguments passed to the scrape_cause_list function in the if __name__ == "__main__": block.

````
Update the following parameters to target the desired court and date:

Parameter	Type	Description	                                Example
state_name	str	Name of the State.	                       "Maharashtra"
dist	        str     Name of the District.	                       "Thane"
court_comp	str	Name of the Court Complex.	               "Thane, District and Sessions Court"
court	        str     Full name of the Court/Judge.	              "14-Rajendra Mansing Rathod..."
date	        str     The hearing date in DD-MM-YYYY format.	       "14-10-2025"
case_type	str	The type of case list ("civil" or "criminal").	 "criminal"
````


2. Run the script from your terminal:
````
python your_scraper_filename.py
````


## Output

The scraper will create a directory named data/ in the root of your project, and store the scraped files within it.

A typical output file structure will look like this:

````
.
├── data/
│   ├── case_data_2025-10-14_20-52-28.json
│   └── case_data_2025-10-14_20-52-28.pdf
└── your_scraper_file_name.py
````

## Key Components


def get_captcha(captcha_el, driver)

This function handles the crucial step of reading the captcha:

    Takes a screenshot of the specific captcha element (captcha_el).

    Performs image preprocessing (grayscale, thresholding) to clean the image.

    Uses pytesseract.image_to_string() with a configuration (--psm 7 for single line) to read the text.

    Deletes the temporary screenshot file.