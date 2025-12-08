
import os
import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import time
import pandas as pd
import re
from datetime import datetime, timedelta

import pyautogui

# Settings and paths for this program
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
startpage = 'https://www.tiktok.com/'
platform = 'TikTok'
dt_str_now = None

upper_datelimit = '2025-12-01'
folder_name = "SMP_Glücksspiel_2025"
file_name = "Auswahl SMP Glücksspiel_2025-12-01"
file_path = r"C:\Users\andre\OneDrive\Desktop/" + folder_name
source_file = file_name + ".xlsx"
########################################################################################################################

def check_for_captchas(soup, pagetext, link):
    if 'Puzzleteil' in pagetext or 'Verifiziere' in pagetext or 'Schieberegler' in pagetext:
        pyautogui.moveTo(x, y)
        pyautogui.click()
        driver.maximize_window()
        input('Press ENTER after solving the captcha')
        driver.get(link)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
        time.sleep(1)
    return soup, pagetext

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(link):
    p_name, pagelikes, follower, following, last_post, desc, userlink = ['' for i in range(7)]
    driver.get(link)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if 'Konto konnte nicht gefunden werden' in pagetext or 'Seite nicht verfügbar' in pagetext:
        return [p_name, '', '', '', '', link, '', pagetext]
    if not pagetext or len(pagetext) <= 100:
        soup, pagetext = check_for_captchas(soup, pagetext, link)
    header_elems = soup.find_all('h1',{'data-e2e':'user-title'})
    if len(header_elems) == 0:
        header_elems = soup.find_all('h1')
    if len(header_elems) >= 1:
        header = [extract_text(e) for e in header_elems]
        p_name = header[0]
    else:
        return [p_name, '', '', '', '', link, '', 'page not available']
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
    try:
        desc = get_visible_text(Comment, soup.find('h2',{'data-e2e':'user-bio'}))
    except:
        return [p_name, pagelikes, follower, following, last_post, link, userlink, 'check page for errors']
    if len(desc) <= 4:
        desc = pagetext
    userlink = soup.find('a',{'data-e2e':'user-link'},href=True)
    if userlink:
        userlink = userlink['href']
    if 'keine Videos veröffentlicht' in pagetext:
        return [p_name, pagelikes, follower, following, last_post, link, userlink, desc]
    if 'Profil enthält Themen' in pagetext:
        return [p_name, 'login required', follower, following, last_post, link, userlink, desc]
    links = [l['href'] for l in soup.find_all('a',href=True)]
    videolinks = list(set([l for l in links if 'video' in str(l)]))
    if len(videolinks) == 0:
        soup, pagetext = check_for_captchas(soup, pagetext, link)
        links = [l['href'] for l in soup.find_all('a', href=True)]
        videolinks = list(set([l for l in links if 'video' in str(l)]))
    if len(videolinks) == 0:
        return [p_name, pagelikes, follower, following, last_post, link, userlink, desc]

    videolinks.sort(reverse=True)
    last_video_link = videolinks[0]
    driver.get(last_video_link)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    name_date = extract_text(soup.find('span',{'data-e2e':'browser-nickname'}))
    if not name_date:
        name_date = extract_text(soup.find('span', {'class': 'css-1kcycbd-SpanOtherInfos evv7pft3'}))
    if '·' in name_date:
        date_str = name_date.split('·')[-1].strip()
        last_dt, last_post = get_approx_date(datetime.now().date(), date_str)
    return [p_name, pagelikes, follower, following, last_post, link, userlink, desc]
########################################################################################################################

# Profile crawler
if __name__ == '__main__':
    # Settings for profile scraping
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)
    col_names = list(df_source.columns)

    # Start crawling
    data = []
    start_ID = 0
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)
    first_captcha = None

    # Loop through the profiles
    for ID, row in df_source.iterrows():
        if 'ID' in col_list and col_list[0] != 'ID':
            ID = int(row['ID'])
        if not 'nan' in str(ID):
            ID = int(ID)
        if not str(ID).isdigit():
            break
        if ID < start_ID:  # If you want to skip some rows
            continue

        company = extract_text(row[comp_header])
        if len(company) <= 4 and 'Name in Studie' in col_names:
            company = extract_text(row['Name in Studie'])
        comp_keywords = get_company_keywords(company, row, col_list)
        link = str(row[platform])
        if len(link) < 10:
            empty_row = [ID, company, dt_str] + ['' for _ in range(8)]
            data.append(empty_row)
            continue
        if not first_captcha:
            soup, pagetext = check_for_captchas(soup, pagetext, link)
            first_captcha = True

        scraped_data = scrapeProfile(link)
        full_row = [ID, company, dt_str] + scraped_data
        data.append(full_row)
        print(ID,full_row[:-1])

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

    driver.quit()
########################################################################################################################

'''
time.sleep(4)
x,y = pyautogui.position()
print(str(x)+ "," + str(y))
time.sleep(4)
pyautogui.moveTo(1277,587)
pyautogui.click()
'''
