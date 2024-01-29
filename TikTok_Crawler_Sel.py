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
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
source_file = "Liste_Nahrungsergänzungsmittel_2024_Auswahl.xlsx"
branch_keywords = ['nutrition', 'vitamin', 'mineral', 'protein', 'supplement', 'diet', 'health', 'ernährung',
                   'ergänzung', 'gesundheit', 'nährstoff', 'fitness', 'sport', 'leistung']
startpage = 'https://www.tiktok.com/'
platform = 'TikTok'
dt_str_now = None
########################################################################################################################

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(url):
    p_name, pagelikes, follower, following, last_post, desc = ['' for i in range(6)]
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if not pagetext or len(pagetext) <= 100 or 'Verifiziere, um fortzufahren' in pagetext:
        # Solve the captcha manually
        time.sleep(7)
        pagetext = get_visible_text(Comment, soup)
    header_elems = soup.find_all('h1',{'data-e2e':'user-title'})
    if len(header_elems) == 0:
        header_elems = soup.find_all('h1')
    if len(header_elems) >= 1:
        header = [extract_text(e) for e in header_elems]
        p_name = header[0]
    #stats = soup.find('h3',class_='tiktok-12ijsdd-H3CountInfos e1457k4r0')
    stat_elems = soup.find_all('h3')
    if len(stat_elems) >= 1:
        stat_elems = [e for e in stat_elems if 'follow' in extract_text(e).lower()]
        if len(stat_elems) >= 1:
            for e in stat_elems[0]:
                i = extract_text(e)
                if 'Like' in i:
                    pagelikes = extract_every_number(i.split('Like')[0].strip())
                elif 'Follower' in i:
                    follower = extract_every_number(i.split('Follower')[0].strip())
                elif 'Folge' in i:
                    following = extract_every_number(i.split('Folge')[0].strip())
    desc = get_visible_text(Comment, soup.find('h2',{'data-e2e':'user-bio'}))
    if len(desc) <= 4:
        desc = pagetext
    userlink = soup.find('a',{'data-e2e':'user-link'},href=True)
    if userlink:
        userlink = userlink['href']
    if 'keine Videos veröffentlicht' in pagetext:
        return [p_name, pagelikes, follower, following, last_post, url, userlink, desc]
    links = [l['href'] for l in soup.find_all('a',href=True)]
    videolinks = list(set([l for l in links if 'video' in str(l)]))
    if len(videolinks) == 0:
        # Solve the captcha manually
        time.sleep(6)
        links = [l['href'] for l in soup.find_all('a', href=True)]
        videolinks = list(set([l for l in links if 'video' in str(l)]))
    if len(videolinks) == 0:
        return [p_name, pagelikes, follower, following, last_post, url, userlink, desc]

    videolinks.sort(reverse=True)
    last_video_link = videolinks[0]
    driver.get(last_video_link)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    name_date = extract_text(soup.find('span',{'data-e2e':'browser-nickname'}))
    if '·' in name_date:
        date_str = name_date.split('·')[-1].strip()
        last_dt, last_post = get_approx_date(datetime.now().date(), date_str)
    return [p_name, pagelikes, follower, following, last_post, url, userlink, desc]
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
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)

    # Iterating over the companies
    count = 0  # If id's aren't ordered
    for id, row in df_source.iterrows():
        count += 1
        if count <= 0:  # If you want to skip some rows
            continue
        company = extract_text(row[comp_header])
        comp_keywords = get_company_keywords(company, row, col_list)
        url = str(row[platform])
        if len(url) < 10:
            empty_row = [id, company, dt_str] + ['' for _ in range(8)]
            data.append(empty_row)
            continue

        scraped_data = scrapeProfile(url)
        full_row = [id, company, dt_str] + scraped_data
        data.append(full_row)
        print(count,full_row[:-1])


    # DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'pagelikes', 'follower', 'following', 'last_post', 'url',
              'desc_link', 'description']
    df_profiles = pd.DataFrame(data, columns=header)
    df_profiles.set_index('ID')

    # Export to Excel
    #    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)
########################################################################################################################

# Post Crawler functions

def check_conditions(id, row, start_at=0):
    if id < start_at:      # If you want to skip some rows
        return True
    p_name = str(row['profile_name'])
    if len(p_name) == 0 or p_name.lower() == 'nan' or p_name == 'None':
        return False
    posts = str(row['last_post'])
    if len(url) < 10 or len(posts) <= 4 or 'Keine Beiträge' in posts:
        print([id, p_name, '', dt_str] + [url])
        return False
    try:
        last_datestr = extract_text(row['last_post'])
        last_dt = datetime.strptime(last_datestr, "%d.%m.%Y")
        if (lower_dt - timedelta(days=31)) > last_dt:
            return True
    except:
        return False


def get_videolinks(driver, url):
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if 'Puzzleteil' in pagetext:
        print('Solve the captcha manually')
        time.sleep(7)

    video_first_info = []
    # Scroll down
    safety_counter = 0
    while safety_counter < 3:       #30
        start_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
        time.sleep(1)
        end_height = driver.execute_script("return document.body.scrollHeight")
        print(start_height, end_height)
        if start_height == end_height:
            break
        safety_counter += 1
    soup = BeautifulSoup(driver.page_source, 'lxml')
    video_containers = soup.find_all('div',{'data-e2e':'user-post-item'})
    if not video_containers:
        return None
    # Iterate over the video containers
    for v in video_containers:
        views, link = '', ''
        links = [l['href'] for l in v.find_all('a',href=True) if 'video' in str(l['href'])]
        if len(links) >= 1:
            link = links[0]
        view_text = get_visible_text(Comment,v)
        if ' ' in view_text:
            view_text = view_text.split(' ')[0].strip()
        views = extract_every_number(view_text)
        video = [views, link]
        video_first_info.append(video)
    video_first_info = sorted(video_first_info, key=lambda link: link[1], reverse=True)
    return video_first_info
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    # Settings for the post crawler
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    import credentials_file as cred
    os.chdir(file_path)
    file ='Profile_' + platform + '_2024'
    df_source, dt, dt_str, upper_dt, lower_dt = post_crawler_settings(file, platform, dt_str_now)

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)

    # Iterate over the companies
    for count, row in df_source.iterrows():
        url = str(row['url'])
        skip = check_conditions(count,row,start_at=0)
        if skip:
            continue
        break

        video_first_info = get_videolinks(driver, url)

        for count, info in enumerate(video_first_info):
#            print(count,info)
            link = videolinks[0]
            if count == 0:
                go_to_page(driver, link)
            else:
                driver.get(link)
                time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            name_date = extract_text(soup.find('span', {'data-e2e': 'browser-nickname'}))
            if '·' in name_date:
                date_str = name_date.split('·')[-1].strip()
                last_dt, last_post = get_approx_date(datetime.now().date(), date_str)

#    if len(videolinks) == 0:
#        return [p_name, pagelikes, follower, following, last_post, url, userlink, desc]
