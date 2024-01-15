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

import os

# General Settings
newpath = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
os.chdir(newpath)
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
startpage = 'https://twitter.com/i/flow/login'
network = 'X'
dt_str_now = None
########################################################################################################################

def settings(source_file):
    df_source = pd.read_excel(source_file)
    df_source.set_index('ID', inplace=True)
    col_list = list(df_source.columns)
    if 'Anbieter' in col_list:
        comp_header = 'Anbieter'
    elif 'Firma' in col_list:
        comp_header = 'Firma'
    dt = datetime.now()
    dt_str = dt.strftime("%d.%m.%Y")
    return df_source, col_list, comp_header, dt, dt_str

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
    if '@' in full_desc:
        p_name, full_desc = full_desc.split('@',1)[1].split(' ',1)
    if len(p_name) <= 2 or len(p_name) >= 30:
        p_name = extract_text(soup.find('div', {'data-testid': 'UserName'}))
        if '@' in p_name:
            p_name = p_name.split('@')[1]
    if len(full_desc) >= 10:
        dlist = full_desc.split()
        for pos, e in enumerate(dlist):
            e = e.lower()
            if 'followers' in e and not 'followed' in e and follower == '':
                follower = dlist[pos - 1]
                print(follower)
                follower = extract_big_number(follower)
            elif 'following' in e and not 'followed' in e and following == '':
                following = dlist[pos - 1]
                following = extract_big_number(following)
            elif 'joined' in e:
                joined = ' '.join(dlist[(pos + 1):(pos + 3)])
    last_post, last_post_dt, posts = get_last_date()
    datarow = [p_name, follower, following, joined, last_post, new_url, full_desc]
    return datarow
########################################################################################################################

if __name__ == '__main__':
    # Settings for profile scraping
    newpath = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
    os.chdir(newpath)
    source_file = "Liste_Nahrungsergänzungsmittel_2024_20240108.xlsx"
    df_source, col_list, comp_header, dt, dt_str = settings(source_file)

    # Start crawling
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(driver, startpage, cred.username_tw, cred.password_tw)

    # Iterating over the companies
    for id, row in df_source.iterrows():
        if id <= -1:
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
    header = ['ID', 'Anbieter', 'Erh.Datum', 'Profilname', 'follower', 'following', 'joined', 'last post', 'url',
              'description']
    dfProfiles = pd.DataFrame(data, columns=header)
    dfProfiles.set_index('ID')

    # Export to Excel
    #    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_Twitter_' + dt_str_now + '.xlsx'
    with pd.ExcelWriter(recent_filename) as writer:
        dfProfiles.to_excel(writer, sheet_name='Profildaten')

    driver.quit()

########################################################################################################################
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
    time.sleep(1)
    driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
    time.sleep(2)
    last_post, current_dt, posts = get_last_date()
    if not current_dt:
        return None, None, None
    if current_dt < lower_dt:
        posts = ''
    url = driver.current_url
    return p_name, url, posts, last_post


# The scrapePost function scrapes the details of every post
def scrapePost(p, p_name):
    date_elem, tweet_type, likes, comments, retweets, views, image, video, link, content = ['' for i in range(10)]
    try:
        date_elem = p.find('time')['datetime']
        date = date_elem.split('T')[0].strip()
        date_dt = datetime.strptime(date, "%Y-%m-%d")
    except:
        date = date_elem
        date_dt = datetime.strptime("2023-12-12", "%Y-%m-%d")
    if not type(date_dt).__name__ == 'datetime':
        date_dt = datetime.strptime("2023-12-12", "%Y-%m-%d")
    else:
        date = date_dt.strftime('%d.%m.%Y')
    full_text = extract_text(p)
    if 'retweet' in full_text.lower() or 'repost' in full_text:
        tweet_type = 'retweet'
    else:
        tweet_type = 'tweet'
    content_elem = p.find_all('span')
    content_all = [extract_text(t) for t in content_elem]
    content = ' '.join([e for e in content_all if (e.strip() != p_name and e.strip() != '@' + p_name) and len(e) >= 3])
    if len(str(content)) <= 4:
        content = full_text
    interact_elems = p.find_all('div', class_='css-1dbjc4n r-13awgt0 r-18u37iz r-1h0z5md')
    interactions = [extract_number(e) for e in interact_elems]
    if len(interactions) == 4:
        comments, retweets, likes, views = interactions
    elif len(interactions) == 0:
        interact_bar = p.find('div', {'role': 'group'})
        if interact_bar:
            interactions = extract_text(interact_bar.get('aria-label'))
            if interactions:
                interact_ls = interactions.split()
                for pos, e in enumerate(interact_ls):
                    if 'like' in e:
                        likes = extract_big_number(interact_ls[pos-1])
                    elif 'repost' in e:
                        retweets = extract_big_number(interact_ls[pos - 1])
                    elif 'reply' in e or 'replie' in e:
                        comments = extract_big_number(interact_ls[pos - 1])
                    elif 'views' in e:
                        views = extract_big_number(interact_ls[pos - 1])
    imagelinks_all = [p['src'] for p in p.find_all('img', src=True)]
    imagelinks = [p for p in imagelinks_all if not 'profile_image' in str(p) and not 'hashtag' in str(p) and not 'emoji' in str(p)]
    if len(imagelinks) >= 1:
        image = 1
        video = 0
    if p.find('video', src=True) or p.find('div', {'aria-label': 'Play'}) or 'livestream' in full_text:
        video = 1
        image = 0
    if p.find('div', {'data-testid': 'cardPoll'}):
        tweet_type = 'poll'
        image = 0
        video = 0
    links_raw = [l['href'] for l in p.find_all('a', href=True)]
    links = ['https://twitter.com' + l if not 'http' in l else l for l in links_raw]
    links_f = [l for l in links if 'status' in l]
    if len(links_f) >= 1:
        link = links_f[0]
    if len(links) >= 2:
        links = str(list(set(links)))
    if len(links) == 1:
        links = links[0]
    else:
        links = ''
    ls = re.sub(r'[.-_]', '', link.lower()).strip()
    ns = re.sub(r'[.-_]', '', p_name.lower()).strip()
    if not (ns[:4] in ls or ns[-4:] in ls) and not tweet_type == 'retweet':
        tweet_type = 'ad'

    data_single_p = [date, tweet_type, likes, comments, retweets, views, image, video, link, links, content]
    for pos, e in enumerate(data_single_p):
        if not e:
            data_single_p[pos] = ''

    return data_single_p, link, date_dt


# Main function for the posts
def main(id, p_name, dt_str, upper_dt, lower_dt, url):
    date, tweet_type, likes, comments, retweets, views, image, video, link, links, content = ['' for i in range(11)]
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = extract_text(get_visible_text(Comment, soup))
    if '@' in pagetext:
        pagetext = pagetext.split('@',1)[1]

    posts = soup.find_all('article')
    if posts:
        last_date_elem = [p.find('time')['datetime'] for p in posts if p.find('time') and 'datetime' in p.find('time').attrs][-1]
        last_date = datetime.strptime(last_date_elem.split('T')[0].strip(),'%Y-%m-%d')
    else:
        no_posts_row = [id, p_name, '0', dt_str,*['' for i in range(9)],url,pagetext]
        return no_posts_row

    counter = 1
    ad_count = 1
    scrolls = 0
    p_linklist = []
    distinct_posts = []
    while True:
 #       scrheight = driver.execute_script("return document.documentElement.scrollHeight")
        if scrolls == 0:
            driver.execute_script("window.scrollBy(0,1500)", "")
        else:
            driver.execute_script("window.scrollBy(0,2000)", "")
        scrolls +=1
        time.sleep(3)
        if scrolls >= 50:
            time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        posts = soup.find_all('article')
        if not posts:
            break
        for p in posts:
            data_single_p, p_link, current_dt = scrapePost(p, p_name)
            if p_link in p_linklist or current_dt >= upper_dt:
                continue
            if data_single_p[1] == 'ad':
                try:
                    alt_name = data_single_p[-1].split()[0]
                except:
                    alt_name = ''
                full_row = [id, alt_name, ad_count, dt_str] + data_single_p
                distinct_posts.append(full_row)
                p_linklist.append(p_link)
                ad_count += 1
            else:
                full_row = [id, p_name, counter, dt_str] + data_single_p
                distinct_posts.append(full_row)
                p_linklist.append(p_link)
                counter += 1
        if current_dt <= lower_dt or scrolls == 280:
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
    data_per_company = main(id, p_name, dt_str, upper_dt, lower_dt, url)
    all_data += data_per_company
    print(data_per_company)


# Create a DataFrame with all posts
header1 = ['ID_A', 'Profilname', 'ID_P', 'Datum_Erhebung', 'Datum_Beitrag']
header2 = ['Beitragsart', 'Likes', 'Kommentare', 'Retweets', 'Views', 'Bild', 'Video', 'Link', 'Links', 'Content']
dfPosts = pd.DataFrame(all_data,columns=header1+header2)

# Export dfPosts to Excel (with the current time)
#dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
file_name = 'Beiträge_Twitter2' + dt_str + '.xlsx'
dfPosts.to_excel(file_name)