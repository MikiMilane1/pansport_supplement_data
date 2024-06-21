import logging
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from functions import has_number

from selenium.common.exceptions import NoSuchElementException

chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option('detach', True)

driver = webdriver.Chrome(options=chrome_options)

driver.get('https://www.pansport.rs/proteini')

# GET NUMBER OF PAGES
pagination = driver.find_element(By.XPATH, "//ul[@class='pager']")
page_numbers = pagination.find_elements(By.XPATH, "./li")
page_numbers = [item.text for item in page_numbers if has_number(item.text)]
last_page = page_numbers[-1]

data = []

for page in range(int(last_page) + 1):
    driver.get(f"https://www.pansport.rs/proteini?page={page}")
    items_page = driver.current_url

    for n in range(50):
        content = driver.find_element(By.XPATH, "//div[@id='main-wrapper']/div/div/div")
        items = content.find_elements(By.CLASS_NAME, "product-teaser")
        try:
            items[n].click()
            item_url = driver.current_url

            price_and_package_section = driver.find_element(By.XPATH, "//div[@class='node-product-info-price-wrapper']")
            package_dropdown = Select(price_and_package_section.find_element(By.XPATH, "//select[1]"))

            package_options = package_dropdown.options

            # SELECT THE BIGGEST PACKAGE
            # CHECK IF THERE ARE PACKAGES IN KG AND GET THE LARGEST ONE
            product_package = "no_info"
            package_list = [item for item in package_options if " kg" in item.text]
            if package_list:
                max_option = package_list[0]
                for option in package_list:
                    if float(option.text.replace(" kg", "")) >= float(max_option.text.replace(" kg", "")):
                        max_option = option
                        product_package = float(max_option.text.replace(" kg", ""))
                    else:
                        print('exception with kg')
                        pass
            # NO PACKAGES IN KG, FIND THE LARGEST ONE
            else:
                max_option = package_options[0]
                for option in package_options:
                    if float(option.text.replace(" g", "")) >= float(max_option.text.replace(" g", "")):
                        max_option = option
                        # CONVERT THE PACKAGE UNIT SIZE FROM g TO kg
                        product_package = float(max_option.text.replace(" g", "")) / 1000
                    else:
                        print('exception with g')
                        pass
            package_dropdown.select_by_visible_text(max_option.text)
            time.sleep(2)

            # GET PRODUCT NAME
            product_name = driver.find_element(By.XPATH, "//div[@role='main']/h1").text

            # GET PRODUCT MANUFACTURER
            product_manufacturer = driver.find_element(By.XPATH, "//div[@class='node-taxonomy']").text.replace("\n", "").replace("Proizdo"
                                                                                                                                 "đač: ",
                                                                                                                                 '')

            # CHECK IF ON SALE
            try:
                sale_ribbon = driver.find_element(By.XPATH, "//div[@class='field-item image']/a[@class='ribbon-wrapper']")
                product_on_sale = True
            except NoSuchElementException:
                product_on_sale = False

            # GET PRODUCT PRICE
            if product_on_sale:
                try:
                    product_price_element = price_and_package_section.find_elements(By.TAG_NAME, "td")[1]
                except IndexError:
                    product_price_element = price_and_package_section.find_element(By.TAG_NAME, "td")
            else:
                product_price_element = price_and_package_section.find_element(By.TAG_NAME, "td")
            product_price = float(product_price_element.text.replace(" RSD", "").replace(".", "").replace(",", "."))

            # SCRAPE NUTRITION DATA
            nutrition_section = driver.find_element(By.XPATH, "//div[@property='content:encoded']")
            try:
                protein_cell = nutrition_section.find_element(By.XPATH, "//table/tbody/tr/td/p[contains(text(), 'Proteini')]")
                protein_row = protein_cell.find_element(By.XPATH, "../..")

                carbs_cell = nutrition_section.find_element(By.XPATH, "//table/tbody/tr/td/p[contains(text(), 'Ugljeni')]")
                carbs_row = carbs_cell.find_element(By.XPATH, "../..")

                protein_row_cells = [item.text for item in protein_row.find_elements(By.TAG_NAME, "td") if has_number(item.text)]
                carbs_row_cells = [item.text for item in carbs_row.find_elements(By.TAG_NAME, "td") if has_number(item.text)]
                try:
                    protein_per_100g = max(
                        [float(item.replace(" g", "").replace("g", "").replace(",", "."), ) for item in protein_row_cells])
                    carbs_per_100g = max(
                        [float(item.replace(" g", "").replace("g", "").replace(",", "."), ) for item in carbs_row_cells])
                except ValueError:
                    protein_row_cells = [item.split()[0] for item in protein_row_cells]
                    carbs_row_cells = [item.split()[0] for item in carbs_row_cells]
                    protein_per_100g = max(
                        [float(item.replace(" g", "").replace("g", "").replace(",", "."), ) for item in protein_row_cells])
                    carbs_per_100g = max(
                        [float(item.replace(" g", "").replace("g", "").replace(",", "."), ) for item in carbs_row_cells])

                # CALCULATE PRICE PER g OF PROTEIN
                price_per_g_protein = round(product_price / (10 * protein_per_100g * product_package), 2)
            except NoSuchElementException:
                protein_per_100g = 'no_info'
                price_per_g_protein = 'no_info'
                carbs_per_100g = 'no_info'

            df_entry = {"name": product_name,
                        'manufacturer': product_manufacturer,
                        "product_url": driver.current_url,
                        "package_weight": product_package,
                        "on_sale": product_on_sale,
                        "price": product_price,
                        "protein_per_100g": protein_per_100g,
                        "price_per_g_protein": price_per_g_protein,
                        "carbs_per_100g": carbs_per_100g,
                        }

            print(df_entry)

            data.append(df_entry)

            time.sleep(3)
            driver.get(items_page)
        except IndexError:
            pass

df = pd.DataFrame(data)
df.to_csv('scraped_data.csv', index=False)
