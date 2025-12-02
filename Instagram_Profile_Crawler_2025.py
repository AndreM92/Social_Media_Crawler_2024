
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
startpage = 'https://www.instagram.com/'
platform = 'Instagram'

upper_datelimit = '2025-12-01'
folder_name = "SMP_Glücksspiel_2025"
file_name = "Auswahl SMP Glücksspiel_2025-12-01"
file_path = r"C:\Users\andre\OneDrive\Desktop/" + folder_name
source_file = file_name + ".xlsx"
########################################################################################################################

def remove_insta_cookies():
    cookiebuttons = driver.find_elements('xpath', "//*[contains(text(), 'Jetzt nicht') or contains(text(), 'jetzt nicht')]")
    if len(cookiebuttons) >= 1:
        for c in cookiebuttons:
            try:
                c.click()
            except:
                pass

# Login function
def login(username, password):
    WebDriverWait(driver,5).until(EC.presence_of_element_located((By.XPATH,'//*[@id="loginForm"]/div/div[1]/div/label/input')))
    try:
        nameslot = driver.find_element(By.CSS_SELECTOR,'input[aria-label*="Benutzername"]')
    except:
        nameslot = driver.find_element('xpath', '//*[@id="loginForm"]/div/div[1]/div/label/input')
    pwslot = driver.find_element(By.CSS_SELECTOR,'input[aria-label*="Passwort"]')
    nameslot.clear()
    # Typing char for char to simulate a human like behavior
    # classic and global version:
    # nameslot.send_keys(cred.username_insta)
    for char in username:
        nameslot.send_keys(char)
        time.sleep(.1)
    pwslot.clear()
    for char in password:
        pwslot.send_keys(char)
        time.sleep(.1)
    driver.find_element('xpath', "//*[text()='Anmelden']").click()
    for _ in range(7):
        time.sleep(2)
        remove_insta_cookies()

# This function scrapes the details of every profile
def scrapeProfile(url, comp_keywords):
    driver.get(url)
    p_name, total_posts, follower, last_post, new_url, desc = ['' for _ in range(6)]
    time.sleep(4)
    new_url = driver.current_url
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = str(get_visible_text(Comment, soup))
    broken_profile = ['nicht verfügbar', 'Eingeschränktes Profil', 'Konto ist privat', 'Seite wurde entfernt', "isn't available"]
    for m in broken_profile:
        if m in pagetext:
            p_name = m
            print(m)
            return [p_name, total_posts, follower, last_post, new_url, desc]

    full_desc = get_visible_text(Comment, soup.find('header'))
    if not full_desc or len(full_desc) <= 100:
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
        full_desc = get_visible_text(Comment, soup.find('header'))
    if not platform.lower() + '.com' in driver.current_url:
        p_name = 'Wrong page'
        return [p_name, total_posts, follower, last_post, new_url, desc]

    headers = [h.text for h in driver.find_elements(By.XPATH, '//h2') if h.text]
    if len(headers) == 1:
        p_name = headers[0]
    elif len(headers) > 1:
        p_name = [h for h in headers if any(part in h.lower() for part in comp_keywords)]
        if p_name == '':
            p_list = [h for h in headers if len(h) >= 3 and (not 'neu' in h.lower() and not 'benachrichtigung' in h.lower())]
            if len(p_list) >= 1:
                p_name = p_list[0]
    p_stats = soup.find('ul',class_='x78zum5 x1q0g3np xieb3on')
    if p_stats:
        stats_list = p_stats.find_all('li')
        if stats_list:
            for e in stats_list:
                i = extract_text(e)
                if 'Beiträge' in i:
                    total_posts = extract_every_number(i)
                elif 'Follower' in i:
                    follower = extract_every_number(i)
        else:
            total_posts = full_desc
    header = soup.find('section')
    header_text = get_visible_text(Comment, header)
    if 'Gefolgt' in header_text and 'Beiträge' in header_text:
        desc = header_text.split('Gefolgt',1)[1].strip()
        desc_alt = desc.rsplit('Beiträge')[0].strip()
        if len(desc_alt) >= 100:
            desc = desc_alt
        else:
            if 'Gefolgt' in desc[:100]:
                desc = desc.split('Gefolgt', 1)[1].strip()
    else:
        desc = header_text
    if len(str(desc)) <= 4:
        desc = pagetext
    if 'Noch keine Beiträge' in pagetext:
        return [p_name, total_posts, follower, last_post, new_url, desc]

    link_elems = [str(l['href']) for l in soup.find_all('a',href=True)]
    all_links = ['https://www.instagram.com' + l for l in link_elems if not 'http' in l]
    p_links = [l for l in all_links if '/p/' in l]
    if len(p_links) == 0:
        p_links = [l for l in all_links if '/reel/' in l]
    if len(p_links) >= 1:
        driver.get(p_links[0])
        time.sleep(2)
        soup_post = BeautifulSoup(driver.page_source,'lxml')
        last_post = soup_post.find('time',class_='x1p4m5qa')
        if last_post:
            last_post = last_post['datetime'].split('T')[0]
            last_dt = datetime.strptime(last_post,'%Y-%m-%d')
            last_post = last_dt.strftime('%d.%m.%Y')
    return [p_name, total_posts, follower, last_post, new_url, desc]
########################################################################################################################

# Profile crawler
if __name__ == '__main__':
    # Settings for profile scraping
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    try:
        from credentials_file import username_insta, password_insta
    except:
        username_insta = str(input('Enter your username:')).strip()
        password_insta = str(input('Enter your password:')).strip()
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)

    # Start crawling
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(username_insta, password_insta)
    input('Press ENTER after the page is loaded')

    start_ID = 83
    # Loop through the companies
    for ID, row in df_source.iterrows():
        if 'ID' in col_list and col_list[0] != 'ID':
            ID = int(row['ID'])
        elif not 'nan' in str(ID):
            ID = int(ID)
        if ID < start_ID:  # If you want to skip some rows
            continue
        company = extract_text(row[comp_header])
        comp_keywords = get_company_keywords(company, row, col_list)
        url = str(row[platform])
        if len(url) < 10 or url == 'https://www.instagram.com' or url == 'https://www.instagram.com/':
            empty_row = [ID, company, dt_str] + ['' for _ in range(6)]
            data.append(empty_row)
            continue

        scraped_data = scrapeProfile(url, comp_keywords)
        full_row = [ID, company, dt_str] + scraped_data
        data.append(full_row)
        print(full_row)
        break
    # DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'all_posts', 'follower', 'last_post', 'url', 'description']
    df_profiles = pd.DataFrame(data,columns=header)
    df_profiles.set_index('ID')

    # Export to Excel
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
#    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()