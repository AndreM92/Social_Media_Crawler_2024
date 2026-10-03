
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

# Settings and paths for this program
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
startpage = 'https://www.tiktok.com/'
platform = 'TikTok'

folder_name = "SMP_Rüstungsunternehmen_2026"
file_name = "Auswahl_1_Rüstungsunternehmen_2026_20261001"
upper_datelimit = '2026-10-01'
file_path = r"C:\Users\andre\OneDrive\Desktop/" + folder_name
source_file = file_name + ".xlsx"

sys.path.insert(0, path_to_crawler_functions)
from crawler_functions import *

########################################################################################################################
# The crawler works without login:
# - Without login TikTok doesn't show the video list on the profile page, but the profile data is part of the
#   page source as JSON (script#__UNIVERSAL_DATA_FOR_REHYDRATION__)
# - The latest videos are taken from the creator embed (https://www.tiktok.com/embed/@name), which works without login
# - The video id contains the publishing time (video id >> 32 = seconds since 1970)

# Decline the optional cookies (the banner is inside a shadow root)
def decline_cookies():
    try:
        return driver.execute_script("""
            const banner = document.querySelector('tiktok-cookie-banner');
            const root = banner && banner.shadowRoot;
            if (!root) return false;
            const button = [...root.querySelectorAll('button')].find(b => /ablehnen|decline/i.test(b.innerText));
            if (button) { button.click(); return true; }
            return false;""")
    except:
        return False

# The captcha has to be solved manually
def check_for_captchas(link):
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    captcha_elem = soup.select_one('#captcha-verify-container, .captcha_verify_container, .captcha-verify-container, '
                                   'iframe[src*="captcha"]')
    if captcha_elem or any(w in pagetext for w in ['Puzzleteil', 'Verifiziere', 'Schieberegler']):
        driver.maximize_window()
        input('Press ENTER after solving the captcha')
        driver.get(link)
        time.sleep(4)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
    return soup, pagetext

# Clean profile url: https://www.tiktok.com/@name
def clean_url(link):
    match = re.search(r'tiktok\.com/@([^/?#]+)', str(link))
    if not match:
        return None, None
    return f'https://www.tiktok.com/@{match.group(1)}', match.group(1)

def get_json_data(soup, script_id):
    script = soup.find('script', id=script_id)
    if not script or not script.string:
        return {}
    try:
        return json.loads(script.string)
    except:
        return {}

def date_from_video_id(video_id):
    try:
        return datetime.fromtimestamp(int(video_id) >> 32)
    except:
        return None

# Profile data from the JSON in the page source
def get_profile_data(soup):
    data = get_json_data(soup, '__UNIVERSAL_DATA_FOR_REHYDRATION__')
    user_detail = data.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
    user_info = user_detail.get('userInfo', {})
    user = user_info.get('user', {})
    stats = user_info.get('stats', {}) or user_info.get('statsV2', {})
    if not user:
        return None
    created = user.get('createTime')
    return {'p_name': user.get('nickname', ''),
            'username': user.get('uniqueId', ''),
            'pagelikes': stats.get('heartCount', stats.get('heart', '')),
            'follower': stats.get('followerCount', ''),
            'following': stats.get('followingCount', ''),
            'videos': stats.get('videoCount', ''),
            'desc': user.get('signature', ''),
            'desc_link': (user.get('bioLink') or {}).get('link', ''),
            'verified': 1 if user.get('verified') else 0,
            'private': 1 if user.get('privateAccount') else 0,
            'account_created': datetime.fromtimestamp(int(created)).strftime('%d.%m.%Y') if created else ''}

# Fallback: profile data from the visible page (old method)
def get_profile_data_from_page(soup, pagetext):
    p_name, pagelikes, follower, following, desc, desc_link = ['' for _ in range(6)]
    header_elems = soup.find_all('h1', {'data-e2e': 'user-title'}) or soup.find_all('h1')
    if header_elems:
        p_name = extract_text(header_elems[0])
    for e in soup.find_all(['strong', 'h3']):
        data_e2e = e.get('data-e2e', '')
        if data_e2e == 'likes-count':
            pagelikes = extract_every_number(extract_text(e))
        elif data_e2e == 'followers-count':
            follower = extract_every_number(extract_text(e))
        elif data_e2e == 'following-count':
            following = extract_every_number(extract_text(e))
    desc_elem = soup.find('h2', {'data-e2e': 'user-bio'})
    desc = extract_text(desc_elem) if desc_elem else ''
    link_elem = soup.find('a', {'data-e2e': 'user-link'}, href=True)
    if link_elem:
        desc_link = link_elem['href']
    return {'p_name': p_name, 'username': '', 'pagelikes': pagelikes, 'follower': follower, 'following': following,
            'videos': '', 'desc': desc or pagetext, 'desc_link': desc_link, 'verified': '', 'private': '',
            'account_created': ''}

# Latest video from the creator embed (about 10 of the latest videos, pinned videos included)
def get_last_post(username):
    embed_link = f'https://www.tiktok.com/embed/@{username}'
    driver.get(embed_link)
    time.sleep(random.uniform(4, 6))
    soup, pagetext = check_for_captchas(embed_link)
    data = get_json_data(soup, '__FRONTITY_CONNECT_STATE__')
    video_ids = []
    for key, value in data.get('source', {}).get('data', {}).items():
        if isinstance(value, dict) and isinstance(value.get('videoList'), list):
            video_ids += [v.get('id') for v in value['videoList']
                          if v.get('id') and str(v.get('authorUniqueId', username)).lower() == username.lower()]
    if not video_ids:
        # Fallback: video links in the embed
        video_ids = re.findall(rf'/@{re.escape(username)}/video/(\d+)', driver.page_source)
    video_dates = [date_from_video_id(v) for v in video_ids]
    video_dates = [d for d in video_dates if d]
    if not video_dates:
        return None
    return max(video_dates).strftime('%d.%m.%Y')

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(link):
    url, username = clean_url(link)
    if not url:
        return ['', '', '', '', 'Kein gültiger TikTok-Link', link, '', '', '', '', '', '', '']
    driver.get(url)
    time.sleep(random.uniform(3, 5))
    soup, pagetext = check_for_captchas(url)
    if any(t in pagetext for t in ['Konto konnte nicht gefunden werden', 'Seite nicht verfügbar',
                                   "Couldn't find this account"]):
        return ['', '', '', '', 'Konto nicht gefunden', url, '', pagetext[:300], '', '', '', '', username]

    profile = get_profile_data(soup) or get_profile_data_from_page(soup, pagetext)
    username = profile['username'] or username

    # Were videos published at all and if possible, when was the latest one?
    if profile['private']:
        last_post = 'Privates Konto'
    elif profile['videos'] == 0 or 'keine Videos veröffentlicht' in pagetext:
        last_post = 'Keine Beiträge'
    else:
        last_post = get_last_post(username)
        if not last_post:
            last_post = 'Beiträge vorhanden (Datum unbekannt)' if profile['videos'] else 'Keine Beiträge gefunden'

    return [profile['p_name'], profile['pagelikes'], profile['follower'], profile['following'], last_post, url,
            profile['desc_link'], profile['desc'], profile['videos'], profile['verified'], profile['private'],
            profile['account_created'], username]
########################################################################################################################

# Profile crawler
if __name__ == '__main__':
    # Settings for profile scraping
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)
    col_names = list(df_source.columns)

    # Start crawling
    data = []
    start_ID = 0
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    driver.get(startpage)
    time.sleep(5)
    decline_cookies()
    check_for_captchas(startpage)

    # Loop through the profiles
    for ID, row in df_source.iterrows():
        if 'ID' in col_list and col_list[0] != 'ID':
            ID = int(row['ID'])
        elif not 'nan' in str(ID):
            try:
                ID = int(ID)
                if ID < start_ID:  # If you want to skip some rows
                    continue
            except:
                ID = str(ID)

        company = extract_text(row[comp_header])
        if len(company) <= 4 and 'Name in Studie' in col_names:
            company = extract_text(row['Name in Studie'])
        link = str(row[platform])
        if len(link) < 10:
            empty_row = [ID, company, dt_str] + ['' for _ in range(13)]
            data.append(empty_row)
            continue

        try:
            scraped_data = scrapeProfile(link)
        except Exception as e:
            print(f'Error: {e}')
            scraped_data = ['', '', '', '', 'Fehler: ' + str(e)[:100], link, '', '', '', '', '', '', '']
        full_row = [ID, company, dt_str] + scraped_data
        data.append(full_row)
        print(full_row[:8] + full_row[11:])

    # DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'pagelikes', 'follower', 'following', 'last_post', 'url',
              'desc_link', 'description', 'videos', 'verified', 'private', 'account_created', 'username']
    df_profiles = pd.DataFrame(data, columns=header)

    # Export to Excel
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()
