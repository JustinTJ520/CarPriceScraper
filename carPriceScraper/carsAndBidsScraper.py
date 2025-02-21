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
    makes = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header
        for index, row in enumerate(reader):
            if row:
                makes[row[0].strip().lower()] = index  # Store makes and their order
    return makes


# User enters desired pages to scrape
userPagesToScrape = int(input("How many pages would you like to scrape? (Enter a valid positive integer)"))
# Load valid car makes and their order
valid_car_makes = load_car_makes('brands.csv')
# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

# Initialize the Chrome driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# URL of the car auction website
url = 'https://carsandbids.com/past-auctions/'

print("Navigating to the URL...")
driver.get(url)

# Wait for the auction items to load
wait = WebDriverWait(driver, 30)

cars = []
pages_to_scrape = userPagesToScrape  # Number of pages to scrape
current_page = 0  # Keep track of the current page

while current_page < pages_to_scrape:
    print(f"Scraping page {current_page + 1}...")

    print("Waiting for auction items to be visible...")
    # Scroll down to trigger lazy loading of items
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)  # Give some time for items to load

    # Wait until auction items are visible
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'li.auction-item')))
    print("Auction items are now visible!")

    # Find all auction items
    car_elements = driver.find_elements(By.CSS_SELECTOR, 'li.auction-item')

    for index, car_element in enumerate(car_elements):
        try:
            # Debugging output to check which car element is being processed
            print(f"Processing car item {index + 1}/{len(car_elements)} on page {current_page + 1}...")

            # Find the car name inside div.auction-title > a
            car_name_elem = car_element.find_element(By.CSS_SELECTOR, 'div.auction-title a')
            car_name = car_name_elem.text.strip() if car_name_elem else 'N/A'

            # Attempt to find the sale status
            sale_status = 'N/A'
            attempts = 5  # Increased number of attempts to locate the sale status
            for attempt in range(attempts):
                try:
                    sale_status_elem = car_element.find_element(By.CSS_SELECTOR, 'span.value')
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
                    sale_status_elem = car_element.find_element(By.CSS_SELECTOR, 'span.value')
                    sale_status = sale_status_elem.text.strip() if sale_status_elem else 'N/A'
                except Exception as e:
                    print(f"Second attempt for item {index + 1}: No sale status found: {e}")

            # If we still don't have a sale status, print the HTML for debugging
            if sale_status == 'N/A':
                print(f"Debug HTML for item {index + 1}: {car_element.get_attribute('outerHTML')}")

            # Check for "Bid to" or "Canceled" and skip if present
            if "Bid to" in sale_status or "Canceled" in sale_status:
                print(f"Skipping car item {index + 1}: Sale status indicates a bid or cancellation.")
                continue

            # Extract sale price from the status
            sale_price = 'N/A'
            if "Sold for" in sale_status:
                sale_price = sale_status.split("Sold for")[1].strip()

            # Regex to separate year, make, and model with descriptors
            # The regex captures the year, and everything else as the car name
            car_match = re.match(r"(\d{4})\s+(.+)", car_name)
            if car_match:
                year = car_match.group(1)
                make_and_model = car_match.group(2).strip()

                # Split into make and model based on valid car makes
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
        next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'ul.paginator li.arrow.next button')))
        if next_button.is_enabled():
            print("Scrolling to the 'Next' button to ensure it's clickable...")
            driver.execute_script("arguments[0].scrollIntoView();", next_button)
            time.sleep(1)  # Wait for scrolling to complete

            # Use JavaScript to click the "Next" button
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(5)  # Wait for the next page to load
            current_page += 1  # Increment the page counter
        else:
            print("No more pages to navigate.")
            break  # Exit the loop if no more pages are available
    except Exception as e:
        print(f"No 'Next' button found or error occurred: {e}")
        break  # Exit the loop if there is an error

# Sort the cars list based on the order of makes in the valid_car_makes dictionary
sorted_cars = sorted(cars, key=lambda x: (valid_car_makes.get(x['Make'].strip().lower(), float('inf')), x['Model']))

# Write the scraped data to a CSV file
with open('carsAndBidsSorted.csv', 'w', encoding='utf-8', newline='') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=['Year', 'Make', 'Model', 'Sale Price'])
    writer.writeheader()
    writer.writerows(sorted_cars)

driver.quit()
print("Scraping completed! Data saved to carsAndBidsSorted.csv")
