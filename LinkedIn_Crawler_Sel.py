import os
os.chdir(r'C:\Users\andre\Documents\Python\Web_Scraper\Social_Media_Crawler_2023')
from crawler_functions import *
import credentials_file as cred

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.chrome.service import Service

import pyautogui

import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import time

import numpy as np
import pandas as pd
import re
from datetime import datetime, timedelta

# Settings
newpath = r"C:\Users\andre\OneDrive\Desktop\SSM_Energieanbieter"
os.chdir(newpath)
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
startpage = 'https://www.linkedin.com/login/de'
network = 'LinkedIn'
########################################################################################################################

# Login function
def login(username, password):
    WebDriverWait(driver,5).until(EC.presence_of_element_located((By.CSS_SELECTOR,'form.login__form')))
    nameslot = driver.find_element(By.CSS_SELECTOR, 'input#username')
    pwslot = driver.find_element(By.CSS_SELECTOR,'input#password')
    nameslot.clear()
#    nameslot.send_keys(cred.useremail_li)
    for char in username:
        nameslot.send_keys(char)
        time.sleep(.1)
    pwslot.clear()
    for char in password:
        pwslot.send_keys(char)
        time.sleep(.1)
    driver.find_element(By.XPATH, '//button[contains(text(), "Einloggen")]').click()
    time.sleep(2)


def scrapeProfile(company, link, date_str):
    p_name, follower, employees, last_post, desc1, desc2, tagline = ['' for _ in range(7)]
    driver.get(link)
    time.sleep(2)
    new_url = driver.current_url
    if new_url[-1] != '/':
        link = new_url.rsplit('/', 1)[0]
        driver.get(link)
        time.sleep(2)
        new_url = driver.current_url
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    not_used = 'wurde noch nicht in Anspruch genommen'
    if not_used in pagetext:
        return ['Seite ' + not_used, date_str, follower, employees, last_post, new_url, tagline, desc1, desc2]

    headers = driver.find_elements(By.TAG_NAME, 'h1')
    if headers:
        names = [h.text.strip() for h in headers]
        sel_names = [n for n in names if company[:4].strip().lower() in n.lower()]
        if len(sel_names) >= 1:
            p_name = sel_names[0]
        if p_name == '':
            if len(names) >= 1:
                p_name = names[0]
    else:
        headers = driver.find_elements(By.TAG_NAME, 'h2')
        names = [h.text.strip() for h in headers]
        for n in names:
            if company[:3].lower() in n.lower():
                p_name = n
    tagline_elem = soup.find('p', class_='org-top-card-summary__tagline')
    tagline = extract_text(tagline_elem)
    p_desc_elem = soup.find('div', class_='org-top-card-summary-info-list')
    desc1 = extract_text(p_desc_elem)
    if p_desc_elem:
        if 'beschäftigte' in desc1.lower():
            employees = desc1.rsplit('innen')[-1].replace('Beschäftigte', '').strip()
        p_list = desc1.split()
        for idx, e in enumerate(p_list):
            if 'follower' in str(e).lower():
                follower_elem = str(p_list[idx - 1]).strip()
                if not follower_elem.isdigit():
                    follower_elem = str(' '.join(p_list[idx - 2: idx])).strip()
                follower = extract_big_number(follower_elem)
    driver.get(new_url + 'about/')
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    info_elem = soup.find('div', class_='org-grid__content-height-enforcer')
    if not info_elem:
        info_elem = ' '.join([extract_text(e) for e in soup.find_all('section')])
    desc2 = str(extract_text(info_elem))
    if len(desc2) <= 4:
        info_elem = soup.find('dl', class_='overflow-hidden')
        desc2 = str(extract_text(info_elem))
    if len(desc2) <= 4:
        desc2 = pagetext
    if 'Übersicht' in desc2:
        desc2 = desc2.split('Übersicht', 1)[1].strip()
    driver.get(new_url + 'posts/?feedView=all')
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = str(get_visible_text(Comment, soup))
    posts = soup.find_all('div', class_='ember-view occludable-update')
    if len(posts) == 0 or "Noch keine Beiträge" in pagetext or len(pagetext) < 2200:
        last_post = 'Keine Beiträge'
        return [p_name, date_str, follower, employees, last_post, new_url, tagline, desc1, desc2]

    last_date_elem = posts[0].find('div', class_='ml4 mt2 text-body-xsmall t-black--light')
    if not last_date_elem:
        last_date_elem = posts[0].find('div', class_='t-black--light t-14')
    if last_date_elem:
        last_date_str = extract_text(last_date_elem)
        post_date_dt, last_post = get_approx_date(dt, last_date_str)
    return [p_name, date_str, follower, employees, last_post, new_url, tagline, desc1, desc2]
########################################################################################################################

# Further Settings
source_file = "Energieanbieter_Auswahl.xlsx"
df_source = pd.read_excel(source_file)
df_source.set_index('ID',inplace=True)
col_list = list(df_source.columns)
if 'Anbieter' in col_list:
    comph_header = 'Anbieter'
elif 'Firma' in col_list:
    comp_header = 'Firma'
comph2 = 'Name in Studie'
dt = datetime.now()
date_str = dt.strftime("%d.%m.%Y")
data = []


# Start crawling
driver = start_browser(webdriver, Service, chromedriver_path)
go_to_page(driver, startpage)
login(cred.useremail_li, cred.password_li)
# LinkedIn might require you to enter a confirmation code at this point for security reasons.


# Loop
count = 0
for id, row in df_source.iterrows():
    count += 1
    if count < 5:
        continue
    link = str(row[network])
    if len(link) < 10:
        print(link)
        continue
    break

    company = row['Firma']
    scraped_row = scrapeProfile(company, link, date_str)
    data.append([id,company] + scraped_row)
#    print(scraped_row)


# Create a DataFrame
header = ['ID', 'Anbieter', 'Profilname', 'Datum', 'Follower', 'Beschäftigte', 'Letzter Beitrag', 'Link', 'Tagline',
          'Beschreibung1', 'Beschreibung2']
df_profiles = pd.DataFrame(data, columns=header)


# Export to Excel
file_path = 'Profile_' + network + '.xlsx'
with pd.ExcelWriter(file_path) as writer:
    df_profiles.to_excel(writer, sheet_name='Profildaten')
#df_profiles.to_excel(filename_profiles)
########################################################################################################################

# Special functions for scraping the Posts
# Full scrolls (posts don't disappear)
# Only posts within a year are shown on the page
def scroll_to_bottom():
    start_height = driver.execute_script('return document.body.scrollHeight')
    new_height = ''
    safety_counter = 0
    while start_height != new_height and safety_counter <= 20:
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
        time.sleep(1)
        new_height = driver.execute_script('return document.body.scrollHeight')
        safety_counter += 1
########################################################################################################################

# Settings for the post crawler
source_file = "Profildaten_Energieanbieter_1.xlsx"
df_source = pd.read_excel(source_file, sheet_name=network)
df_source.set_index('ID',inplace=True)
dt = datetime.now()
dt_str = dt.strftime("%d.%m.%Y")
lower_dt = datetime.strptime('2022-10-31','%Y-%m-%d')
upper_dt = datetime.strptime('2023-11-01','%Y-%m-%d')

data_posts = []

new_path = r"C:\Users\andre\OneDrive\Desktop\SSM_Energieanbieter"
os.chdir(new_path)
datelimit_str = '31.10.2022'
datelimit = datetime.strptime(datelimit_str,'%d.%m.%Y')


# Start crawling
driver = start_browser(webdriver, Service, chromedriver_path)
go_to_page(driver, startpage)
login(cred.useremail_li, cred.password_li)

# Loop
for id, row in df_source.iterrows():
    if len(str(row['last post'])) <= 4 or str(row['last post']).strip() == 'Keine Beiträge':
        continue
    p_name = row['Profilname']
    url = row['url']
    print(id, p_name, url)

#def scrape_posts(p_name, url):
    driver.get(url + 'posts/?feedView=all')
    time.sleep(2)
    scroll_to_bottom()

# def scrape_links():
    linklist = []
    dropdown_buttons = driver.find_elements(By.CSS_SELECTOR,'svg[a11y-text="Kontrollmenü öffnen"]')

    dropdown_buttons[-1].click()

    # Wait for the dropdown to appear
    dropdown_selector = '.artdeco-dropdown__content-inner'
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, dropdown_selector)))

    # Locate the "Link zum Artikel kopieren" option by its visible text and click it
    try:
        link_selector = f'//div[contains(@class, "{dropdown_selector}")]/descendant::*[normalize-space(.)="Link zum Artikel kopieren"]'
        link_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, link_selector)))
        link_element.click()
    except:
        copy_link_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Link zum Artikel kopieren')]"))
        )

    # Selenium is unable to locate the Button responsible for copying the link

# This code ends here


########################################################################################################################
#if needed:
if driver.current_url == startpage:
    firstname = driver.find_element(By.CSS_SELECTOR, 'input#first-name')
    lastname = driver.find_element(By.CSS_SELECTOR, 'input#last-name')
    firstname.send_keys(firstname_li)
    lastname.send_keys(lastname_li)
    driver.find_element(By.XPATH, '//button[contains(text(), "Weiter")]').click()