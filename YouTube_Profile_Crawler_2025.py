
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
startpage = 'https://www.youtube.com/'
platform = 'YouTube'
dt_str_now = None

upper_datelimit = '2025-10-01'
file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_Mineralwasser 2025'
file_name = 'Auswahl SMP Mineralwasser_2025-10-14'
file_type = '.xlsx'
source_file = file_path + '/' + file_name + file_type
########################################################################################################################


def base_url(url):
    to_remove = ['/videos', '/about', '/featured', '/playlists']
    for e in to_remove:
        if e in url:
            url = url.split(e)[0]
    if url[-1] == '/':
        url = url[:-1]
    return url

def open_and_check_page(link):
    try:
        driver.get(link)
        time.sleep(3)
    except:
        try:
            driver.get(link)
            time.sleep(5)
        except:
            return False
    status_code = requests.head(driver.current_url).status_code
    if status_code != 200:
        driver.get(link)
        time.sleep(5)
    status_code = requests.head(link).status_code
    if status_code != 200:
        return False
    return True

def open_description(driver):
    expand = driver.find_elements(By.CSS_SELECTOR, 'tp-yt-paper-button[id*="expand"]')
    if len(expand) > 1:
        for e in expand:
            try:
                e.click()
            except:
                pass
    elif len(expand) == 1:
        expand.click()

def get_likes(soup):
    likes = ''
    like_elem = soup.find('like-button-view-model')
    if like_elem:
        likes = extract_every_number((extract_text(like_elem)))
        if not like_elem or 'Mag' in str(likes):
            like_elem = soup.find('button', {'aria-label': lambda x: x and 'mag das Video' in x})
            if like_elem:
                like_text = extract_text(like_elem['aria-label'])
                if 'mag' in like_text.lower():
                    likes = extract_number(like_text)
    if likes == 'Mag ich':
        likes = ''
    return likes

def get_video_title(soup):
    title_elem = soup.find('h1',class_='style-scope ytd-watch-metadata')
    title = extract_text(title_elem)
    if len(str(title)) <= 4:
        titles = soup.find_all('h1')
        for t in titles:
            t_text = extract_text(t)
            if len(str(t_text)) >= 4:
                title = t_text
                break
    return title

def get_video_details(soup):
    date_str, date, views, desc = ['' for _ in range(4)]
    desc_elem = soup.find('div',{'id':'bottom-row'})
    full_desc = extract_text(desc_elem)
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
    if desc == '…':
        desc = ''
    return [date_str, date, views, desc]

def get_comment_number(driver,soup):
    comments = ''
    comments_elem = soup.find('h2',{'id':'count'})
    if comments_elem:
        comments_text = extract_text(comments_elem)
        if 'Kommentar' in comments_text or 'comment' in comments_text:
            comments = extract_number(comments_elem)
    else:
        for i in range(8):
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
        if not comments and str(comments) != '0':
            try:
                comments_elem = driver.find_element(By.CLASS_NAME, 'style-scope ytd-comments-header-renderer').text
                if 'Kommentar' in comments:
                    comments = extract_number(comments_elem)
            except:
                pass
    return comments


def crawl_video(driver, link):
    date, title, views, likes, comments, desc = ['' for _ in range(6)]
    page_status = open_and_check_page(link)
    if not page_status:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        pagetext = extract_text(soup)
        return [pagetext] + ['' for _ in range(6)]
    link = driver.current_url
    open_description(driver)
    driver.execute_script("window.scrollBy(0,1000)", "")
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source,'html.parser')
    pagetext = extract_text(soup)
    likes = get_likes(soup)
    title = get_video_title(soup)
    date_str, date, views, desc = get_video_details(soup)
    if '0 Kommentare' in pagetext:
        comments = 0
    if not 'Kommentare sind deaktiviert' in pagetext and not str(comments) == '0':
        comments = get_comment_number(driver, soup)
    return [date, title, views, likes, comments, link, desc]

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(url, comp_keywords):
    p_name, follower, total_posts, last_post, link, desc = ['' for _ in range(6)]
    url = base_url(url)
    driver.get(url + '/videos')
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = extract_text(get_visible_text(Comment, soup))
    if not pagetext or 'leider nicht verfügbar' in pagetext:
        return [p_name, follower, total_posts, last_post, url, 'page not available']
    restricted = ['potenziell ungeeignet für', 'dass du alt genug', 'leider nicht verfügbar']
    if any(e in pagetext for e in restricted) or len(pagetext) <= 1000:
        return [p_name, follower, total_posts, last_post, url, pagetext]
#    p_name = extract_text(soup.find('ytd-channel-name',{'id':'channel-name'}))
    name_options = soup.find_all('h1')
    for n in name_options:
        n_text = extract_text(n)
        if any(c.lower() in n_text.lower() for c in comp_keywords):
            p_name = n_text
            if len(p_name):
                break
#    follower_elem = extract_text(soup.find('yt-formatted-string',{'id':'subscriber-count'}))
    span_text = [extract_text(e) for e in soup.find_all('span')]
    for s in span_text:
        if 'Abonnenten' in s and not follower:
            follower = extract_every_number(s)
        if 'Videos' in s and not total_posts:
            total_posts = extract_every_number(s)
        if follower and total_posts:
            break
    video_d = soup.find_all('div', {'id': 'details'})
    if len(video_d) >= 1:
        videolinks = ['https://www.youtube.com' + v.find('a', href=True)['href'] for v in video_d if v.find('a', href=True)]
        if len(videolinks) >= 1:
            link = videolinks[0]
    driver.get(url + '/about')
    time.sleep(3)
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
    if len(link) >= 10:
        result_row = crawl_video(driver, link)
        last_post = result_row[0]
    return [p_name, follower, total_posts, last_post, url, desc]
########################################################################################################################

# Profile crawler
if __name__ == '__main__':
    # Settings for profile scraping
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)

    # Driver and Browser setup
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)
    start_ID = 0  # start the crawler at a specific ID

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
        comp_keywords = get_company_keywords(company, row, col_list)
        url = str(row[platform])
        if len(url) < 10:
            empty_row = [ID, company, dt_str] + ['' for _ in range(6)]
            data.append(empty_row)
            continue

        scraped_data = scrapeProfile(url, comp_keywords)
        full_row = [ID, company, dt_str] + scraped_data
        data.append(full_row)
        start_ID = ID + 1
        print(full_row)

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