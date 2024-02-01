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

import os
# Settings
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
source_file = "Liste_Nahrungsergänzungsmittel_2024_Auswahl.xlsx"
branch_keywords = ['nutrition', 'vitamin', 'mineral', 'protein', 'supplement', 'diet', 'health', 'ernährung',
                   'ergänzung', 'gesundheit', 'nährstoff', 'fitness', 'sport', 'leistung']
startpage = 'https://www.linkedin.com/login/de'
platform = 'LinkedIn'
dt_str_now = None
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

def scrapeProfile(company, link):
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
        return ['Seite ' + not_used, follower, employees, last_post, new_url, tagline, desc1, desc2]

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
                follower = extract_every_number(follower_elem)
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
        return [p_name, follower, employees, last_post, new_url, tagline, desc1, desc2]

    last_date_elem = posts[0].find('div', class_='ml4 mt2 text-body-xsmall t-black--light')
    if not last_date_elem:
        last_date_elem = posts[0].find('div', class_='t-black--light t-14')
    if not last_date_elem:
        last_date_elem = posts[0].find('div', class_='update-components-text-view break-words')
    if last_date_elem:
        last_date_str = extract_text(last_date_elem)
        if '•' in last_date_str:
            last_date_str = last_date_str.split('•')[1].strip()
        post_date_dt, last_post = get_approx_date(dt, last_date_str)
    return [p_name, follower, employees, last_post, new_url, tagline, desc1, desc2]
########################################################################################################################

# Profile crawler
if __name__ == '__main__':
    # Settings for profile scraping
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    import credentials_file as cred
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)

    # Start crawling
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(cred.useremail_li, cred.password_li)
    # LinkedIn might require you to enter a confirmation code at this point for security reasons.

    # Loop
    count = 0
    for id, row in df_source.iterrows():
        count += 1
        if count >= 0:   # If you want to skip some rows
            continue
        company = extract_text(row[name_header])
        link = str(row[platform])
        if len(link) < 10:
            empty_row = [id, company, dt_str] + ['' for _ in range(8)]
            data.append(empty_row)
            print(empty_row)
            continue

        scraped_row = scrapeProfile(company, link)
        data.append([id, company, dt_str] + scraped_row)
        print([id, company, dt_str] + scraped_row)


    # Create a DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'follower', 'employees', 'last_post', 'link', 'tagline',
              'description1', 'description2']
    df_profiles = pd.DataFrame(data, columns=header)

    # Export to Excel
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()
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

def check_conditions(id, p_name, url, row, lower_dt, start_at=0):
    if id < start_at:      # If you want to skip some rows
        return False
    if len(p_name) == 0 or p_name.lower() == 'nan' or p_name == 'None':
        return False
    posts = str(row['last_post'])
    if len(url) < 10 or len(posts) <= 4 or 'Keine Beiträge' in posts:
        print([id, p_name, url])
        return False
    try:
        last_datestr = extract_text(row['last_post'])
        last_dt = datetime.strptime(last_datestr, "%d.%m.%Y")
        if (last_dt + timedelta(days=31)) < lower_dt:
            return False
        driver.get(url + 'posts/?feedView=all')
        time.sleep(2)
        return True
    except:
        return False

def scrape_post(p):
    post_date_dt = datetime.now()
    post_date = post_date_dt.strftime("%d.%m.%Y")
    link_elems = [a for a in p.find_all('a',href=True)]
    header_desc = [str(get_visible_text(Comment,a)).strip() for a in link_elems]
    date_elements = ['Std', 'Tag', 'Woche', 'Monat', 'Jahr']
    date_opt = [d for d in header_desc if any(e in d for e in date_elements)]
    if len(date_opt) > 0:
        date_str = date_opt[0]
        if '•' in date_str:
            date_str = date_str.split('•')[1].strip()
        try:
            post_date_dt, post_date = get_approx_date(post_date_dt, date_str)
        except:
            pass

    likes, comments, shares = ['' for _ in range(3)]
    react_elements = p.find_all('button', attrs={'aria-label': True})
    aria_labels = [a['aria-label'] for a in react_elements]
    for a in aria_labels:
        ptext = str(extract_text(a))
        num = extract_every_number(a)
        if 'Reaktionen' in ptext and likes == '':
            likes = num
        elif ' Kommentar' in a and comments == '':
            comments = num
        elif ' geteilt' in a or 'Veröffentlichungen' in a and shares == '':
            shares = num
    content_elem = p.find('span', class_='break-words')
    if content_elem:
        content = get_visible_text(Comment, content_elem)
    if not content_elem or len(str(content)) <= 4:
        content = get_visible_text(Comment, p)

    imagelinks = [e['src'] for e in p.find_all('img', src=True) if not 'company-logo' in e['src']]
    if p.find('video'):
        video, image = 1,0
    elif len(imagelinks) >= 1 or p.find('ul', class_='carousel-track') or p.find('iframe', src=True):
        image, video = 1,0
    else:
        image, video = 0,0
    link = ''
    result = [post_date, likes, comments, shares, image, video, link, content]
    return post_date_dt, result
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    # Settings for the post crawler
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    import credentials_file as cred
    os.chdir(file_path)
    file ='Profile_LinkedIn_2024'
    df_source, dt, dt_str, upper_dt, lower_dt = post_crawler_settings(file, platform, dt_str_now)

    # Current date
    upper_dt = datetime.now()

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(cred.useremail_li, cred.password_li)

    # Iterate over the companies
    for n, row in df_source.iterrows():
        id = row['ID']
        url = str(row['url'])
        p_name = str(row['profile_name'])
        go_crawl = check_conditions(n, p_name, url, row, lower_dt, start_at=27) # Start at the row 0
        if not go_crawl:
            continue
        scroll_to_bottom()
        soup = BeautifulSoup(driver.page_source, 'lxml')
        posts = soup.find_all('div', class_='ember-view occludable-update')
        if len(posts) == 0:
            continue

        data_per_company = []
        id_p = 0
        for count, p in enumerate(posts):
            post_dt, postdata = scrape_post(p)
            print(post_dt, postdata)
            if post_dt >= upper_dt:
                continue
            if post_dt < lower_dt:
                break
            id_p += 1
            full_row = [id, p_name, id_p, dt_str] + postdata
            data_per_company.append(full_row)

        all_data += data_per_company

        # Create a DataFrame with all posts
        header1 = ['ID_A', 'Profilname', 'ID_P', 'Datum_Erhebung', 'Datum_Beitrag']
        header2 = ['Likes', 'Kommentare', 'Shares', 'Bild', 'Video', 'Link', 'Content']
        dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

        # Export dfPosts to Excel (with the current time)
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_' + platform + dt_str_now + '.xlsx'
        dfPosts.to_excel(file_name)

    driver.quit()
########################################################################################################################
'''
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
'''
# header_desc = [str(a['aria-label']).strip() for a in p.find_all('a', {'aria-label': True})]
# header_desc = [a.text for a in p.find_all('a', {'aria-label': True})]