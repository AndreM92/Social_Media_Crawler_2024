
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
startpage = 'https://www.linkedin.com/login/de'
platform = 'LinkedIn'
dt_str_now = None
upper_datelimit = '2025-08-01'

upper_datelimit = '2025-08-01'
file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_Automatisierungstechnik 2025'
file_name = 'Auswahl_SMP Automatisierungstechnik 2025-08-01'
file_type = '.xlsx'
source_file = file_path + '/' + file_name + file_type
branch_keywords = ['Automatisierung', 'System', 'Technik', 'Maschine', 'Industrie', 'Automation', 'Technologie',
                   'Technology', 'Roboter', 'Steuerung', 'technik']
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

def find_post_date(p):
    date_elements = ['Min', 'Std', 'Tag', 'Woche', 'Monat', 'Jahr']
    span_elems = p.find_all('span')
    for e in span_elems:
        if any(d in str(e) for d in date_elements):
            date_str = get_visible_text(Comment, e)
            if '•' in date_str:
                date_str = date_str.split('•')[1].strip()
            try:
                post_date_dt, last_post = get_approx_date(datetime.now(), date_str)
                break
            except:
                pass
    return post_date_dt, last_post

def find_exact_follower(p):
    post_text = extract_text(p)
    text_list = post_text.split()
    for pos, t in enumerate(text_list):
        if 'Follower' in t:
            exact_follower = extract_number(text_list[pos-1])
            return exact_follower
    return None


def scrapeProfile(company, link):
    p_name, follower, employees, last_post, desc1, desc2, tagline = ['' for _ in range(7)]
    driver.get(link)
    time.sleep(2)
    new_url = driver.current_url
    if new_url[-1] != '/':
        link = new_url.rsplit('/', 1)[0]
    if driver.current_url != link:
        driver.get(link)
        time.sleep(2)
    url_adds = ['posts/','about/','people/','?feedView=all', '?originalSubdomain=de']
    for u in url_adds:
        new_url = new_url.replace(u,'')
        if driver.current_url != new_url:
            driver.get(new_url)
            time.sleep(2)
    if '?' in new_url:
        new_page = new_url.split('?')[0]
        try:
            driver.get(new_page)
            time.sleep(2)
        except:
            pass
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

    p = posts[0]
    link_elems = [a for a in p.find_all('a', href=True)]
    header_desc = [str(get_visible_text(Comment, a)).strip() for a in link_elems]
    if len(header_desc) >= 1:
        for h in header_desc:
            if 'Follower' in str(h):
                desc1 = str(h) + '; ' + desc1
                break
    post_date_dt, last_post = find_post_date(posts[0])
    exact_follower = find_exact_follower(p)
    if exact_follower:
        follower = exact_follower

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
    old_ID = 0
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(cred.useremail_li, cred.password_li)
    # LinkedIn might require you to enter a confirmation code at this point for security reasons.

    # Loop
    for n, row in df_source.iterrows():
        ID = n
        if isinstance(ID,(int,float)) and (ID <= old_ID or ID > 9999):   # If you want to skip some rows
            continue
        old_ID = ID
        company = extract_text(row[name_header])
        link = str(row[platform])
        if len(link) < 10:
            empty_row = [ID, company, dt_str] + ['' for _ in range(8)]
            data.append(empty_row)
            print(empty_row)
            continue
        try:
            scraped_row = scrapeProfile(company, link)
        except Exception as e:
            print(f"Error: {e}")
            driver.quit()
            time.sleep(3)
            driver = start_browser(webdriver, Service, chromedriver_path)
            go_to_page(driver, startpage)
            login(cred.useremail_li, cred.password_li)
            scraped_row = scrapeProfile(company, link)

        data.append([ID, company, dt_str] + scraped_row)
        print([ID, company, dt_str] + scraped_row)

    # Create a DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'follower', 'employees', 'last_post', 'url', 'tagline',
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

def check_conditions(id, p_name, row, lower_dt, start_at=0):
    if id < start_at:      # If you want to skip some rows
        return False
    if len(p_name) == 0 or p_name.lower() == 'nan' or p_name == 'None':
        return False
    url = str(row['url'])
    last_post = row['last_post']
    if len(url) < 10 or 'Keine Beiträge' in str(last_post):
        return False
    if not isinstance(last_post, datetime):
        last_datestr = extract_text(last_post)
        try:
            last_post = datetime.strptime(last_datestr, "%d.%m.%Y")
        except:
            print([id, url, 'no posts'])
            return False
#    if not last_datestr or len(url) < 10 or len(last_posts) <= 4 or 'Keine Beiträge' in last_posts:
    if (lower_dt - timedelta(days=31)) > last_post:
        return False
    try:
        driver.get(url + 'posts/?feedView=all')
        time.sleep(2)
    except:
        return False
    return True


def scrape_post(p):
    post_date_dt, post_date = find_post_date(p)
    likes, comments, shares = ['' for _ in range(3)]
    post_text = get_visible_text(Comment, p)
    react_elements = p.find_all('button', attrs={'aria-label': True})
    aria_labels = [a['aria-label'] for a in react_elements]
    for a in aria_labels:
        ptext = extract_text(a)
        if not ptext:
            continue
        num = extract_every_number(ptext.split()[0])
        if 'Reaktionen' in ptext and likes == '':
            likes = num
        elif ' Kommentar' in a and comments == '':
            comments = num
            if str(comments)[-1] == '.':
                comments = extract_number(comments)
        elif ' geteilt' in a or 'Veröffentlichungen' in a and shares == '':
            shares = num
            if str(shares)[-1] == '.':
                shares = extract_number(shares)
    if 'Menü' in str(likes):
        likes = ''
    if not likes and '1 Gefällt' in post_text:
        likes = 1
    if not shares and 'direkt geteilter' in post_text:
        shares = 1

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
    files = os.listdir()
    for e in files:
        if 'Profile_LinkedIn_2025' in str(e):
            file = extract_text(e)
            break
    file ='Profile_LinkedIn_2025-04-06'

#    dt_str_now = None
    df_source, dt, dt_str, upper_dt, lower_dt = post_crawler_settings(file, platform, dt_str_now, upper_datelimit)
    current_id = 0

    # Current date
    upper_dt = datetime.now()

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(cred.useremail_li, cred.password_li)

    old_id = 0
    # Iterate over the companies
    for n, row in df_source.iterrows():
        id = row['ID']
        url = str(row['url'])
        p_name = str(row['profile_name'])
        go_crawl = check_conditions(n, p_name, row, lower_dt, start_at=old_id) # Start at the row 0
        if not go_crawl:
            continue
        old_id = id

        scroll_to_bottom()
        soup = BeautifulSoup(driver.page_source, 'lxml')
        posts = soup.find_all('div', class_='ember-view occludable-update')
#        if len(posts) == 0:
#            continue
        data_per_company = []
        id_p = 0
        for count, p in enumerate(posts):
            extract_text(p)
            post_dt, postdata = scrape_post(p)
            print(postdata)
            if post_dt >= upper_dt:
                continue
            if post_dt < lower_dt:
                break
            id_p += 1
            full_row = [id, p_name, id_p, dt_str] + postdata
            data_per_company.append(full_row)

        all_data += data_per_company

        # Create a DataFrame with all posts
        header1 = ['ID_A', 'Profilname', 'ID_P', 'Erhebung', 'Datum']
        header2 = ['Likes', 'Kommentare', 'Shares', 'Bild', 'Video', 'Link', 'Content']
        dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

        # Export dfPosts to Excel (with the current time)
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_' + platform + '_' + dt_str_now + '.xlsx'
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