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
# Settings
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
source_file = "Liste_Nahrungsergänzungsmittel_2024_Auswahl.xlsx"
branch_keywords = ['nutrition', 'vitamin', 'mineral', 'protein', 'supplement', 'diet', 'health', 'ernährung',
                   'ergänzung', 'gesundheit', 'nährstoff', 'fitness', 'sport', 'leistung']
startpage = 'https://www.facebook.com/'
platform = 'Facebook'
dt_str_now = None
########################################################################################################################

# Facebook Login function
def login(useremail, password, driver, pyautogui):
    try:
        WebDriverWait(driver,5).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div[1]/div[1]/div/div/div/div[1]/div/img')))
    except:
        time.sleep(3)
    nameslot = driver.find_element('xpath','/html/body/div[1]/div[1]/div[1]/div/div/div/div[2]/div/div[1]/form/div[1]/div[1]/input')
    nameslot.clear()
    for char in useremail:
        time.sleep(0.1)
        nameslot.send_keys(char)
    pwslot = driver.find_element('xpath','/html/body/div[1]/div[1]/div[1]/div/div/div/div[2]/div/div[1]/form/div[1]/div[2]/div/input')
    pwslot.clear()
    for char in password:
        time.sleep(0.1)
        pwslot.send_keys(char)
    time.sleep(1)
    driver.find_element('xpath','/html/body/div[1]/div[1]/div[1]/div/div/div/div[2]/div/div[1]/form/div[2]/button').click()
    time.sleep(3)
    cookiebuttons = driver.find_elements('xpath', "//*[contains(text(), 'Blockieren') or contains(text(), 'blockieren')]")
    if len(cookiebuttons) >= 1:
        for c in cookiebuttons:
            try:
                c.click()
            except:
                time.sleep(1)
                pyautogui.moveTo(459, 203)
                pyautogui.click()
                time.sleep(1)
                pyautogui.moveTo(460, 205)
                pyautogui.click()

def get_p_name(driver, comp_keywords, p_name = ''):
    headers = [h.text for h in driver.find_elements(By.XPATH, '//h1') if h.text]
    if 'Suchergebnisse' in headers:
        return None
    if len(headers) >= 1:
        p_list = [h for h in headers if any(part in h.lower() for part in comp_keywords)]
        if len(p_list) >= 1:
            p_name = p_list[0].strip()
        else:
            p_list = [h for h in headers if len(h) >= 3 and (not 'neu' in h.lower() and not 'benachrichtigung' in h.lower())]
            if len(p_list) >= 1:
                p_name = p_list[0].strip()
    if p_name == '':
        headers2 = [h.text for h in driver.find_elements(By.XPATH, '//h2') if h.text]
        if len(headers2) >= 1:
            p_list = [h for h in headers if any(part in h.lower() for part in comp_keywords)]
            if len(p_list) >= 1:
                p_name = p_list[0].strip()
            else:
                p_list = [h for h in headers if
                          len(h) >= 3 and (not 'neu' in h.lower() and not 'benachrichtigung' in h.lower())]
                if len(p_list) >= 1:
                    p_name = p_list[0].strip()
    if 'Bestätigtes' in str(p_name):
        p_name = p_name.replace('Bestätigtes Konto', '').strip()
    return p_name


def get_last_postdate(p_name):
    last_post = ''
    scr_text = get_text_from_screenshot(driver, p_name)
    list_of_dates = getDates(scr_text)
    list_of_datetimes = []
    for d in list_of_dates:
        try:
            dt_elem = dateFormat(d)
            list_of_datetimes.append(dt_elem)
        except:
            print('Datetime Error')
            pass
    if len(list_of_datetimes) == 0:
        conditions = ['gestern', 'stund', 'minut', 'tage']
        soup = BeautifulSoup(driver.page_source,'lxml')
        text_list = [str(t.text) for t in soup.find_all('text')]
        datelist = [e for e in text_list if (e[0].isdigit() == True or any(c in e.lower() for c in conditions))]
        if len(datelist) >= 1:
            list_of_datetimes = [dateFormat(d) for d in datelist]
    if len(list_of_datetimes) >= 1:
        list_of_datetimes.sort(reverse=True)
        last_post = list_of_datetimes[0].strftime('%d.%m.%Y')
    return last_post


def scrapeProfile(url):
    p_name, pagelikes, follower, last_post, desc1, desc2 = ['' for i in range(6)]
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if ('gelöscht' in pagetext and 'nicht verfügbar' in pagetext) or len(pagetext) <= 200:
        p_name = 'page not available'
        return [p_name, pagelikes, follower, last_post, desc1, desc2]
    p_name = get_p_name(driver, comp_keywords)
    if len(str(p_name)) <= 2:
        return [p_name, pagelikes, follower, last_post, desc1, desc2]

    upper_posts = soup.find_all('div', class_='x1c4vz4f x2lah0s xeuugli x1bhewko xq8finb xnqqybz')
    if len(upper_posts) >= 1:
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(1)

    last_post = get_last_postdate(p_name)
    rawdesc = driver.find_element(By.CLASS_NAME, 'x1yztbdb')
    desc2 = extract_text(rawdesc).replace('Steckbrief ', '')
    stats_elem = soup.find('div',class_='x9f619 x1n2onr6 x1ja2u2z x78zum5 xdt5ytf x2lah0s x193iq5w x1cy8zhl xyamay9')
    stats_text = extract_text(stats_elem)
    if stats_text:
        stats_list = str(stats_text).split('•')
        for e in stats_list:
            if "gefällt" in e.lower():
                pagelikes = extract_every_number(e)
            elif 'follower' in e.lower():
                follower = extract_every_number(e)
    else:
        print('Other profile type')
        elems = [e for e in soup.find_all('div', class_='x1e56ztr x1xmf6yo')]
        clean_elems = [extract_text(e) for e in elems]
        if len(str(p_name)) <= 2:
            p_name = clean_elems[0].replace(' Bestätigtes Konto','')
        desc1 = ' '.join(clean_elems[1:]).strip()
        stats = soup.find('div', class_='x1jx94hy x78zum5 xdt5ytf')
        if len(str(stats)) <= 3:
            stats = soup.find('div', class_="x78zum5 xdt5ytf x5yr21d")
        if stats:
            info = [i.text for i in stats if len(i.text) > 1 and 'datenrichtlinien' not in i.text.lower()]
            for pos, e in enumerate(info):
                if "gefällt" in e.lower():
                    pagelikes = extract_every_number(e)
                elif 'follower' in e.lower():
                    follower = extract_every_number(e)
            desc2 = ' '.join(info).replace('Steckbrief', '').strip()
    if len(desc2) <= 5:
        desc2 = extract_text(pagetext)
    new_url = driver.current_url
    return [p_name, pagelikes, follower, last_post, new_url, desc1, desc2]
########################################################################################################################

# Profile Crawler
if __name__ == '__main__':
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    import credentials_file as cred
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)

    # Open the browser, go to the startpage and login
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(cred.email_fb, cred.password_fb, driver, pyautogui)

    # Loop through the companies
    count = 0 #If id's aren't ordered
    for id, row in df_source.iterrows():
        count += 1
        if count <= 0:
            continue
        company = extract_text(row[comp_header])
        comp_keywords = get_company_keywords(company, row, col_list)
        if name_header:
            name = extract_text(row[name_header])
            comp_keywords += get_company_keywords(name, row, col_list)
            company = name
        url = str(row[platform])
        if len(url) < 10:
            data.append([id, company, dt_str] + ['' for _ in range(7)])
            continue

        scraped_data = scrapeProfile(url)
        full_row = [id, company, dt_str] + scraped_data
        data.append(full_row)
        print(count, full_row[:-2])

    # DataFrame
    header = ['ID','company','date','profile_name','likes','follower','last_post','url','desc_alt','description']
    df_profiles = pd.DataFrame(data,columns=header)
    df_profiles.set_index('ID')

    # Export to Excel
#    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_Facebook_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    # If you want to add more sheets
#    with pd.ExcelWriter(recent_filename) as writer:
#        dfProfiles.to_excel(writer, sheet_name='Profildaten')

    driver.quit()

########################################################################################################################
# Post crawler functions

def inspect_page(row, lower_dt):
    id = row['ID']
    url = str(row['url'])
    p_name = str(row['profile_name'])
    driver.get(url)
    time.sleep(1)
    driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
    time.sleep(2)
    current_dt, datelist = get_oldest_date(driver, p_name)
    if not current_dt:
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
        time.sleep(2)
        current_dt, datelist = get_oldest_date(driver, p_name)
    if not current_dt:
        print([id, p_name, url, 'no posts'])
        return None, None, None, None
    if current_dt > lower_dt:
        datelist = scroll_down(lower_dt, driver, p_name)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    posts = soup.find_all('div', {'role': 'article', 'class': 'x1a2a7pz',
                                  'aria-label': lambda x: x is None or 'Kommentar' not in x})
    if len(posts) == 0:
        posts = soup.find_all('div', class_='x1n2onr6 x1ja2u2z')
    return id, p_name, posts, datelist


def get_oldest_date(driver, p_name):
    conditions = ['gestern', 'stund', 'minut', 'tage']
    soup = BeautifulSoup(driver.page_source, 'lxml')
    text_list = [str(t.text) for t in soup.find_all('text')]
    datelist = [str(e) for e in text_list if e[0].isdigit()]
    if len(datelist) == 0:
        scr_text = get_text_from_screenshot(driver, p_name)
        if not 'Reels' in scr_text:
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)
            scr_text = get_text_from_screenshot(driver, p_name)
            if not 'Reels' in scr_text:
                return None, datelist
        date_raw = scr_text.split('Reels', 1)[1].split('@', 1)[0].replace('-', '').strip()
        datelist = [date_raw]
    list_of_datetimes = [dateFormat(d) for d in datelist]
    list_of_datetimes.sort(reverse=True)
    current_dt = list_of_datetimes[-1]
    datelist = [d.strftime('%d.%m.%Y') for d in list_of_datetimes]
    return current_dt, datelist


def scroll_down(lower_dt, driver, p_name):
    # Faster start:
    for i in range(10):
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
        time.sleep(1)
    time.sleep(3)
    current_dt, datelist = get_oldest_date(driver, p_name)
    date_diff = current_dt - lower_dt
    rounds = date_diff.days // 2
    if rounds > 200:
        return datelist
    height2 = False
    for i in range(rounds):
        height1 = height2
        height2 = driver.execute_script("return document.documentElement.scrollHeight")
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
        incr = 1 + round(i/100)
        time.sleep(incr)
        height3 = driver.execute_script("return document.documentElement.scrollHeight")
        if height1 == height3:
            break
        current_dt, datelist = get_oldest_date(driver, p_name)
        if current_dt < lower_dt:
            break
    return datelist

#rawtext = get_visible_text(Comment,posts[0])
def scrape_reel(id_p, datelist, rawtext, p):
    post_date, likes, comments, shares, link = ['' for _ in range(5)]
    p_text = rawtext.replace('Facebook', '').strip()
    reactions = p_text.rsplit('·', 1)[-1].strip().replace('Senden!','').strip()
    if '.com' in reactions:
        reactions = reactions.split('.com')[0].rsplit(' ', 1)[0]
    react_la = [str(e).strip() for e in reactions.split(' ') if 5 >= len(str(e).strip()) >= 1]
    react_l = [extract_every_number(e) for e in react_la if str(e)[0].isdigit()]
    if len(react_l) >= 3:
        react_l = react_l[:3]
        likes, comments, shares = react_l
    elif len(react_l) == 2:
        likes, comments = react_l
    elif len(react_l) == 1:
        likes = react_l[0]
    reel_date = p_text.rsplit('·', 2)[-2].strip()
    if not reel_date or not reel_date[0].isdigit():
        reel_date = p_text[p_text.find('Reels') + 9:].split('·')[0].strip()
    if reel_date[0].isdigit():
        post_dt = dateFormat(reel_date)
        post_date = post_dt.strftime("%d.%m.%Y")
        if post_dt >= datetime.now():
            day = str(post_dt.day).zfill(2)
            month = str(post_dt.month).zfill(2)
            year = post_dt.year - 1
            post_date = f'{day}.{month}.{year}'
            post_dt = datetime.strptime(post_date,"%d.%m.%Y")
    if not post_date or not post_dt:
        post_date = datetime.now().strftime("%d.%m.%Y")
    datelist.insert(id_p, post_date)
    p_text = p_text.rsplit('·', 1)[0].strip()
    r_links = [l['href'] for l in p.find_all('a', href=True) if 'reel' in l['href']]
    if len(r_links) >= 1:
        link = "https://www.facebook.com" + r_links[0].split('?', 1)[0]
    reel_data = [datelist, post_date, likes, comments, shares, link, p_text]
    return reel_data

# Scrape the posts
def get_p_link(p):
    links = [str(l['href']) for l in p.find_all('a', href=True)]
    f_links = [l for l in links if 'post' in l or '/p/' in l]
    if len(f_links) == 0:
        f_links = [l for l in links if '/video' in l]
    if len(f_links) == 0:
        f_links = [l for l in links if '/photo' in l]
    if len(f_links) == 0:
        return None
    link = f_links[0].split('&__')[0].split('?__')[0]
    return link

def find_p_elements(p, rawtext):
    not_imagelinks = ['profile', 'hashtag', 'emoji']
    imagelinks_all = [p['src'] for p in p.find_all('img', src=True)]
    imagelinks = [p for p in imagelinks_all if not any(e in p for e in not_imagelinks)]
    if 'livestream' in rawtext or p.find('video', src=True) or p.find('div', {'aria-label': 'Play'}):
        image, video = 0, 1
    elif len(imagelinks) >= 1 or 'Bild' in str(p):
        image, video = 1, 0
    else:
        image, video = 0, 0
    return image, video

def split_p_text(rawtext):
    p_text = rawtext
    if '·' in p_text:
        p_text = p_text.split('·', 1)[1].strip()
    if '·' in p_text:
        p_text = p_text.split('·', 1)[1].strip()
    p_text1 = p_text
    if 'Teilen' in p_text:
        p_text = p_text.split('Teilen')[0].strip()
    else:
        if 'Kommentieren' in p_text:
            p_text = p_text.split('Kommentieren')[0].strip()
    forbidden_chars = ['+', '-', '*', '=']
    if any(c in p_text[0] for c in forbidden_chars):
        p_text = '$$' + p_text
    comments = False
    if len(p_text1) - len(p_text) >= 120:
        comments = True
    if 'Alle Reaktionen:' in p_text:
        reactions = p_text.split('Alle Reaktionen:')[1].strip()
    elif 'All reactions' in p_text:
        reactions = p_text.split('All reactions:')[1].strip()
    else:
        reactions = None
    return p_text1, p_text, reactions, comments

def get_reactions(p_text1, reactions, comments):
    if not reactions:
        return '', '', ''
    react_ls = [str(e).strip() for e in reactions.split(' ') if len(str(e).strip()) >= 1]
    react_numbers = [extract_every_number(e) for e in react_ls if str(e)[0].isdigit()]
    if len(react_numbers) == 0:
        return 0, 0, 0
    if len(react_numbers) >= 2:
        react_numbers.pop(1)
    if len(react_numbers) == 1:
        if comments:
            return [0, react_numbers[0], 0]
        elif 'Mal' in p_text1 and ' geteilt' in p_text1:
            return [0, 0, react_numbers[0]]
        return [react_numbers[0], 0, 0]
    elif len(react_numbers) == 2:
        if comments:
            if 'Mal' in p_text1 and ' geteilt' in p_text1:
                return [0, react_numbers[0], react_numbers[1]]
            return [react_numbers[0], react_numbers[1], 0]
        return [react_numbers[0], 0, react_numbers[1]]
    return react_numbers[:3]


def post_scraper(p_name, posts, datelist, upper_dt, lower_dt):
    data_per_company = []
    count_p = 0
    reels = False
    for p in posts[:2]:
        if 'Reels' in str(get_visible_text(Comment, p)):
            reels = True
    if len(posts) > (len(datelist) + 1) and not reels:
        datelist = [datetime.now().strftime('%d.%m.%Y')] + datelist
    for id_p, p in enumerate(posts):
        post_date = ''
        rawtext = str(get_visible_text(Comment, p))
        if len(rawtext) <= 100 or not p_name[:4].lower() in rawtext.lower():
            continue
        if 'Reels' in rawtext:
            p_type = 'reel'
            video, image = 1, 0
            datelist, post_date, likes, comments, shares, link, p_text = scrape_reel(id_p, datelist, rawtext, p)
        else:
            p_type = 'post'
            link = get_p_link(p)
            image, video = find_p_elements(p, rawtext)
            p_text1, p_text, reactions, comments = split_p_text(rawtext)
            likes, comments, shares = get_reactions(p_text1, reactions, comments)
        if id_p >= len(datelist) and not post_date:
            break
        if not post_date:
            post_date = datelist[id_p]
        try:
            post_dt = datetime.strptime(post_date, "%d.%m.%Y")
            if post_dt >= upper_dt:
                continue
            if post_dt < lower_dt and count_p > 1:
                break
        except:
            pass
        count_p += 1
        scraped_data = [post_date, likes, comments, shares, image, video, p_type, link, p_text]
        full_row = [id, p_name, count_p, dt_str] + scraped_data
        data_per_company.append(full_row)
    return data_per_company



def check_conditions(id, row, start_at=0):
    if id < start_at:      # If you want to skip some rows
        return False
    url = str(row['url'])
    last_posts = str(row['last_post'])
    if len(url) < 10 or len(last_posts) <= 4 or 'Keine Beiträge' in last_posts:
        print([id, url, 'no posts'])
        return False
    try:
        last_datestr = extract_text(last_post)
        last_dt = datetime.strptime(last_datestr, "%d.%m.%Y")
        if (lower_dt + timedelta(days=31)) < last_dt:
            return False
    finally:
        return True

def restart_browser(driver, webdriver, Service, chromedriver_path):
    driver.quit()
    time.sleep(3)
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(cred.username_fb, cred.password_fb, driver, pyautogui)
    time.sleep(3)
    return driver
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    import credentials_file as cred
    os.chdir(file_path)
    file ='Profile_Facebook_2024'
    df_source, dt, dt_str, upper_dt, lower_dt = post_crawler_settings(file, platform, dt_str_now)

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(cred.username_fb, cred.password_fb, driver, pyautogui)

    # Iterate over the companies
    for count, row in df_source.iterrows():
        crawl = check_conditions(count,row,start_at=0)
        if not crawl:
            continue

        # Restart the browser after 5 companies
        if count % 5 == 0:
            driver = restart_browser(driver, webdriver, Service, chromedriver_path)
        # Troubleshooting various issues like network errors
        try:
            id, p_name, posts, datelist = inspect_page(row, lower_dt)
        except:
            driver = restart_browser(driver, webdriver, Service, chromedriver_path)
            id, p_name, posts, datelist = inspect_page(row, lower_dt)
        if not posts or len(posts):
            continue

        # Post_scraper scrapes the data of every post
        data_per_company = post_scraper(p_name, posts, datelist, upper_dt, lower_dt)
        all_data += data_per_company

        # Create a DataFrame with all posts
        header1 = ['ID_A', 'profile_name', 'ID_P', 'Erhebung', 'Datum']
        header2 = ['Likes', 'Kommentare', 'Shares', 'Bild', 'Video', 'Beitragsart', 'Link', 'Content']
        dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

        # Export dfPosts to Excel or CSV (with the current time)
        dt_str_now2 = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_Facebook_' + dt_str_now2
        # In case there are issues with specific characters
        try:
            dfPosts.to_excel(file_name + '.xlsx')
        except:
            dfPosts.to_csv(file_name + '.csv', index=False)

    driver.quit()
########################################################################################################################
# Find all posts with the driver
#posts = driver.find_elements(By.XPATH, '//div[@role="article" and not(contains(@aria-label, "Kommentar"))]')
# Pyautogui Investigation process
'''
time.sleep(4)
x,y = pyautogui.position()
print(str(x)+ "," + str(y))
'''