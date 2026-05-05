
import os
import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import time
import pandas as pd
import re
from datetime import datetime, timedelta

# Settings and paths for this program
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
startpage = 'https://www.tiktok.com/'
platform = 'TikTok'
dt_str_now = None

upper_datelimit = '2026-03-01'
file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_ÖPNV_2026'
########################################################################################################################

def check_for_captchas(driver, Comment):
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if 'Puzzleteil' in pagetext or 'Verifiziere' in pagetext or 'Schieberegler' in pagetext:
        driver.maximize_window()
        input('Press ENTER after solving the captcha')
    return None

def check_conditions(id, p_name, link, row, lower_dt, start_at=0):
    if id < start_at:      # If you want to skip some rows
        return False
    if len(p_name) == 0 or p_name.lower() == 'nan' or p_name == 'None':
        return False
    if len(link) < 10 or 'Keine Beiträge' in posts:
        print([id, p_name, link])
        return False
    try:
        driver.get(link)
        time.sleep(3)
        check_for_captchas(driver, Comment)
        return True
    except:
        pass
    return False

def scrape_post(row):
    ID_A = row['ID']
    p_name = row['profile_name']
    ID_P = row['ID_P']
    views = row['Aufrufe']
    if str(views)[0].isdigit():
        views = int(views)
    else:
        views = ''
    link = str(row['URL'])
    driver.get(link)
    time.sleep(4)
    check_for_captchas(driver, Comment)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if not pagetext or len(pagetext) <= 200 or 'Seite nicht verfügbar' in pagetext or 'Fehler beim Anzeigen der Webseite' in pagetext:
        return None, None
    date_str = str(extract_text(soup.find('div', class_ = 'css-f1s7n1-7937d88b--DivCreatorInfoContainer e1td56050')))
    if '·' in date_str:
        date_str = date_str.split('·',1)[-1].strip()
    date_dt, date_str = get_approx_date(datetime.now(), date_str)
    if not date_dt:
        return None, None
    likes, comments, shares, dms = ['' for _ in range(4)]
    react_counts = soup.find_all('strong')
    for r in react_counts:
        line = str(r)
        number = extract_every_number(r.text)
        if 'like' in line and not likes:
            likes = number
        elif 'comment' in line and not comments:
            comments = number
        elif 'share' in line and not shares:
            shares = number
        elif 'favorite-count' in line and not dms:
            dms = number
    content = extract_text(soup.find('div', {'data-e2e': 'video-desc'}))
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
    if not shares:
        shares = 0
    today = datetime.now().strftime("%d.%m.%Y")
    return date_dt, [ID_A, p_name, ID_P, today, date_str, likes, comments, shares, dms, views, link, content]

#time.sleep(3)
x,y = (1204, 1051)
#x,y = pyautogui.position()
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    # Settings for the post crawler
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    os.chdir(file_path)
    file_p = 'Profile_' + platform + '_' + str(datetime.now().year)
    file_l ='Videolinks_' + platform
    df_source, dt, crawl_datestr, upper_dt, lower_dt = post_crawler_settings(file_p, platform, None, upper_datelimit)
    df_source = df_source.set_index('ID')
    col_names = list(df_source.columns)

    filename = None
    for f in os.listdir():
        if not filename and file_l in f:
            filename = f
    if not filename:
        print('File not found')
        exit()
    df_source_l = pd.read_excel(filename)

    # Driver and Browser setup
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)
    first_captcha = None
    start_ID = 0 #start the crawler at a specific ID

    # Iterate over the companies
    for ID, row in df_source_l.iterrows():
        if ID < start_ID:
            continue
        if len(data) == 0:
            check_for_captchas(driver, Comment)
        date_dt, datarow = scrape_post(row)
        if not date_dt:
            print('second round')
            date_dt, datarow = scrape_post(row)
        print(datarow)
        start_ID = ID + 1
        if not date_dt:
            print('Date not found')
            break
            continue
        if date_dt >= upper_dt:
            continue
        if date_dt > lower_dt:
            data.append(datarow)
#        print(datetime.now().strftime("%Y-%m-%d_%H_%M_%S"))

    # Create a DataFrame with all posts
    header1 = ['ID_A', 'profile_name', 'ID_P', 'Erhebung', 'Datum']
    header2 = ['Likes', 'Kommentare', 'Shares', 'DMs', 'Aufrufe', 'Link', 'Content']
    dfPosts = pd.DataFrame(data, columns=header1 + header2)

    # Export dfPosts to Excel (with the current time)
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    file_name = 'Beiträge_' + platform + '_' + dt_str_now + '.xlsx'
    dfPosts.to_excel(file_name)

    driver.quit()


'''

#    date_str = str(extract_text(soup.find('span', {'data-e2e': 'browser-nickname'})))
    if len(date_str) <= 4 or not any(e.isdigit() for e in [e for e in date_str]):
        date_str = str(extract_text(soup.find('div', class_ = 'css-m5q4d-5e6d46e3--DivCreatorInfoContainer e1td56050')))
    if len(date_str) <= 4 or not any(e.isdigit() for e in [e for e in date_str]):
        if pagetext and len(pagetext) >= 100:
            date_str = pagetext.split(p_name,1)[1][:50].split('Folgen')[0].strip()
    if (not p_name[:3].lower() in date_str.lower() and not p_name[-3:].lower() in date_str.lower()) and \
            (not p_name[:3].lower() in link.lower() and not p_name[-3:].lower() in link.lower()):
        return None, None

    if len(date_str) > 10:
        date_str = date_str.split()[0]
'''