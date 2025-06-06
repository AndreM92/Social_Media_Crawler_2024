
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

#time.sleep(3)
x,y = (1204, 1051)
#x,y = pyautogui.position()

# Settings and paths for this program
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
startpage = 'https://www.tiktok.com/'
platform = 'TikTok'
dt_str_now = None

upper_datelimit = '2025-05-01'
file_path = r"C:\Users\andre\OneDrive\Desktop\SMP_Banken_2025"
source_file = file_path + '\Auswahl_SMP Banken 2025_2025-04-01.xlsx'
branch_keywords = ['Bank', 'Finanz', 'Anlage', 'Anleg', 'Kurs', 'Aktie', 'Institut', 'Geld', 'Vermögen', 'Spar',
                   'dienstleist']
#branch_keywords = ['nutrition', 'vitamin', 'mineral', 'protein', 'supplement', 'diet', 'health', 'ernährung',
#                   'ergänzung', 'gesundheit', 'nährstoff', 'fitness', 'sport', 'leistung']
#file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
#source_file = "Liste_Nahrungsergänzungsmittel_2024_Auswahl.xlsx"
########################################################################################################################
def check_for_captchas(soup, pagetext, link):
    if 'Puzzleteil' in pagetext or 'Verifiziere' in pagetext or 'Schieberegler' in pagetext:
        pyautogui.moveTo(x, y)
        pyautogui.click()
        driver.maximize_window()
        input('Press ENTER after solving the captcha')
        driver.get(link)
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
        time.sleep(1)
    return soup, pagetext


# A function to open the targetpage and scrape the profile stats
def scrapeProfile(link):
    p_name, pagelikes, follower, following, last_post, desc = ['' for i in range(6)]
    driver.get(link)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if 'Konto konnte nicht gefunden werden' in pagetext or 'Seite nicht verfügbar' in pagetext:
        return [p_name, '', '', '', '', url, '', pagetext]
    if not pagetext or len(pagetext) <= 100:
        soup, pagetext = check_for_captchas(soup, pagetext, link)
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
                if not str(i)[0].isdigit():
                    continue
                if 'Like' in i:
                    pagelikes = extract_every_number(i.split('Like')[0].strip())
                elif 'Follower' in i:
                    follower = extract_every_number(i.split('Follower')[0].strip())
                elif 'Folge' in i or 'Gefolgt' in i:
                    following = extract_every_number(i.split('Folge')[0].strip())
    desc = get_visible_text(Comment, soup.find('h2',{'data-e2e':'user-bio'}))
    if len(desc) <= 4:
        desc = pagetext
    userlink = soup.find('a',{'data-e2e':'user-link'},href=True)
    if userlink:
        userlink = userlink['href']
    if 'keine Videos veröffentlicht' in pagetext:
        return [p_name, pagelikes, follower, following, last_post, url, userlink, desc]
    if 'Profil enthält Themen' in pagetext:
        return [p_name, 'login required', follower, following, last_post, url, userlink, desc]
    links = [l['href'] for l in soup.find_all('a',href=True)]
    videolinks = list(set([l for l in links if 'video' in str(l)]))
    if len(videolinks) == 0:
        soup, pagetext = check_for_captchas(soup, pagetext)
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
    col_names = list(df_source.columns)

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
        if len(company) <= 4 and 'Name in Studie' in col_names:
            company = extract_text(row['Name in Studie'])
        comp_keywords = get_company_keywords(company, row, col_list)
        url = str(row[platform])
        if len(url) < 10:
            empty_row = [id, company, dt_str] + ['' for _ in range(8)]
            data.append(empty_row)
            continue

        scraped_data = scrapeProfile(url)
        full_row = [count, company, dt_str] + scraped_data
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
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '2.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()

########################################################################################################################
# Post Crawler functions
def check_conditions(id, p_name, link, row, lower_dt, start_at=0):
    if id < start_at:      # If you want to skip some rows
        return False
    if len(p_name) == 0 or p_name.lower() == 'nan' or p_name == 'None':
        return False
    posts = str(row['last_post'])
    if len(link) < 10 or len(posts) <= 4 or 'Keine Beiträge' in posts:
        print([id, p_name, link])
        return False
    try:
        last_datestr = extract_text(row['last_post'])
        last_dt = datetime.strptime(last_datestr, "%d.%m.%Y")
        if (last_dt + timedelta(days=31)) < lower_dt:
            return False
        driver.get(link)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
        soup, pagetext = check_for_captchas(soup, pagetext, link)
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
            driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
            break
        safety_counter += 1
    time.sleep(1)
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
    if not link:
        link = driver.current_url
    if not link or len(link) <= 10:
        return None, None
    if count == 0:
        go_to_page(driver, link)
        time.sleep(3)
    else:
        driver.get(link)
        time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if len(pagetext) <= 300:
        soup, pagetext = check_for_captchas(soup, pagetext, link)
    if 'Seite nicht verfügbar' in pagetext or 'Fehler beim Anzeigen der Webseite' in pagetext:
        return None, None
    date_str = str(extract_text(soup.find('span', {'data-e2e': 'browser-nickname'})))
    if len(date_str) <= 4:
        if pagetext and len(pagetext) >= 100:
            date_str = pagetext.split(p_name,1)[1][:50].split('Folgen')[0].strip()
#    if len(date_str) <= 4:
#        return None, None
    if (not p_name[:3].lower() in date_str.lower() and not p_name[-3:].lower() in date_str.lower()) and \
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
    content = extract_text(soup.find('div', {'data-e2e': 'browse-video-desc'}))
    if not content or len(str(content)) <= 4:
        content = extract_text(soup.find('h1', {'data-e2e': 'browse-video-desc'}))
    if not content or len(str(content)) <= 4:
        content = extract_text(soup.find('span', class_='tiktok-j2a19r-SpanText efbd9f0'))
    if not content or len(str(content)) <= 4:
        content = extract_text(soup.find('span', class_='css-j2a19r-SpanText efbd9f0'))
    if len(str(content)) <= 4:
        print('Kein Content gefunden')
        content = pagetext.split('mehr ')[-1]
        if 'Anmelden' in content:
            content = content.split('Anmelden ')[0].strip()
    return date_dt, [date_str, likes, comments, shares, dms, views, link, content]
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    # Settings for the post crawler
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    import credentials_file as cred
    os.chdir(file_path)
    file ='Profile_' + platform + '_2025'
    df_source, dt, crawl_datestr, upper_dt, lower_dt = post_crawler_settings(file, platform, dt_str_now, upper_datelimit)
    col_names = list(df_source.columns)

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)

    # Iterate over the companies
    for id, row in df_source.iterrows():
        if 'ID_new' in col_names:
            id = row['ID_new']
        elif 'ID' in col_names:
            id = row['ID']
        url = str(row['url'])
        p_name = str(row['profile_name'])
        go_crawl = check_conditions(id, p_name, url, row, lower_dt, start_at=0)
        if not go_crawl:
            continue

        video_info_list = get_videolinks(driver)
        if not video_info_list or len(video_info_list) == 0:
            input('Press ENTER after solving website issues')
            video_info_list = get_videolinks(driver)
        if not video_info_list or len(video_info_list) == 0:
            continue
        data_per_company = []
        id_p = 0
        error_index = 0
        for count, video_info in enumerate(video_info_list[error_index:]):
            error_index = video_info_list.index(video_info)
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
        file_name = 'Beiträge_' + platform + '_' + dt_str_now + '.xlsx'
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
