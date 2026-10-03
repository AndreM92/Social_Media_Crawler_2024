
import os
import sys
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
startpage = 'https://x.com/'
platform = 'X'

folder_name = "SMP_Rüstungsunternehmen_2026"
file_name = "Auswahl_1_Rüstungsunternehmen_2026_20261001"
upper_datelimit = '2026-10-01'
file_path = r"C:\Users\andre\OneDrive\Desktop/" + folder_name
source_file = file_name + ".xlsx"

sys.path.insert(0, path_to_crawler_functions)
from crawler_functions import *

########################################################################################################################
# The crawler works without login (the login in the automated browser is blocked by X):
# - Without login X shows the profile header and the latest posts (about 5) in a separate page layout
# - The status id of a post contains the publishing time ((id >> 22) + 1288834974657 = milliseconds since 1970)

not_existent = ['Dieser Account existiert nicht', 'This account doesn’t exist', "This account doesn't exist"]
suspended = ['Account gesperrt', 'Account suspended']
not_available = ['Wir können dieses Konto nicht anzeigen', 'We can’t show this account']
protected = ['Diese Posts sind geschützt', 'These posts are protected']

# Decline the optional cookies
def decline_cookies():
    buttons = driver.find_elements('xpath', "//button[contains(., 'ablehnen') or contains(., 'Refuse non-essential')]")
    for b in buttons:
        try:
            b.click()
            time.sleep(1)
            return True
        except:
            pass
    return False

# Captchas and security checks have to be solved manually
def check_for_captchas(url):
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if 'account/access' in driver.current_url or soup.select_one('iframe[src*="captcha"], iframe[src*="arkose"]') \
            or 'Bestätige, dass du ein Mensch bist' in pagetext:
        driver.maximize_window()
        input('Press ENTER after solving the captcha')
        driver.get(url)
        time.sleep(4)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
    return soup, pagetext

# Clean profile url: https://x.com/<handle>
def clean_url(link):
    match = re.search(r'(?:x|twitter)\.com/(?:#!/)?@?([A-Za-z0-9_]{1,15})(?:[/?#]|$)', str(link))
    if not match or match.group(1).lower() in ['home', 'i', 'search', 'intent', 'share']:
        return None, None
    return f'https://x.com/{match.group(1)}', match.group(1)

def date_from_status_id(status_id):
    try:
        return datetime.fromtimestamp(((int(status_id) >> 22) + 1288834974657) / 1000)
    except:
        return None

def wait_for_profile():
    try:
        WebDriverWait(driver, 12).until(EC.presence_of_element_located(
            ('xpath', "//h1 | //*[contains(text(), 'existiert nicht')] | //*[contains(text(), 'gesperrt')]")))
    except:
        pass
    # The posts are loaded after the header
    try:
        WebDriverWait(driver, 6).until(EC.presence_of_element_located(('xpath', '//article')))
    except:
        pass
    time.sleep(1)

# Header of the profile: name, handle, description, location, website, joined, following and follower
def get_profile_header(soup, handle):
    header = {'p_name': '', 'handle': handle, 'desc': '', 'location': '', 'website': '', 'joined': '',
              'follower': '', 'following': '', 'verified': 0}
    if soup.title and '(@' in soup.title.get_text():
        header['handle'] = re.search(r'\(@([^)]+)\)', soup.title.get_text()).group(1)
    h1 = soup.find('h1')
    if not h1:
        return header
    header['p_name'] = extract_text(h1)
    # The verified badge is next to the name (not in the posts)
    name_box = h1.parent.parent if h1.parent else h1
    header['verified'] = 1 if name_box.find(attrs={'aria-label': re.compile('Verifizierter Account|Verified account')}) else 0
    # The header box contains the joined date and the follower links
    box = h1
    for _ in range(10):
        box = box.parent
        if not box or (box.find('a', href=re.compile(r'/following$')) and box.find('a', href=re.compile(r'/about$'))):
            break
    if not box:
        return header
    bio = box.find('div', attrs={'dir': 'auto'})
    if bio:
        header['desc'] = extract_text(bio.get_text(' '))
    joined_elem = box.find('a', href=re.compile(r'/about$'))
    if joined_elem:
        header['joined'] = extract_text(joined_elem).replace('Beigetreten', '').replace('Joined', '').strip()
        # Location and website are in the same row as the joined date
        for item in joined_elem.parent.parent.find_all('div', recursive=False):
            link = item.find('a', href=True)
            if link and link['href'].endswith('/about'):
                continue
            if link:
                header['website'] = extract_text(link)
            elif extract_text(item):
                header['location'] = extract_text(item)
    for a in box.find_all('a', href=True):
        number = a.find('span')
        if not number:
            continue
        if re.search(r'/(verified_followers|followers)$', a['href']):
            header['follower'] = extract_every_number(extract_text(number))
        elif a['href'].endswith('/following'):
            header['following'] = extract_every_number(extract_text(number))
    return header

# Latest visible own post (pinned posts included, the highest status id is the latest post)
def get_last_post(soup, handle):
    status_ids = []
    for article in soup.find_all('article'):
        for a in article.find_all('a', href=True):
            match = re.match(rf'^/{re.escape(handle)}/status/(\d+)$', a['href'], re.I)
            if match:
                status_ids.append(match.group(1))
    dates = [date_from_status_id(s) for s in status_ids]
    dates = [d for d in dates if d]
    if not dates:
        return None
    return max(dates).strftime('%d.%m.%Y')

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(link):
    url, handle = clean_url(link)
    if not url:
        return ['Kein gültiger X-Link', '', '', '', '', link, '', '', '', '', '', '']
    driver.get(url)
    wait_for_profile()
    soup, pagetext = check_for_captchas(url)
    new_url = driver.current_url
    if any(t in pagetext for t in not_existent):
        return ['Account existiert nicht', '', '', '', '', new_url, '', handle, '', '', '', '']
    if any(t in pagetext for t in suspended):
        return ['Account gesperrt', '', '', '', '', new_url, '', handle, '', '', '', '']
    if any(t in pagetext for t in not_available):
        return ['Account nicht verfügbar (privat, gelöscht oder nur in der App)', '', '', '', '', new_url, '', handle,
                '', '', '', '']

    header = get_profile_header(soup, handle)
    if not header['p_name']:
        # Reload once, if the page was not loaded completely
        driver.get(url)
        wait_for_profile()
        soup, pagetext = check_for_captchas(url)
        header = get_profile_header(soup, handle)

    if any(t in pagetext for t in protected):
        last_post = 'Geschützter Account'
    else:
        last_post = get_last_post(soup, header['handle'] or handle) or 'Keine Beiträge sichtbar'

    # Total number of posts in the top bar (e.g. "Rheinmetall 4.512 posts")
    posts = ''
    posts_match = re.search(r'([\d.,]+\s*(?:K|M|Mio\.|Tsd\.)?)\s+(?:posts|Posts)\b', pagetext[:800])
    if posts_match:
        posts = extract_every_number(posts_match.group(1))

    return [header['p_name'], header['follower'], header['following'], header['joined'], last_post, new_url,
            header['desc'], header['handle'], header['location'], header['website'], header['verified'], posts]
########################################################################################################################

# Profile crawler
if __name__ == '__main__':
    # Settings for profile scraping
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)
    if 'X' in col_list:
        platform = 'X'
    elif 'Twitter' in col_list:
        platform = 'Twitter'
    else:
        print('No platform found')
        exit()

    # Start crawling (without login)
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    driver.get(startpage)
    time.sleep(4)
    decline_cookies()

    # Iterating over the companies
    for n, row in df_source.iterrows():
        if 'ID' in col_list and col_list[0] != 'ID':
            ID = int(row['ID'])
        elif not 'nan' in str(n):
            ID = int(n)
        if ID <= -1:                   # If you want to skip some rows
            continue

        company = extract_text(row[comp_header])
        url = str(row[platform])
        if len(url) < 10:
            empty_row = [ID, company, dt_str] + ['' for _ in range(12)]
            data.append(empty_row)
            continue
        try:
            datarow = scrapeProfile(url)
        except Exception as e:
            print(f'Error: {e}')
            datarow = ['Fehler: ' + str(e)[:100], '', '', '', '', url, '', '', '', '', '', '']
        full_row = [ID, company, dt_str] + datarow
        data.append(full_row)
        print(full_row[:8] + full_row[10:])
        time.sleep(random.uniform(2, 4))

    # DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'follower', 'following', 'joined', 'last_post', 'url',
              'description', 'handle', 'location', 'website', 'verified', 'posts']
    df_profiles = pd.DataFrame(data, columns=header)

    # Export to Excel
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()
