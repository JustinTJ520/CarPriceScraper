import requests
from bs4 import BeautifulSoup
import csv


def scrape_page(soup, brands):
    # retrieving all the brand <dd> HTML elements on the page
    brandElements = soup.select('div.vw-column-shortcode p')

    # iterating over the list of brand elements
    for brandElement in brandElements:
        carBrand = brandElement.text.strip()
        brands.append(carBrand)


# the url of the home page of the target website
base_url = 'https://www.webbikeworld.com/motorcycle-brands/all-brands/#block-wrap-31504'

# defining the User-Agent header to use in the GET request below
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

# retrieving the target web page
page = requests.get(base_url, headers=headers)

# parsing the target web page with Beautiful Soup
soup = BeautifulSoup(page.text, 'html.parser')

# initializing the variable that will contain
# the list of all brand data
brands = []

# scraping the home page
scrape_page(soup, brands)

# writing the brand names to "brands.csv"
with open('motorcycleBrands.csv', 'w', encoding='utf-8', newline='') as csv_file:
    writer = csv.writer(csv_file)

    # writing the header of the CSV file
    writer.writerow(['Brand'])

    # writing each row of the CSV
    for brand in brands:
        writer.writerow([brand])  # Wrap brand in a list to write it correctly

print("Scraping complete. Brands saved to 'motorcycleBrands.csv'.")
