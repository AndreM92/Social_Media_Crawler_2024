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
# Settings and paths for this program
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Scraper\Social_Media_Crawler_2023"
file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
source_file = "Liste_Nahrungsergänzungsmittel_2024_Auswahl.xlsx"
branch_keywords = ['nutrition', 'vitamin', 'mineral', 'protein', 'supplement', 'diet', 'health', 'ernährung',
                   'ergänzung', 'gesundheit', 'nährstoff', 'fitness', 'sport', 'leistung']
startpage = 'https://twitter.com/i/flow/login'
network = 'X'
dt_str_now = None
########################################################################################################################

# Login function
def login(driver, startpage, email, password):
    if driver.current_url != startpage:
        driver.get(startpage)
        time.sleep(3)
    try:
        nameslot = driver.find_element(By.CSS_SELECTOR,'input[autocapitalize="sentences"][autocomplete="username"]')
    except:
        try:
            xp1 = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[5]/label/div/div[2]/div/input'
            nameslot = driver.find_element('xpath', xp1)
        except:
            pass
    nameslot.click()
    nameslot.clear()
    for char in email:
        time.sleep(0.1)
        nameslot.send_keys(char)
#    nameslot.send_keys(email)
    time.sleep(1)
    conf = driver.find_elements('xpath', "//*[contains(text(), 'Weiter') or contains(text(), 'weiter')]")
    for c in conf:
        try:
            c.click()
        except:
            pass
#    pushx = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[6]/div'
#    driver.find_element('xpath',pushx).click()
    # Error: Unusual Login activities
    try:
        pwslot = driver.find_element(By.CSS_SELECTOR,'input[autocapitalize="sentences"][name="password"]')
    except:
        try:
            pwx = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input'
            WebDriverWait(driver, 5).until(EC.presence_of_element_located(('xpath', pwx)))
            pwslot = driver.find_element('xpath', pwx)
            pwslot.clear()
        except:
            return None
    for char in password:
        pwslot.send_keys(char)
        time.sleep(.2)
    login_buttons = driver.find_elements('xpath', "//*[contains(text(), 'Anmelden') or contains(text(), 'anmelden')]")
    for b in login_buttons:
        try:
            b.click()
        except:
            pass
#       pwslot.send_keys(cred.password_tw)
#        loginx = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/div/div'
#        driver.find_element('xpath', loginx).click()
    time.sleep(2)
    try:
        driver.find_element('xpath', "//*[text()='Refuse non-essential cookies']").click()
    except Exception as e:
        print(repr(e))

def get_last_date():
    soup = BeautifulSoup(driver.page_source, 'lxml')
    last_post, parsed_datetime = '', ''
    posts = soup.find_all('article')
    if len(posts) >= 2:
        # Last or second last (not pinned) post
        last_post = posts[1]
        date_str = last_post.find('time')['datetime']
        parsed_datetime = datetime.fromisoformat(date_str.replace('Z', ''))
        last_post = parsed_datetime.strftime('%d.%m.%Y')
    if len(str(last_post)) <= 4:
        date_elements = driver.find_elements('xpath', '//time[@datetime]')
        if len(date_elements) >= 2:
            date_str = date_elements[1].get_attribute('datetime')
            parsed_datetime = datetime.fromisoformat(date_str.replace('Z', ''))
            last_post = parsed_datetime.strftime('%d.%m.%Y')
    return last_post, parsed_datetime, posts

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(driver, url):
    p_name, follower, following, joined = ['' for _ in range(4)]
    driver.get(url)
    time.sleep(4)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if len(pagetext) <= 1000 or 'not available' in pagetext:
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
    new_url = driver.current_url
    not_existent = 'This account doesn’t exist'
    if len(pagetext) <= 1000 or not_existent in pagetext or not 'twitter.com' in new_url:
        return [not_existent, follower, following, '', joined, new_url, pagetext]
    full_desc_elem = soup.find('div', class_='css-1dbjc4n r-1ifxtd0 r-ymttw5 r-ttdzmv')
    if not full_desc_elem:
        full_desc_elem = soup.find('div',class_='css-175oi2r r-ymttw5 r-ttdzmv r-1ifxtd0')
        full_desc = ' '.join([extract_text(e) for e in full_desc_elem]).replace('Following', 'Following ')
    else:
        full_desc = extract_text(full_desc_elem)
    p_name = str(extract_text(soup.find('div', {'data-testid': 'UserName'})))
    if '@' in full_desc:
        if len(p_name) <= 4 or len(p_name) >= 30:
            p_name, full_desc = full_desc.split('@', 1)[1].split(' ', 1)
        else:
            full_desc = full_desc.split('@', 1)[1].strip()
    if '@' in p_name:
        p_name = p_name.split('@')[1]
    if len(str(full_desc)) >= 30 and p_name in full_desc[:30]:
        full_desc = full_desc.split(p_name,1)[1].strip()
    if len(full_desc) >= 10:
        dlist = full_desc.split()
        for pos, e in enumerate(dlist):
            e = e.lower()
            if 'followers' in e and not 'followed' in e and follower == '':
                follower = dlist[pos - 1]
                follower = extract_every_number(follower)
            elif 'following' in e and not 'followed' in e and following == '':
                following = dlist[pos - 1]
                following = extract_every_number(following)
            elif 'joined' in e:
                joined = ' '.join(dlist[(pos + 1):(pos + 3)])
    last_post, last_post_dt, posts = get_last_date()
    datarow = [p_name, follower, following, joined, last_post, new_url, full_desc]
    return datarow
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
    login(driver, startpage, cred.username_tw, cred.password_tw)

    # Iterating over the companies
    count = 0  # If id's aren't ordered
    for id, row in df_source.iterrows():
        count += 1
        if count <= 0:  # If you want to skip some rows
            continue
        company = extract_text(row[comp_header])
        comp_keywords = get_company_keywords(company, row, col_list)
        url = str(row[network])
        if len(url) < 10:
            empty_row = [id, company, dt_str] + ['' for _ in range(7)]
            data.append(empty_row)
            continue

        datarow = scrapeProfile(driver, url)
        full_row = [id, company, dt_str] + datarow
        data.append(full_row)
        print(datarow)

    # DataFrame
    header = ['ID','company','date','profile_name','follower','following','joined','last_post', 'url','description']
    df_profiles = pd.DataFrame(data,columns=header)
    df_profiles.set_index('ID')

    # Export to Excel
    #    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_Twitter_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()
########################################################################################################################

# Post crawler functions
def post_crawler_settings():
    upper_dt = datetime.strptime('2024-01-01', '%Y-%m-%d')
    lower_dt = upper_dt - timedelta(days=365)
    if dt_str_now:
        source_file = 'Profile_Twitter_' + dt_str_now + '.xlsx'
        return upper_dt, lower_dt, source_file
    # Else: load the last file I created
    source_file = 'Profile_Twitter_2024-01-13.xlsx'
    if source_file not in os.listdir():
        print('Twitter File not found')
        exit()
    return upper_dt, lower_dt, source_file

def inspect_page(id, row, lower_dt):
    url = str(row['url'])
    p_name = row['Profilname']
    if len(url) < 10 or len(str(row['last post'])) <= 4 or '2022' in str(row['last post']):
        print([id, p_name, '', '', url])
        return ['' for _ in range(4)]
    driver.get(url)
    time.sleep(3)
    driver.execute_script("window.scrollBy(0,1500)", "")
    time.sleep(2)
    last_post, current_dt, posts = get_last_date()
    if not current_dt:
        return ['' for _ in range(4)]
    if current_dt < lower_dt:
        posts = ''
    url = driver.current_url
    return p_name, url, posts, last_post

# Scrape the post interactions
def get_reactions(p):
    react_elements = p.find_all('div', {'aria-label': True})
    aria_content = [str(e['aria-label']).lower().strip() for e in react_elements]
    for a in aria_content:
        if ',' in a:
            aria_content += a.split(',')
    react_list = [a for a in aria_content if (20 > len(a) > 4 and not ('like' and 'view' in a))]
    likes, comments, shares, views = [0 for _ in range(4)]
    for a in react_list:
        if 'like' in a and likes == 0:
            likes = extract_every_number(a)
        elif 'repl' in a and comments == 0:
            comments = extract_every_number(a)
        elif 'repost' in a and shares == 0:
            shares = extract_every_number(a)
        elif 'view' in a and views == 0:
            views = extract_every_number(a)
    return likes, comments, shares, views

def get_post_elements(p, full_text, tweet_type):
    image, video = 0, 0
    imagelinks_all = [p['src'] for p in p.find_all('img', src=True)]
    imagelinks = [p for p in imagelinks_all if not 'profile_image' in str(p) and not 'hashtag' in str(p) and not 'emoji' in str(p)]
    if len(imagelinks) >= 1:
        image, video = 1,0
    if p.find('video', src=True) or p.find('div', {'aria-label': 'Play'}) or 'livestream' in full_text:
        video, image = 1,0
    if p.find('div', {'data-testid': 'cardPoll'}):
        tweet_type = 'poll'
    return image, video, tweet_type

def get_link(p):
    links_raw = [l['href'] for l in p.find_all('a', href=True)]
    links = ['https://twitter.com' + l if not 'http' in l else l for l in links_raw]
    links_f = [l for l in links if 'status' in l]
    if len(links_f) >= 1:
        return links_f[0]
    if len(links) >= 1:
        return links[0]
    return ''

# post_scraper function scrapes the details of every post
def post_scraper(p, p_name, lower_dt):
    full_text = get_visible_text(Comment, p)
    try:
        date_elem = p.find('time')['datetime']
        date = date_elem.split('T')[0].strip()
        date_dt = datetime.strptime(date, "%Y-%m-%d")
        date = date_dt.strftime("%d.%m.%Y")
        if date_dt >= upper_dt or date_dt < lower_dt:
            return None, date_dt
    except:
        return None, None
    tweet_type = 'tweet'
    if 'retweet' in full_text.lower() or 'repost' in full_text:
        tweet_type = 'retweet'
    ns = re.sub(r'[.-_]', '', p_name.lower()).strip()
    if not ns.lower() in full_text[:50].lower():
        tweet_type = 'ad'
        p_name = full_text[:50].split('·')[0]
    likes, comments, shares, views = get_reactions(p)
    image, video, tweet_type = get_post_elements(p, full_text, tweet_type)
    link = get_link(p)
    content_elem = p.find_all('span')
    content_all = [extract_text(t) for t in content_elem]
    content = ' '.join(
        [e for e in content_all if (e.strip() != p_name and e.strip() != '@' + p_name) and len(e) >= 3])
    if len(str(content)) <= 4:
        content = full_text
    post_data = [date, tweet_type, likes, comments, shares, views, image, video, link, content]
    return post_data, date_dt

def scroller(scrolls, height2):
    height1 = height2
    height2 = driver.execute_script("return document.documentElement.scrollHeight")
    driver.execute_script("window.scrollBy(0,2000)", "")
    scrolls += 1
    time.sleep(3)
    if scrolls >= 50:
        time.sleep(1)
    height3 = driver.execute_script("return document.documentElement.scrollHeight")
    if height1 == height3 or scrolls == 300:
        return True, scrolls, height2
    return False, scrolls, height2

# Crawler function for the whole profile (scrolls down and scrapes the post data)
def page_crawler(id, p_name, dt_str, upper_dt, lower_dt):
    crawl = True
    distinct_posts = []
    distinct_linklist = []
    id_p = 0
    id_ad = 0
    scrolls = 0
    height2 = False

    while crawl:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        posts = soup.find_all('article')
        if not posts:
            crawl = False
        for p in posts:
            post_data, date_dt = post_scraper(p, p_name, lower_dt)
            if not date_dt or date_dt < lower_dt:
                crawl = False
                break
            if not post_data or date_dt >= upper_dt:
                continue
            link = post_data[-2]
            if link in distinct_linklist:
                continue
            if post_data[1] == 'ad':
                full_row = [id, p_name, id_ad, dt_str] + post_data
                id_ad += 1
            else:
                full_row = [id, p_name, id_p, dt_str] + post_data
                id_p += 1
            print(full_row)
            distinct_linklist.append(link)
            distinct_posts.append(full_row)
        stopped, scrolls, height2 = scroller(scrolls, height2)
        scrolls += 1
        if scrolls >= 15 or stopped:
            break
    return distinct_posts

########################################################################################################################
# Post Crawler
if __name__ == '__main__':
    # Settings for the post crawler
    upper_dt, lower_dt, source_file = post_crawler_settings()
    df_source, col_list, comp_header, dt, dt_str = settings(source_file)

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(driver, startpage, cred.username_tw, cred.password_tw)

    # Iterate over the companies
    for id, row in df_source.iterrows():
        p_name, url, posts, last_post = inspect_page(id, row, lower_dt)
        if not posts:
            continue
        data_per_company = page_crawler(id, p_name, dt_str, upper_dt, lower_dt)
        all_data += data_per_company

    # Create a DataFrame with all posts
    header1 = ['ID_A', 'Profilname', 'ID_P', 'Erhebung', 'Datum']
    header2 = ['Beitragsart', 'Likes', 'Kommentare', 'Retweets', 'Aufrufe', 'Bild', 'Video', 'Link', 'Content']
    dfPosts = pd.DataFrame(all_data,columns=header1+header2)

    # Export dfPosts to Excel (with the current time)
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    file_name = 'Beiträge_Twitter_' + dt_str_now + '.xlsx'
    dfPosts.to_excel(file_name)

    driver.quit()