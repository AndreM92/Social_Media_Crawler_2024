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
startpage = 'https://www.youtube.com/'
platform = 'YouTube'
dt_str_now = None
########################################################################################################################

def crawlVideo(link):
    try:
        driver.get(link)
        time.sleep(3)
    except:
        return ''
    date, title, views, likes, comments, link, desc = ['' for _ in range(7)]
    link = driver.current_url
    expand = driver.find_elements(By.CSS_SELECTOR, 'tp-yt-paper-button[id*="expand"]')
    if len(expand) > 1:
        for e in expand:
            try:
                e.click()
            except:
                pass
    elif len(expand) == 1:
        expand.click()
    driver.execute_script("window.scrollBy(0,1000)", "")
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source,'html.parser')
    pagetext = extract_text(soup)
    like_elem = soup.find('like-button-view-model')
    if like_elem:
        likes = extract_every_number((extract_text(like_elem)))
        if likes == 'Mag ich':
            likes = ''
            like_elem = ''
    if not like_elem:
        like_elem = soup.find('button', {'aria-label': lambda x: x and 'mag das Video' in x})
        if like_elem:
            like_text = extract_text(like_elem['aria-label'])
            if 'mag' in like_text.lower():
                likes = extract_number(like_text)
    title_elem = soup.find('h1',class_='style-scope ytd-watch-metadata')
    title = extract_text(title_elem)
    if len(str(title)) <= 4:
        titles = soup.find_all('h1')
        for t in titles:
            t_text = extract_text(t)
            if len(str(t_text)) >= 4:
                title = t_text
                break
    desc_elem = soup.find('div',{'id':'bottom-row'})
    full_desc = extract_text(desc_elem)
    date_str = ''
    if full_desc:
        desc = full_desc
        if 'Weniger anzeigen' in desc:
            desc = desc.split('Weniger anzeigen',1)[1].strip()
        if '...mehr' in desc:
            desc = desc.split('...mehr')[0].strip()
        desc_l = full_desc.split()
        for pos, e in enumerate(desc_l):
            if 'Aufruf' in e and views == '':
                views = extract_every_number(desc_l[pos-1])
            if '.201' in e or '.202' in e and date_str == '':
                date_opt = e.strip()
                try:
                    date_dt = datetime.strptime(date_opt, "%d.%m.%Y")
                    date = date_dt.strftime("%d.%m.%Y")
                except:
                    pass
            if views != '' and date != '':
                break
    if 'Kommentare sind deaktiviert' in pagetext:
        comments = ''
        return [date, title, views, likes, comments, link, desc]
    comments_elem = soup.find('h2',{'id':'count'})
    if comments_elem:
        comments_text = extract_text(comments_elem)
        if 'Kommentar' in comments_text or 'comment' in comments_text:
            comments = extract_number(comments_elem)
    else:
        for i in range(5):
            driver.execute_script("window.scrollBy(0,400)", "")
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            comments_elem = soup.find('h2', {'id': 'count'})
            if comments_elem:
                comments_text = extract_text(comments_elem)
                if 'Kommentar' in comments_text or 'comment' in comments_text:
                    comments = extract_number(comments_elem)
            if comments != '':
                break
        if comments == '':
            try:
                comments_elem = driver.find_element(By.CLASS_NAME, 'style-scope ytd-comments-header-renderer').text
                if 'Kommentar' in comments:
                    comments = extract_number(comments_elem)
            except:
                pass
    crawled_row = [date, title, views, likes, comments, link, desc]
    return crawled_row


# A function to open the targetpage and scrape the profile stats
def scrapeProfile(url):
    p_name, follower, total_posts, last_post, v_link, desc = ['' for i in range(6)]
    transform_url = ['/videos', '/about', '/featured', '/playlists']
    for e in transform_url:
        url = url.replace(e,'')
    if url[-1] == '/':
        url = url[:-1]
    driver.get(url + '/videos')
    time.sleep(3)
    new_url = driver.current_url.replace('/videos','')
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = extract_text(get_visible_text(Comment, soup))
    restricted = ['potenziell ungeeignet für', 'dass du alt genug', 'leider nicht verfügbar']
    if any(e in pagetext for e in restricted) or len(pagetext) <= 1000:
        return [p_name, follower, total_posts, last_post, new_url, pagetext]
    p_name = extract_text(soup.find('ytd-channel-name',{'id':'channel-name'}))
    if p_name and len(p_name) >= 3 and ' ' in p_name:
        p_name1 = p_name[:round((len(p_name)/2))].strip()
        p_name2 = p_name[round((len(p_name)/2)):].strip()
        if p_name1[:-1] in p_name2:
            p_name = p_name1
    follower_elem = extract_text(soup.find('yt-formatted-string',{'id':'subscriber-count'}))
    if follower_elem and 'abonnent' in follower_elem.lower():
        follower = extract_every_number(follower_elem)
    videocount_elem = extract_text(soup.find('yt-formatted-string',{'id':'videos-count'}))
    if videocount_elem and 'video' in videocount_elem.lower():
        total_posts = extract_every_number(videocount_elem)
    video_d = soup.find_all('div', {'id': 'details'})
    if len(video_d) >= 1:
        videolinks = ['https://www.youtube.com' + v.find('a', href=True)['href'] for v in video_d if v.find('a', href=True)]
        if len(videolinks) >= 1:
            v_link = videolinks[0]
    driver.get(new_url + '/about')
    time.sleep(2)
    if not '/about' in driver.current_url:
        try:
            desc_link = driver.find_element('xpath', "//*[contains(text(), 'weitere Links')]")
            desc_link.click()
            time.sleep(2)
        except:
            pass
    soup = BeautifulSoup(driver.page_source, 'lxml')
    desc_elem = soup.find('tp-yt-paper-dialog')
    if desc_elem:
        desc = get_visible_text(Comment, desc_elem).replace('Kanalinfo','').strip()

    # Get the date of the latest video
    if len(v_link) >= 10:
        result_row = crawlVideo(v_link)
        last_post = result_row[0]
    return [p_name, follower, total_posts, last_post, new_url, desc]
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
            empty_row = [id, company, dt_str] + ['' for _ in range(6)]
            data.append(empty_row)
            continue

        scraped_data = scrapeProfile(url)
        full_row = [id, company, dt_str] + scraped_data
        data.append(full_row)
        print(count,full_row[:-1])

    # DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'follower', 'all_posts', 'last_post', 'url', 'description']
    df_profiles = pd.DataFrame(data, columns=header)
    df_profiles.set_index('ID')

    # Export to Excel
#    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()

########################################################################################################################
# Collect all the videolinks after scrolling
def getVideolinks(url):
    transform_url = ['/videos', '/about', '/featured', '/playlists']
    for e in transform_url:
        url = url.replace(e, '')
    if url[-1] == '/':
        url = url[:-1]
    try:
        driver.get(url + '/videos')
        time.sleep(3)
    except:
        return []
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = extract_text(get_visible_text(Comment, soup))
    if 'potenziell unangemessene Inhalte' in pagetext or 'existiert nicht' in pagetext or 'Automatisch von YouTube erstellt' in pagetext:
        return []
    scrolls = 0
    while True:
        old_dates = [f'vor {i} Jahren' for i in range(2, 11)]
        if any(date in pagetext for date in old_dates):
            break
        scrheight = driver.execute_script("return document.documentElement.scrollHeight")
        driver.execute_script("window.scrollBy(0, 3000);")
        scrolls += 1
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = extract_text(get_visible_text(Comment, soup))
        newheight = driver.execute_script("return document.documentElement.scrollHeight")
        if scrheight == newheight or scrolls == 10:
            break
    videos = soup.find_all('div',{'id':'details'})
    videolinks = ['https://www.youtube.com' + v.find('a',href=True)['href'] for v in videos if v.find('a',href=True)]
#    print(f'Anzahl der Videolinks: {len(videolinks)}')
    return videolinks

########################################################################################################################