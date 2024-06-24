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
startpage = 'https://www.tiktok.com/'
platform = 'TikTok'
dt_str_now = None

file_path = r"C:\Users\andre\OneDrive\Desktop\SMP_Brauereien_2024"
source_file = r"C:\Users\andre\OneDrive\Desktop\SMP_Brauereien_2024\Brauereien_Auswahl_2024-06-16.xlsx"
branch_keywords = ['Brauerei', 'Brauhaus', 'Bräu', 'braeu', 'Bier', 'brewing']
#branch_keywords = ['nutrition', 'vitamin', 'mineral', 'protein', 'supplement', 'diet', 'health', 'ernährung',
#                   'ergänzung', 'gesundheit', 'nährstoff', 'fitness', 'sport', 'leistung']
#file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
#source_file = "Liste_Nahrungsergänzungsmittel_2024_Auswahl.xlsx"
########################################################################################################################

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(url):
    p_name, pagelikes, follower, following, last_post, desc = ['' for i in range(6)]
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if not pagetext or len(pagetext) <= 100 or 'Verifiziere, um fortzufahren' in pagetext:
        input('Press ENTER after solving the captcha')
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
        input('Press ENTER after solving the captcha')
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
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
        if 'Puzzleteil' in pagetext or 'Verifiziere' in pagetext:
            input('Press ENTER after solving the captcha')
            time.sleep(1)
        return True
    except:
        pass
    return False


def get_videolinks(driver):
    video_first_info = []
    # Scroller
    safety_counter = 0
    while safety_counter < 30:       #30
        start_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
        time.sleep(1)
        if safety_counter > 15:
            time.sleep(1)
        end_height = driver.execute_script("return document.body.scrollHeight")
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
        try:
            views = round(views)
        except:
            pass
        video = [views, link]
        video_first_info.append(video)
    video_first_info = sorted(video_first_info, key=lambda link: link[1], reverse=True)
    return video_first_info


def scrape_post(count, p_name, video_info):
    views = video_info[0]
    link = video_info[1]
    if not link or len(link) <= 10:
        return None, None
    if count == 0:
        go_to_page(driver, link)
    else:
        driver.get(link)
        time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if len(pagetext) <= 100 or 'Puzzleteil' in pagetext or 'Verifiziere' in pagetext or 'Schieberegler' in pagetext:
        input('Press ENTER after solving the captcha')
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
    if 'Seite nicht verfügbar' in pagetext or 'Fehler beim Anzeigen der Webseite' in pagetext:
        driver.get(link)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
    date_str = str(extract_text(soup.find('span', {'data-e2e': 'browser-nickname'})))
    if len(date_str) <= 4:
        if pagetext and len(pagetext) >= 100:
            date_str = pagetext.split(p_name,1)[1][:50].split('Folgen')[0].strip()
#    if len(date_str) <= 4:
#        return None, None
    if (not p_name[:3].lower() in date_str.lower() and not p_name[-3:].lower() in date_str.lower()) or \
            (not p_name[:3].lower() in link.lower() and not p_name[-3:].lower() in link.lower()):
        return None, None
    if '·' in date_str:
        date_str = date_str.split('·',1)[-1].strip()
    date_dt, date_str = get_approx_date(datetime.now(), date_str)
    if not date_dt:
        return None, None
    likes, comments, shares, dms = np.zeros(4)
    react_counts = soup.find_all('strong')
    for r in react_counts:
        line = str(r)
        number = extract_every_number(r.text)
        if 'like' in line:
            likes = number
        elif 'comment' in line:
            comments = number
        elif 'share' in line:
            shares = number
        elif 'undefined-count' in line:
            dms = number
    content_desc = extract_text(soup.find('h1', {'data-e2e': 'browse-video-desc'}))
    content_music = extract_text(soup.find('h4', {'data-e2e': 'browse-music'}))
    content = content_desc + ' ' + content_music
    if len(content) <= 10:
        content = get_visible_text(Comment, soup.find('div', class_='css-r4nwrj-DivVideoInfoContainer eqrezik3'))
        content = content.replace('mehr ','').strip()
    return date_dt, [date_str, likes, comments, shares, dms, views, link, content]
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    # Settings for the post crawler
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    import credentials_file as cred
    os.chdir(file_path)
    file ='Profile_' + platform + '_2024'
    df_source, dt, crawl_datestr, upper_dt, lower_dt = post_crawler_settings(file, platform, dt_str_now)

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)

    # Iterate over the companies
    for n, row in df_source.iterrows():
        id = str(row['ID'])
        url = str(row['url'])
        p_name = str(row['profile_name'])
        go_crawl = check_conditions(n, p_name, url, row, lower_dt, start_at=13)
        if not go_crawl:
            continue
        if 'bsn' in p_name.lower():
            break
        video_info_list = get_videolinks(driver)
        if not video_info_list or len(video_info_list) == 0:
            input('Press ENTER after solving website issues')
            video_info_list = get_videolinks(driver)
        if not video_info_list or len(video_info_list) == 0:
            continue
        data_per_company = []
        id_p = 0
#        error_index = video_info_list.index(video_info)
#        for count, video_info in enumerate(video_info_list[error_index:]):
        for count, video_info in enumerate(video_info_list):
            date_dt, scraped_postdata = scrape_post(count, p_name, video_info)
            print(scraped_postdata)
            if not date_dt:
                print('Date not found')
                continue
            if date_dt >= upper_dt:
                continue
            if date_dt < lower_dt:
                break
            id_p += 1
            full_row = [id, p_name, id_p, crawl_datestr] + scraped_postdata
            data_per_company.append(full_row)

        all_data += data_per_company

        # Create a DataFrame with all posts
        header1 = ['ID_A', 'profile_name', 'ID_P', 'Erhebung', 'Datum']
        header2 = ['Likes', 'Kommentare', 'Shares', 'DMs', 'Aufrufe', 'Link', 'Content']
        dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

        # Export dfPosts to Excel (with the current time)
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_' + platform + dt_str_now + '.xlsx'
        dfPosts.to_excel(file_name)

    driver.quit()

'''
time.sleep(4)
x,y = pyautogui.position()
print(str(x)+ "," + str(y))
time.sleep(4)
pyautogui.moveTo(1277,587)
pyautogui.click()
'''
