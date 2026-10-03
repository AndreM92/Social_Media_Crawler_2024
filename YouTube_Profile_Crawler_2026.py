
import os
import sys
import json
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import time
import random
import pandas as pd
import re
from datetime import datetime, timedelta

# Settings
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
startpage = 'https://www.youtube.com/'
platform = 'YouTube'

folder_name = "SMP_Rüstungsunternehmen_2026"
file_name = "Auswahl_1_Rüstungsunternehmen_2026_20261001"
upper_datelimit = '2026-10-01'
file_path = r"C:\Users\andre\OneDrive\Desktop/" + folder_name
source_file = file_name + ".xlsx"

sys.path.insert(0, path_to_crawler_functions)
from crawler_functions import *

########################################################################################################################
# The channel data is part of the page source as JSON (ytInitialData):
# - channelMetadataRenderer: name, description, channel id; pageHeaderViewModel: handle, subscribers, videos
# - The latest post is the latest of the tabs "Videos", "Shorts" and "Live" (the first item of each tab);
#   its exact date is read from the watch page (publishDate)

restricted = ['potenziell ungeeignet für', 'dass du alt genug', 'leider nicht verfügbar', 'Dieser Kanal ist nicht verfügbar',
              'Dieser Kanal existiert nicht']

def base_url(url):
    url = str(url).split('?')[0]
    for e in ['/videos', '/about', '/featured', '/playlists', '/shorts', '/streams', '/community', '/posts']:
        if e in url:
            url = url.split(e)[0]
    url = url.replace('://youtube.com', '://www.youtube.com').replace('://m.youtube.com', '://www.youtube.com')
    if url[-1] == '/':
        url = url[:-1]
    return url

def get_initial_data(html):
    match = re.search(r'(?:var ytInitialData|window\["ytInitialData"\])\s*=\s*(\{.*?\});\s*</script>', html, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except:
        return {}

def find_keys(obj, key, found=None):
    if found is None:
        found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                found.append(v)
            find_keys(v, key, found)
    elif isinstance(obj, list):
        for x in obj:
            find_keys(x, key, found)
    return found

# Captchas ("Bestätige, dass du kein Bot bist") have to be solved manually
def check_for_captchas(link):
    if 'google.com/sorry' in driver.current_url or 'kein Bot' in driver.page_source[:200000]:
        driver.maximize_window()
        input('Press ENTER after solving the captcha')
        driver.get(link)
        time.sleep(4)

def open_page(link):
    driver.get(link)
    time.sleep(random.uniform(3, 4.5))
    check_for_captchas(link)
    return driver.page_source

# Channel data from the JSON in the page source
def get_channel_data(data):
    channel = {'p_name': '', 'desc': '', 'handle': '', 'channel_id': '', 'follower': '', 'all_posts': ''}
    meta = find_keys(data, 'channelMetadataRenderer')
    if meta:
        channel['p_name'] = meta[0].get('title', '')
        channel['desc'] = extract_text(meta[0].get('description', '')) or ''
        channel['channel_id'] = meta[0].get('externalId', '')
        vanity = meta[0].get('vanityChannelUrl', '') or ''
        if '/@' in vanity:
            channel['handle'] = '@' + vanity.split('/@', 1)[1]
    header = find_keys(data, 'pageHeaderViewModel')
    texts = [t.get('content', '') for t in find_keys(header, 'text') if isinstance(t, dict)]
    for t in texts:
        if t.startswith('@') and not channel['handle']:
            channel['handle'] = t
        elif 'Abonnent' in t or 'subscriber' in t:
            channel['follower'] = extract_every_number(t.split('Abonnent')[0].split('subscriber')[0].strip())
        elif re.search(r'\bVideos?\b', t):
            channel['all_posts'] = extract_every_number(t.split('Video')[0].strip())
    return channel

# First (latest) item of a tab ("videos", "shorts" or "streams"), upcoming streams are ignored
def get_first_video_id(data):
    for item in find_keys(data, 'richItemRenderer'):
        if find_keys(item, 'upcomingEventData'):
            continue
        ids = find_keys(item, 'videoId')
        if ids:
            return ids[0]
    return None

# Exact publishing date from the watch page
def get_publish_date(video_id):
    html = open_page(f'https://www.youtube.com/watch?v={video_id}')
    # The date is given with the time zone of YouTube (e.g. "2026-09-30T23:57:33-07:00"), so it's converted to local time
    match = re.search(r'"publishDate":"([^"]+)"', html) or re.search(r'"uploadDate":"([^"]+)"', html)
    if not match:
        return None
    try:
        publish_dt = datetime.fromisoformat(match.group(1))
        if publish_dt.tzinfo:
            publish_dt = publish_dt.astimezone().replace(tzinfo=None)
        return datetime(publish_dt.year, publish_dt.month, publish_dt.day)
    except:
        return datetime.strptime(match.group(1)[:10], '%Y-%m-%d')

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(url):
    url = base_url(url)
    html = open_page(url + '/videos')
    soup = BeautifulSoup(html, 'lxml')
    pagetext = extract_text(get_visible_text(Comment, soup)) or ''
    if not pagetext:
        # Old channel urls (/user/...) are sometimes not loaded on the first try
        html = open_page(url + '/videos')
        soup = BeautifulSoup(html, 'lxml')
        pagetext = extract_text(get_visible_text(Comment, soup)) or ''
    data = get_initial_data(html)
    channel = get_channel_data(data)
    # Only a page without channel data counts as not available (the words can also appear in other texts)
    if not channel['p_name'] and (not pagetext or any(e in pagetext for e in restricted)):
        time.sleep(3)
        html = open_page(url + '/videos')
        soup = BeautifulSoup(html, 'lxml')
        pagetext = extract_text(get_visible_text(Comment, soup)) or ''
        data = get_initial_data(html)
        channel = get_channel_data(data)
        if not channel['p_name']:
            return ['', '', '', 'Kanal nicht verfügbar', url, pagetext[:300], '', '', '', '', '']
    # Sometimes the channel data is missing in the first page load
    if not channel['p_name'] or not find_keys(data, 'pageHeaderViewModel'):
        time.sleep(2)
        html = open_page(url + '/videos')
        soup = BeautifulSoup(html, 'lxml')
        data = get_initial_data(html)
        channel = get_channel_data(data)
    if not channel['p_name']:
        h1 = soup.find('h1')
        channel['p_name'] = extract_text(h1) if h1 else ''

    # Latest video, short and live stream
    latest = {}
    first_ids = {'videos': get_first_video_id(data)}
    for tab in ['shorts', 'streams']:
        first_ids[tab] = get_first_video_id(get_initial_data(open_page(f'{url}/{tab}')))
    for tab, video_id in first_ids.items():
        if video_id:
            latest[tab] = get_publish_date(video_id)
    dates = [d for d in latest.values() if d and d <= datetime.now()]
    if dates:
        last_post = max(dates).strftime('%d.%m.%Y')
    elif any(first_ids.values()):
        last_post = 'Beiträge vorhanden (Datum unbekannt)'
    else:
        last_post = 'Keine Beiträge'
    as_str = lambda d: d.strftime('%d.%m.%Y') if d else ''

    return [channel['p_name'], channel['follower'], channel['all_posts'], last_post, url, channel['desc'],
            channel['handle'], as_str(latest.get('videos')), as_str(latest.get('shorts')),
            as_str(latest.get('streams')), channel['channel_id']]
########################################################################################################################

# Profile crawler
if __name__ == '__main__':
    # Settings for profile scraping
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
        url = str(row[platform])
        if len(url) < 10:
            empty_row = [ID, company, dt_str] + ['' for _ in range(11)]
            data.append(empty_row)
            continue
        try:
            scraped_data = scrapeProfile(url)
        except Exception as e:
            print(f'Error: {e}')
            scraped_data = ['', '', '', 'Fehler: ' + str(e)[:100], url, '', '', '', '', '', '']
        full_row = [ID, company, dt_str] + scraped_data
        data.append(full_row)
        print(full_row[:7] + full_row[9:13])

    # DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'follower', 'all_posts', 'last_post', 'url', 'description',
              'handle', 'last_video', 'last_short', 'last_stream', 'channel_id']
    df_profiles = pd.DataFrame(data, columns=header)

    # Export to Excel
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()
