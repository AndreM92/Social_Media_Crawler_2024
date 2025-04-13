
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.chrome.service import Service

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
startpage = 'https://www.facebook.com/'
platform = 'Facebook'
dt_str_now = None
upper_datelimit = '2025-04-01'

file_path = r"C:\Users\andre\OneDrive\Desktop\SMP_Banken_2025"
source_file = file_path + '\Auswahl_SMP Banken 2025_2025-03-26.xlsx'
branch_keywords = ['Bank', 'Finanz', 'Anlage', 'Anleg', 'Kurs', 'Aktie', 'Institut', 'Geld', 'Vermögen', 'Spar', 'dienstleist']
########################################################################################################################

# Facebook Login function
def login(useremail, password, driver, pyautogui):
    try:
        WebDriverWait(driver,5).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div[1]/div[1]/div/div/div/div[1]/div/img')))
    except:
        time.sleep(3)
    nameslot = driver.find_element('xpath','/html/body/div[1]/div[1]/div[1]/div/div/div/div[2]/div/div[1]/form/div[1]/div[1]/input')
    nameslot.clear()
    for char in useremail:
        time.sleep(0.1)
        nameslot.send_keys(char)
    pwslot = driver.find_element('xpath','/html/body/div[1]/div[1]/div[1]/div/div/div/div[2]/div/div[1]/form/div[1]/div[2]/div/input')
    pwslot.clear()
    for char in password:
        time.sleep(0.1)
        pwslot.send_keys(char)
    time.sleep(1)
    driver.find_element('xpath','/html/body/div[1]/div[1]/div[1]/div/div/div/div[2]/div/div[1]/form/div[2]/button').click()
    time.sleep(3)
    cookiebuttons = driver.find_elements('xpath', "//*[contains(text(), 'Blockieren') or contains(text(), 'blockieren')]")
    if len(cookiebuttons) >= 1:
        for c in cookiebuttons:
            try:
                c.click()
            except:
                time.sleep(1)
                pyautogui.moveTo(459, 203)
                pyautogui.click()
                time.sleep(1)
                pyautogui.moveTo(460, 205)
                pyautogui.click()

def get_p_name(driver, comp_keywords, p_name = ''):
    headers = [h.text for h in driver.find_elements(By.XPATH, '//h1') if h.text]
    if 'Suchergebnisse' in headers:
        return None
    if len(headers) >= 1:
        p_list = [h for h in headers if any(part in h.lower() for part in comp_keywords)]
        if len(p_list) >= 1:
            p_name = p_list[0].strip()
        else:
            p_list = [h for h in headers if len(h) >= 3 and (not 'neu' in h.lower() and not 'benachrichtigung' in h.lower())]
            if len(p_list) >= 1:
                p_name = p_list[0].strip()
    if p_name == '':
        headers2 = [h.text for h in driver.find_elements(By.XPATH, '//h2') if h.text]
        if len(headers2) >= 1:
            p_list = [h for h in headers if any(part in h.lower() for part in comp_keywords)]
            if len(p_list) >= 1:
                p_name = p_list[0].strip()
            else:
                p_list = [h for h in headers if
                          len(h) >= 3 and (not 'neu' in h.lower() and not 'benachrichtigung' in h.lower())]
                if len(p_list) >= 1:
                    p_name = p_list[0].strip()
    if 'Bestätigtes' in str(p_name):
        p_name = p_name.replace('Bestätigtes Konto', '').strip()
    return p_name

def date_hint(scr_text):
    day, month, year = None, None, None
    recent = ['gestern', 'stunde', 'minute', 'tage']
    for r in recent:
        if r in scr_text.lower():
            curr_dt = datetime.now().date()
            curr_dt_str = curr_dt.strftime('%d.%m.%Y')
            return curr_dt_str
    mDictGer = {'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5, 'Juni': 6, 'Juli': 7, \
                    'August': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12}
    for key, value in mDictGer.items():
        if key in scr_text:
            month = value
            month = str(month).zfill(2)
    if not month:
        for key, value in mDictGer.items():
            if key[:4] in scr_text:
                month = value
                month = str(month).zfill(2)
    years = ['2025','2024','2023','2022','2021','2020','2019','2018','2017']
    for y in years:
        if y in scr_text:
            year = y
    if year and month:
        curr_dt_str = f'01.{month}.{year}'
    elif month:
        curr_dt_str = f'01.{month}.2024'
    else:
        curr_dt_str = ''
    return curr_dt_str


def scrapeProfile(url):
    p_name, pagelikes, follower, last_post, raw_desc = ['' for _ in range(5)]
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if ('gelöscht' in pagetext and 'nicht verfügbar' in pagetext) or len(pagetext) <= 200:
        p_name = 'page not available'
        return [p_name, pagelikes, follower, '', url, pagetext]
    p_name = get_p_name(driver, comp_keywords)
    if len(str(p_name)) <= 2:
        return [p_name, pagelikes, follower, '', url, pagetext]

    upper_posts = soup.find_all('div', class_='x1c4vz4f x2lah0s xeuugli x1bhewko xq8finb xnqqybz')
    if len(upper_posts) >= 1:
        driver.execute_script("window.scrollBy(0, 1000);")
    else:
        driver.execute_script("window.scrollBy(0, 300);")
    time.sleep(1)
    scr_text = get_text_from_screenshot(driver, p_name)
    last_post = date_hint(scr_text)
    raw_desc_elem = soup.find('div',class_='x1yztbdb')
    if raw_desc_elem:
        raw_desc = get_visible_text(Comment, raw_desc_elem)
    if not raw_desc_elem or len(str(raw_desc)) <= 4:
        raw_desc_elem = driver.find_element(By.CLASS_NAME, 'x1yztbdb')
        raw_desc = extract_text(raw_desc_elem)
    description = raw_desc.replace('Steckbrief ', '').replace('Intro', '').strip()
    stats_elem = soup.find('div',class_='x9f619 x1n2onr6 x1ja2u2z x78zum5 xdt5ytf x2lah0s x193iq5w x1cy8zhl xyamay9')
    stats_text = extract_text(stats_elem)
    if stats_text:
        stats_list = str(stats_text).split('•')
        for e in stats_list:
            if "gefällt" in e.lower():
                pagelikes = extract_every_number(e)
            elif 'follower' in e.lower():
                follower = extract_every_number(e)
    if len(description) <= 5:
        description = extract_text(pagetext)
    new_url = driver.current_url
    return [p_name, pagelikes, follower, last_post, new_url, description]

########################################################################################################################
# Profile Crawler
if __name__ == '__main__':
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    import credentials_file as cred
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)
    col_list = list(df_source.columns)

    # Open the browser, go to the startpage and login
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(cred.email_fb, cred.password_fb, driver, pyautogui)

    # Loop through the companies
    for n, row in df_source.iterrows():
        if n < 0:
            continue
        id = row['ID']
        company = extract_text(row[comp_header])
        comp_keywords = get_company_keywords(company, row, col_list)
        url = extract_text(row[platform])
        if len(url) < 10 or '/search' in url or '/events' in url or '/public' in url:
            data.append([id, company, dt_str] + ['' for _ in range(4)] + [url,''])
            continue
        # Correct the url
        url = url.split('/followers')[0].split('/impressu')[0]
        # Correct the language of the url
        if 'locale=' in url:
            url = url.split('locale=')[0] + 'locale=de_DE'
        time.sleep(2)
        scraped_data = scrapeProfile(url)
        full_row = [id, company, dt_str] + scraped_data
        data.append(full_row)
        print(full_row)

#        if id % 5 == 0:
            # DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'likes', 'follower', 'last_post', 'url', 'description']
    df_profiles = pd.DataFrame(data, columns=header)
#            df_profiles.set_index('ID')

    # Export to Excel
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
#    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_Facebook_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)
    driver.quit()

########################################################################################################################
# Post crawler functions
def inspect_profile(row, lower_dt):
    link = extract_text(row['url'])
    last_dt = (row['last_post'])
    if not link or len(link) <= 4 or len(str(last_dt)) <= 4:
        return None
    if not isinstance(last_dt,datetime):
        try:
            last_dt = datetime.strptime(last_dt, '%d.%m.%Y')
        except:
            return None
    if (lower_dt - timedelta(days=31)) > last_dt:
        return None
    driver.get(link)
    time.sleep(3)
    driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    posts = soup.find_all('div', {'class': 'x1n2onr6 x1ja2u2z',
                                  'aria-label': lambda x: x is None or 'Kommentar' not in x})
    if len(posts) == 0:
        return None
    return last_dt

def scrape_reel(rawtext, p):
    post_date, likes, comments, shares, link = ['' for _ in range(5)]
    p_text = rawtext.replace('Facebook', '').strip()
    reactions = p_text.rsplit('·', 1)[-1].strip().replace('Senden!','').strip()
    if '.com' in reactions:
        reactions = reactions.split('.com')[0].rsplit(' ', 1)[0]
    react_la = [str(e).strip() for e in reactions.split(' ') if 5 >= len(str(e).strip()) >= 1]
    react_l = [extract_every_number(e) for e in react_la if str(e)[0].isdigit()]
    if len(react_l) >= 3:
        react_l = react_l[:3]
        likes, comments, shares = react_l
    elif len(react_l) == 2:
        likes, comments = react_l
    elif len(react_l) == 1:
        likes = react_l[0]
    reel_date = p_text.rsplit('·', 2)[-2].strip()
    if not reel_date or not reel_date[0].isdigit():
        reel_date = p_text[p_text.find('Reels') + 9:].split('·')[0].strip()
    if reel_date[0].isdigit():
        post_dt = dateFormat(reel_date)
        post_date = post_dt.strftime("%d.%m.%Y")
        if post_dt >= datetime.now():
            day = str(post_dt.day).zfill(2)
            month = str(post_dt.month).zfill(2)
            year = post_dt.year - 1
            post_date = f'{day}.{month}.{year}'
    p_text = p_text.rsplit('·', 1)[0].strip()
    r_links = [l['href'] for l in p.find_all('a', href=True) if 'reel' in l['href']]
    if len(r_links) >= 1:
        link = "https://www.facebook.com" + r_links[0].split('?', 1)[0]
    reel_data = [post_date, likes, comments, shares, link, p_text]
    return reel_data

# Scrape the posts
def get_p_link(p):
    links = [str(l['href']) for l in p.find_all('a', href=True)]
    f_links = [l for l in links if ('post' in l or '/p/' in l) and 'www.' in l]
    if len(f_links) == 0:
        f_links = [l for l in links if '/video' in l]
    if len(f_links) == 0:
        f_links = [l for l in links if '/photo' in l]
    if len(f_links) == 0:
        return None
    link = f_links[0].split('&__')[0].split('?__')[0]
    return link

def find_p_elements(p, rawtext):
    not_imagelinks = ['profile', 'hashtag', 'emoji']
    imagelinks_all = [p['src'] for p in p.find_all('img', src=True)]
    imagelinks = [p for p in imagelinks_all if not any(e in p for e in not_imagelinks)]
    if 'livestream' in rawtext or p.find('video', src=True) or p.find('div', {'aria-label': 'Play'}):
        image, video = 0, 1
    elif len(imagelinks) >= 1 or 'Bild' in str(p):
        image, video = 1, 0
    else:
        image, video = 0, 0
    return image, video

def split_p_text(rawtext):
    p_text = rawtext
    if '·' in p_text:
        p_text = p_text.split('·', 1)[1].strip()
    if '·' in p_text:
        p_text_s = p_text.split('·', 1)[1].strip()
        if 'Reaktionen' in p_text_s or 'reactions' in p_text_s:
            p_text = p_text_s
    p_text1 = p_text
    if 'Teilen' in p_text:
        if p_text.count('Teilen') > 1:
            p_text = 'Teilen ' + ' '.join(p_text.split('Teilen')[:2]).strip()
        else:
            p_text = p_text.split('Teilen')[0].strip()
    else:
        if 'Kommentieren' in p_text:
            p_text = p_text.split('Kommentieren')[0].strip()
    forbidden_chars = ['+', '-', '*', '=']
    if any(c in p_text[0] for c in forbidden_chars):
        p_text = '$$' + p_text
    comments = False
    if len(p_text1) - len(p_text) >= 145 or 'Kommentar' in p_text1:
        comments = True
    if 'Alle Reaktionen:' in p_text:
        reactions = p_text.split('Alle Reaktionen:')[1].strip()
    elif 'All reactions' in p_text:
        reactions = p_text.split('All reactions:')[1].strip()
    elif 'Kommentar' in p_text:
        reactions = [p_text.split('Kommentar')[0].split()[-1]]
    else:
        reactions = None
    return p_text1, p_text, reactions, comments

def get_reactions(p_text1, reactions, comments):
    if not reactions or len(reactions) <= 4 :
        return '', '', ''
    react_ls = [str(e).strip() for e in reactions.split(' ') if len(str(e).strip()) >= 1]
    react_numbers = [extract_every_number(e) for e in react_ls if str(e)[0].isdigit()]
    if len(react_numbers) == 0:
        return 0, 0, 0
    if len(react_numbers) >= 2:
        react_numbers.pop(1)
    if len(react_numbers) == 1:
        if comments:
            return [0, react_numbers[0], 0]
        elif 'Mal' in p_text1 and ' geteilt' in p_text1:
            return [0, 0, react_numbers[0]]
        return [react_numbers[0], 0, 0]
    elif len(react_numbers) == 2:
        if comments:
            if 'Mal' in p_text1 and ' geteilt' in p_text1:
                return [0, react_numbers[0], react_numbers[1]]
            return [react_numbers[0], react_numbers[1], 0]
        return [react_numbers[0], 0, react_numbers[1]]
    return react_numbers[:3]

def post_scraper(p):
    rawtext = str(get_visible_text(Comment, p))
    if len(rawtext) <= 30 or not p_name[:4].lower() in rawtext.lower():
        return None
    post_date = ''
    if 'Reels' in rawtext:
        p_type = 'reel'
        video, image = 1, 0
        post_date, likes, comments, shares, link, p_text = scrape_reel(rawtext, p)
    else:
        p_type = 'post'
        link = get_p_link(p)
        image, video = find_p_elements(p, rawtext)
        p_text1, p_text, reactions, comments = split_p_text(rawtext)
        likes, comments, shares = get_reactions(p_text1, reactions, comments)
    return [post_date, likes, comments, shares, image, video, p_type, link, p_text]

def check_distinct(distinct_content, scraped_post):
    p_text = str(scraped_post[-1])
    if len(p_text) >= 50:
        content_short = p_text[:50]
    elif len(p_text) >= 20:
        content_short = p_text[:20]
    else:
        content_short = p_text
    if content_short not in distinct_content:
        distinct_content.append(content_short)
        return distinct_content
    return None
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    import credentials_file as cred
    os.chdir(file_path)
    files = os.listdir()
    for e in files:
        if 'Profile_Facebook_2025' in str(e):
            file = extract_text(e)
            break
    df_source, dt, dt_str, upper_dt, lower_dt = post_crawler_settings(file, platform, dt_str_now, upper_datelimit)

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(cred.username_fb, cred.password_fb, driver, pyautogui)

    start_time = time.time()
    # Iterate over the companies
    for count, row in df_source.iterrows():
        id = row['ID']
        p_name = extract_text(row['profile_name'])
        if id <= 0:                                     #If you want to skip some rows
            continue
        last_dt = inspect_profile(row, lower_dt)
        if not last_dt:
            continue

        data_per_company = []
        distinct_content = []
        count_p = 0
        no_p = 0
        days_delta = (last_dt - lower_dt).days
        scrolls = round(days_delta / 2)

        for _ in range(scrolls):
            len_post_list = len(data_per_company)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            posts = soup.find_all('div', class_='x1n2onr6 x1ja2u2z')
            if count_p == 0:
                upper_posts = soup.find_all('div', class_='x1c4vz4f x2lah0s xeuugli x1bhewko xq8finb xnqqybz')
                if len(upper_posts) >= 1:
                    posts = upper_posts + posts
            for p in posts:
                scraped_post = post_scraper(p)
                if not scraped_post:
                    continue
                distinct_content_new = check_distinct(distinct_content, scraped_post)
                if distinct_content_new:
                    count_p += 1
                    full_row = [id, p_name, count_p, dt_str] + scraped_post
                    print(full_row)
                    data_per_company.append(full_row)
                    distinct_content = distinct_content_new
            if len_post_list == len(data_per_company) and no_p >= 3:
                print('No more new posts')
                break
            if len_post_list == len(data_per_company):
                no_p += 1
            else:
                no_p = 0
            driver.execute_script("window.scrollBy(0, 1800);")
            wait_time = round(((len_post_list)*0.025)**0.5)
            time.sleep(wait_time)

        ##### Safe #####
        all_data += data_per_company

        # Create a DataFrame with all posts
        header1 = ['ID_A', 'profile_name', 'ID_P', 'Erhebung', 'Datum']
        header2 = ['Likes', 'Kommentare', 'Shares', 'Bild', 'Video', 'Beitragsart', 'Link', 'Content']
        dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

        # Export dfPosts to Excel (with the current time)
        dt_str_now2 = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_Facebook_' + dt_str_now2
        dfPosts.to_excel(file_name + '.xlsx')

        # Close the crawler after two hours
        end_time = time.time()
        time_diff = end_time - start_time
        if time_diff >= (180 * 60):
            start_time = time.time()
            driver.quit()

    driver.quit()