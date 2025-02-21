from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
from webdriver_manager.chrome import ChromeDriverManager
import re


def load_car_makes(file_path):
    carMakes = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header
        for index, row in enumerate(reader):
            if row:
                carMakes[row[0].strip().lower()] = index  # Store carMakes and their order
    return carMakes


# User enters desired pages to scrape
userPagesToScrape = int(input("How many pages would you like to scrape? (Enter a valid positive integer)"))

# Pick a time frame to search
timeFrame = input("Would you like to search 1: All Time, 2: Past 7 Days, 3: Past Month, 4: Past Year, 5: Past 2 Years, 6: Past 5 Years?")

# Load valid car makes and their order
valid_car_makes = load_car_makes('brands.csv')

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

# Initialize the Chrome driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.minimize_window()

# URL of the car auction website depending on user input
try:
    if timeFrame == '1':
        url = 'https://bringatrailer.com/auctions/results/?result=sold&exclude=parts+and+automobilia'
    elif timeFrame == '2':
        url = 'https://bringatrailer.com/auctions/results/?timeFrame=7D&result=sold&exclude=parts+and+automobilia'
    elif timeFrame == '3':
        url = 'https://bringatrailer.com/auctions/results/?timeFrame=30D&result=sold&exclude=parts+and+automobilia'
    elif timeFrame == '4':
        url = 'https://bringatrailer.com/auctions/results/?timeFrame=1Y&result=sold&exclude=parts+and+automobilia'
    elif timeFrame == '5':
        url = 'https://bringatrailer.com/auctions/results/?timeFrame=2Y&result=sold&exclude=parts+and+automobilia'
    elif timeFrame == '6':
        url = 'https://bringatrailer.com/auctions/results/?timeFrame=5Y&result=sold&exclude=parts+and+automobilia'
except Exception as e:
    print(f"Invalid Entry: {e}. Exiting Program.")

print("Navigating to the URL...")
driver.get(url)

# Wait for the auction items to load
wait = WebDriverWait(driver, 30)

cars = []
scraped_urls = set()
pages_to_scrape = userPagesToScrape  # Number of pages to scrape based on user input
current_page = 0  # Keep track of the current page

while current_page < pages_to_scrape:
    print(f"Scraping page {current_page + 1}...")

    print("Waiting for auction items to be visible...")
    # Scroll down to trigger lazy loading of items
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)  # Give some time for items to load

    try:
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'h3')))
        print("Auction items are now visible!")
    except Exception as e:
        print(f"Error waiting for items to load: {e}")
        break

    # Find all auction items
    car_elements = driver.find_elements(By.CSS_SELECTOR, 'a.listing-card')

    for index, car_element in enumerate(car_elements):
        try:
            # Get the car URL (to avoid reprocessing)
            car_url = car_element.get_attribute('href')

            # Skip cars that have already been scraped
            if car_url in scraped_urls:
                continue

            # Add the URL to the scraped set
            scraped_urls.add(car_url)

            # Debugging output to check which car element is being processed
            print(f"Processing car item {index + 1}/{len(car_elements)} on page {current_page + 1}...")

            # Find the car name inside h3
            car_name_elem = car_element.find_element(By.CSS_SELECTOR, 'h3')
            car_name = car_name_elem.text.strip() if car_name_elem else 'N/A'

            # Attempt to find the sale status
            sale_status = 'N/A'
            attempts = 5  # Increased number of attempts to locate the sale status
            for attempt in range(attempts):
                try:
                    sale_status_elem = car_element.find_element(By.CSS_SELECTOR, 'div.item-results')
                    sale_status = sale_status_elem.text.strip() if sale_status_elem else 'N/A'
                    break  # Exit the loop if the element was found
                except Exception as e:
                    print(f"Attempt {attempt + 1}: No sale status found for item {index + 1}: {e}")
                    time.sleep(1)  # Wait a bit before retrying

            # If we still don't have a sale status, scroll to this item for lazy loading
            if sale_status == 'N/A':
                driver.execute_script("arguments[0].scrollIntoView();", car_element)
                time.sleep(2)  # Wait for the lazy load to complete
                try:
                    sale_status_elem = car_element.find_element(By.CSS_SELECTOR, 'div.item-results')
                    sale_status = sale_status_elem.text.strip() if sale_status_elem else 'N/A'
                except Exception as e:
                    print(f"Second attempt for item {index + 1}: No sale status found: {e}")

            # If we still don't have a sale status, print the HTML for debugging
            if sale_status == 'N/A':
                print(f"Debug HTML for item {index + 1}: {car_element.get_attribute('outerHTML')}")

            # Extract sale price from the status
            sale_price = 'N/A'
            if "Sold for" in sale_status:
                sale_price_with_date = sale_status.split("Sold for")[1].strip()
                # Remove date from sale_price
                sale_price = sale_price_with_date.split(" on ")[0].strip()

            # Remove content before year
            car_name_cleaned = re.sub(r'^.*?(\d{4})', r'\1', car_name).strip()
            # The regex captures the year, and everything else as the car name
            car_match = re.match(r"(\d{4})\s+(.+)", car_name_cleaned)
            if car_match:
                year = car_match.group(1)
                make_and_model = car_match.group(2).strip()

                # Now split into make and model based on valid car makes
                make = ''
                model = ''

                # Try to find the longest matching make from the valid car makes
                for valid_make in valid_car_makes.keys():
                    if make_and_model.lower().startswith(valid_make):
                        make = valid_make
                        model = make_and_model[len(valid_make):].strip()
                        break

                # If no valid make was found, assign them to 'N/A'
                if not make:
                    year, make, model = 'N/A', 'N/A', 'N/A'
            else:
                year, make, model = 'N/A', 'N/A', 'N/A'

            # Append car details to the list without excluding any makes
            cars.append({
                'Year': year,
                'Make': make,
                'Model': model,
                'Sale Price': sale_price,
            })

        except Exception as e:
            print(f"Error parsing car details for item {index + 1}: {e}")
            continue

    # Check for the "Next" button and click it if available
    try:
        show_more = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.auctions-footer div.auctions-footer-content button')))
        if show_more.is_enabled():
            print("Scrolling to the 'Show More' button to ensure it's clickable...")
            driver.execute_script("arguments[0].scrollIntoView();", show_more)
            time.sleep(1)  # Wait for scrolling to complete

            # Use JavaScript to click the "Show More" button
            driver.execute_script("arguments[0].click();", show_more)
            time.sleep(5)  # Wait for the next page to load
            current_page += 1  # Increment the page counter
        else:
            print("No more pages to navigate.")
            break  # Exit the loop if no more pages are available
    except Exception as e:
        print(f"No 'Show More' button found or error occurred: {e}")
        break  # Exit the loop if there is an error

# Sort the cars list based on the order of makes in the valid_car_makes dictionary
sorted_cars = sorted(cars, key=lambda x: (valid_car_makes.get(x['Make'].strip().lower(), float('inf')), x['Model']))

# Write the scraped data to a CSV file
with open('bringATrailerSorted.csv', 'w', encoding='utf-8', newline='') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=['Year', 'Make', 'Model', 'Sale Price'])
    writer.writeheader()
    writer.writerows(sorted_cars)

driver.quit()
print("Scraping completed! Data saved to bringATrailerSorted.csv")
