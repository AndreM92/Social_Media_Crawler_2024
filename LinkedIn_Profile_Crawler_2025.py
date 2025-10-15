
import os
import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import time
import pandas as pd
import re
from datetime import datetime, timedelta

# Settings
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
startpage = 'https://www.linkedin.com/login/de'
platform = 'LinkedIn'
dt_str_now = None

upper_datelimit = '2025-10-01'
file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_Mineralwasser 2025'
file_name = 'Auswahl SMP Mineralwasser_2025-10-14'
file_type = '.xlsx'
source_file = file_path + '/' + file_name + file_type
branch_keywords = [
    'Abfüll', 'Getränk', 'Lebensmittel', 'PET-', 'Flasche', 'Etikett', 'Dosier', 'Wasser', 'Mineral', 'Füllstand',
    'Verpackung', 'Trink', 'Durst']
########################################################################################################################

# Login function
def login(username, password, driver):
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
    try:
        from credentials_file import *
    except:
        useremail_li = str(input('Enter your user-email:')).strip()
        password_li = str(input('Enter your password:')).strip()
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)
    col_list = list(df_source.columns)

    # Open the browser, go to the startpage and login
    data = []
    start_ID = 0
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(useremail_li, password_li, driver)
    input('Press ENTER after the page is loaded')

    # Loop through the profiles
    for ID, row in df_source.iterrows():
        if 'ID' in col_list and col_list[0] != 'ID':
            ID = int(row['ID'])
        elif not 'nan' in str(ID):
            ID = int(ID)
        if ID < start_ID:  # If you want to skip some rows
            continue

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
            login(useremail_li, password_li, driver)
            scraped_row = scrapeProfile(company, link)

        data.append([ID, company, dt_str] + scraped_row)
        start_ID = ID + 1
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