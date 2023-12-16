from crawler_functions import *
import credentials as cred

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
newpath = r"C:\Users\andre\OneDrive\Desktop\SSM_Energieanbieter"
os.chdir(newpath)
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
startpage = 'https://www.instagram.com/'
network = 'Instagram'
########################################################################################################################

def remove_insta_cookies2():
    cookiebuttons = driver.find_elements('xpath', "//*[contains(text(), 'Jetzt nicht') or contains(text(), 'jetzt nicht')]")
    if len(cookiebuttons) >= 1:
        for c in cookiebuttons:
            try:
                c.click()
            except:
                pass

# Login function
def login(username, password):
    WebDriverWait(driver,5).until(EC.presence_of_element_located((By.XPATH,'//*[@id="loginForm"]/div/div[1]/div/label/input')))
    try:
        nameslot = driver.find_element(By.CSS_SELECTOR,'input[aria-label*="Benutzername"]')
    except:
        nameslot = driver.find_element('xpath', '//*[@id="loginForm"]/div/div[1]/div/label/input')
    pwslot = driver.find_element(By.CSS_SELECTOR,'input[aria-label*="Passwort"]')
    nameslot.clear()
    # Typing char for char to simulate a human like behavior
    # classic and global version:
    # nameslot.send_keys(cred.username_insta)
    for char in username:
        nameslot.send_keys(char)
        time.sleep(.1)
    pwslot.clear()
    for char in password:
        pwslot.send_keys(char)
        time.sleep(.1)
    driver.find_element('xpath', "//*[text()='Anmelden']").click()
    for _ in range(5):
        time.sleep(2)
        remove_insta_cookies2()

# This function scrapes the details of every profile
def scrapeProfile(link, comp_keywords):
    driver.get(link)
    p_name, total_posts, follower, last_post, new_url, desc = ['' for _ in range(6)]
    time.sleep(4)
    new_url = driver.current_url
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    full_desc = get_visible_text(Comment, soup.find('header'))
    if len(full_desc) <= 100:
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
        full_desc = get_visible_text(Comment, soup.find('header'))
    if not network.lower() + '.com' in driver.current_url:
        p_name = 'Wrong page'
        return [p_name, total_posts, follower, last_post, new_url, desc]
    broken_profile = ['nicht verfügbar', 'Eingeschränktes Profil', 'Konto ist privat', 'Seite wurde entfernt']
    for m in broken_profile:
        if m in pagetext:
            p_name = m
            return [p_name, total_posts, follower, last_post, new_url, desc]

    headers = [h.text for h in driver.find_elements(By.XPATH, '//h2') if h.text]
    if len(headers) == 1:
        p_name = headers[0]
    elif len(headers) > 1:
        p_name = [h for h in headers if any(part in h.lower() for part in comp_keywords)]
        if p_name == '':
            p_list = [h for h in headers if len(h) >= 3 and (not 'neu' in h.lower() and not 'benachrichtigung' in h.lower())]
            if len(p_list) >= 1:
                p_name = p_list[0]
    p_stats = soup.find('ul',class_='x78zum5 x1q0g3np xieb3on')
    if p_stats:
        stats_list = p_stats.find_all('li')
        if stats_list:
            for e in stats_list:
                i = extract_text(e)
                if 'Beiträge' in i:
                    total_posts = extract_number(i.split(' ')[0])
                elif 'Follower' in i:
                    follower = extract_number(i.split(' ')[0])
        else:
            total_posts = full_desc
    header = soup.find('section')
    header_text = extract_text(header)
    if 'Gefolgt' in header_text and 'Beiträge' in header_text:
        desc = header_text.split('Gefolgt',1)[1].rsplit('Beiträge')[0].strip()
    else:
        desc = header_text
    if len(str(desc)) <= 4:
        desc = pagetext
    if 'Noch keine Beiträge' in pagetext:
        return [p_name, dt_str, total_posts, follower, last_post, new_url, desc]

    p_links = ['https://www.instagram.com' + str(l['href']) for l in soup.find_all('a',href=True) if '/p/' in str(l['href'])]
    if len(p_links) >= 1:
        driver.get(p_links[0])
        time.sleep(2)
        soup_post = BeautifulSoup(driver.page_source,'lxml')
        last_post = soup_post.find('time',class_='_aaqe')
        if last_post:
            last_post = last_post['datetime'].split('T')[0]
            last_dt = datetime.strptime(last_post,'%Y-%m-%d')
            last_post = last_dt.strftime('%d.%m.%Y')

    return [p_name, total_posts, follower, last_post, new_url, desc]

########################################################################################################################
# Further Settings
source_file = "Energieanbieter_Auswahl.xlsx"
df_source = pd.read_excel(source_file)
df_source.set_index('ID',inplace=True)
col_list = list(df_source.columns)
if 'Anbieter' in col_list:
    comph_header = 'Anbieter'
elif 'Firma' in col_list:
    comp_header = 'Firma'
comph2 = 'Name in Studie'
dt = datetime.now()
dt_str = dt.strftime("%d.%m.%Y")
data = []

# start crawling
driver = start_browser(webdriver, Service, chromedriver_path)
go_to_page(driver, startpage)
login(cred.username_insta, cred.password_insta)

# Loop
count = 0
for id, row in df_source.iterrows():
    count += 1
    url = str(row[network])
    company = row[comp_header]
    if len(url) < 10:
        empty_row = [id, company, dt_str] + ['' for _ in range(6)]
        data.append(empty_row)
        continue
    comp_keywords = get_company_keywords(company, row, col_list)
    comp_keywords += [row[comph2]]
    scraped_data = scrapeProfile(url, comp_keywords)
    full_row = [id, company, dt_str] + scraped_data
    data.append(full_row)
    # To look at the results immediately
    print(count,full_row[:-1])


# DataFrame
header = ['ID','Anbieter','Erh.Datum','Profilname','likes','follower','last post','url','description']
dfProfiles = pd.DataFrame(data,columns=header)
dfProfiles.set_index('ID')

# Export to Excel
filename_profiles = 'Profile_' + network + '.xlsx'
with pd.ExcelWriter(filename_profiles) as writer:
    dfProfiles.to_excel(writer, sheet_name='Profildaten')

########################################################################################################################
# post_crawler functions

def clickOnFirst(startlink):
    try:
        driver.find_element(By.CLASS_NAME, '_aagw').click()
        time.sleep(2)
    except:
        try:
            time.sleep(2)
            driver.find_element(By.CLASS_NAME, '_aagw').click()
            time.sleep(1)
        except:
            pyautogui.moveTo(650, 900)
            pyautogui.click()
            time.sleep(2)
    post_url = driver.current_url
    if post_url == startlink:
        link_elems = driver.find_elements(By.CSS_SELECTOR, 'a[href]')
        if len(link_elems) >= 1:
            links = [a.get_attribute('href') for a in link_elems]
            p_links = ['https://www.instagram.com' + str(l) for l in links if '/p/' in str(l) and not 'http' in str(l)]
            if len(p_links) == 0:
                return None
            first_post = p_links[0]
            try:
                driver.get(first_post)
                time.sleep(2)
            except:
                pass
    post_url = driver.current_url
    if post_url == startlink or not 'instagram.com' in post_url:
        post_url == None
    return post_url


def nextPost(startlink):
    try:
        driver.find_element(By.CSS_SELECTOR, 'svg[aria-label="Weiter"]').click()
        time.sleep(1)
    except:
        pyautogui.moveTo(1865, 575)
        pyautogui.click()
        time.sleep(3)
    if startlink == driver.current_url:
        try:
            driver.find_element(By.CSS_SELECTOR, 'svg[aria-label="Weiter"]').click()
            time.sleep(1)
        except:
            pyautogui.moveTo(1865, 575)
            pyautogui.click()
            time.sleep(3)
    if startlink == driver.current_url:
        try:
            driver.find_element(By.CSS_SELECTOR, 'svg[aria-label="Weiter"]').click()
            time.sleep(1)
        except:
            pyautogui.moveTo(1865, 575)
            pyautogui.click()
            time.sleep(3)
    post_url = driver.current_url
    if post_url == startlink or not 'instagram.com' in post_url:
        post_url == None
    return post_url


def get_commentnumber(soup, post_text):
    orig_page = driver.current_url
    if 'keine kommentare' in post_text.lower():
        return 0
    comments = len(soup.find_all('ul', class_='_a9ym'))
    c_section = 'x78zum5 xdt5ytf x1iyjqo2'
    if comments == 0:
        comments_elem = soup.find('div', class_=c_section)
        if comments_elem:
            comments = len(comments_elem)
    if comments <= 5:
        return comments
    pyautogui.moveTo(1475, 330)
    pyautogui.scroll(-1500)
    pyautogui.moveTo(1385,755)
    # Clicking led to many errors so I will scrape the correct higher comment counts later (with the post links)
#    pyautogui.click()
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source,'lxml')
    comments = soup.find('div',class_= c_section)
    if comments:
        if len(comments) >= 1:
            comments = len(comments) - 1
    else:
        comments = len(soup.find_all('ul', class_='_a9ym'))
    if comments <= 14:
        return comments
    for i in range(50):
        old_comments = comments
        pyautogui.moveTo(1475, 330)
        pyautogui.scroll(-1500)
        pyautogui.moveTo(1385, 755)
 #       pyautogui.click()
        time.sleep(1)
        if i >= 20:
            time.sleep(1)
        if i >= 40:
            time.sleep(1)
        if orig_page != driver.current_url:
            driver.get(orig_page)
            return comments
        c_soup = BeautifulSoup(driver.page_source,'lxml')
        comments = len(c_soup.find_all('ul', class_='_a9ym'))
        if comments <= 15:
            new_comments = c_soup.find('div',class_= c_section)
            if new_comments:
                if len(new_comments) > comments:
                    comments = len(new_comments) - 1
        if old_comments == comments:
            break
    return comments


def scrape_post(post_url, p_name, upper_dt, lower_dt):
    post_date, likes, comments, image, video, calls, content = ['' for _ in range(7)]
    post_dt = None
    soup = BeautifulSoup(driver.page_source, 'lxml')
    post_text = get_visible_text(Comment, soup)
    date_elem = soup.find('time', class_='_aaqe')
    if date_elem:
        post_dt_str = date_elem['datetime'].split('T')[0]
        post_dt = datetime.strptime(post_dt_str, '%Y-%m-%d')
        if post_dt >= upper_dt:
            return post_dt, None
        elif post_dt <= lower_dt or not p_name in post_text:
            return None, None
        post_date = post_dt.strftime('%d.%m.%Y')
    content_elem = soup.find('div', class_='_a9zs')
    content = extract_text(content_elem)
    if len(str(content)) <= 4:
        if len(post_text) >= 1200:
            content = post_text
    if soup.find('video'):
        video = 1
        image = 0
    else:
        imagelinks = [l['src'] for l in soup.find('div', class_='_aagv').find_all('img', src=True)]
        if len(imagelinks) >= 1:
            video = 0
            image = 1
    react_text = extract_text(soup.find('section', class_='_ae5m _ae5n _ae5o'))
    if not react_text:
        react_text = extract_text(soup.find('section', class_='x12nagc'))
    if not react_text:
        pt_l = post_text.split()
        for pos, e in enumerate(pt_l):
            if e == 'Gefällt':
                react_text = pt_l[pos] + ' ' + pt_l[pos+1] + ' ' + pt_l[pos+2]
                break
    if react_text:
        if 'Aufrufe' in react_text:
            video = 1
            image = 0
            calls = extract_number(react_text)
            show_likes_button = driver.find_element(By.CLASS_NAME, '_aauw')
            if show_likes_button:
                show_likes_button.click()
            # Two clicks to get on the next post
            likes_elem = driver.find_element(By.CLASS_NAME, '_aauu')
            likes = extract_number(extract_text(likes_elem))
        elif 'Gefällt' in react_text or 'likes' in react_text.lower():
            likes = extract_number(react_text)
        if likes == '' and 'weiteren Personen' in post_text:
            # This alternative like display will be scraped with the alternative comment display later
            likelink = ['https://www.instagram.com/' + l['href'] for l in soup.find_all('a', href=True) if
                        'liked' in l['href']]
            if len(likelink) >= 1:
                likes = likelink[0]
    if not likes or str(likes) == '':
        likes = int(0)
    comments = get_commentnumber(soup, post_text)

    scraped_data = [post_date, likes, comments, image, video, calls, post_url, content]
    return post_dt, scraped_data

########################################################################################################################
# Settings for the post crawler
source_file = "Profildaten_Energieanbieter_1.xlsx"
df_source = pd.read_excel(source_file, sheet_name=network)
df_source.set_index('ID',inplace=True)
dt = datetime.now()
dt_str = dt.strftime("%d.%m.%Y")
lower_dt = datetime.strptime('2022-10-31','%Y-%m-%d')
upper_dt = datetime.strptime('2023-11-01','%Y-%m-%d')

all_data = []

# start crawling the posts
driver = start_browser(webdriver, Service, chromedriver_path)
go_to_page(driver, startpage)
login(cred.username_insta, cred.password_insta)

# Loop
for id, row in df_source.iterrows():
    data_per_company = []
    url = str(row['url'])
    company = row['Anbieter']
    p_name = row['Profilname']
    posts = str(row['last post'])
    if len(url) < 10 or len(posts) <= 4 or 'Keine Beiträge' in posts:
        print([id, p_name, '', dt_str] + [url])
        continue
    driver.get(url)
    time.sleep(4)
    post_url = clickOnFirst(driver.current_url)
    if not post_url:
        print([id, p_name, '', dt_str] + [post_url])
        continue
    p_num = 0
    while True:
        post_dt, scraped_data = scrape_post(post_url, p_name, upper_dt, lower_dt)
        if not post_dt:
            break
        if post_dt >= upper_dt:
            post_url = nextPost(post_url)
            if not post_url:
                break
            continue
        p_num += 1
        full_row = [id, p_name, p_num, dt_str] + scraped_data
        data_per_company.append(full_row)
        if p_num == 1000:
            break
        post_url = nextPost(driver.current_url)
        if not post_url:
#            print([id, p_name, p_num, dt_str] + ['No more Posts'])
            break
    all_data += data_per_company


# Create a DataFrame with all posts
header1 = ['ID_A', 'Profilname', 'ID_P', 'Datum_Erhebung', 'Datum_Beitrag']
header2 = ['Likes', 'Kommentare', 'Bild', 'Video', 'Aufrufe', 'Link', 'Content']
dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

# Export dfPosts to Excel (with the current time)
dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
file_name = 'Beiträge_' + network + '_' + dt_str_now + '.xlsx'
dfPosts.to_excel(file_name)

########################################################################################################################
# Adding the like count and comment count for exceptional posts
fill_data = []
source_file = 'Beiträge_Instagram2023-11-23_aktuell.xlsx'
df_fillc = pd.read_excel(source_file)

for id, row in df_fillc.iterrows():
    comments = row['Kommentare']
    likes = row['Likes']
    if not comments == 15 and not 'http' in str(likes):
        fill_data.append([id,row['ID_A'], likes, comments])
        continue
    if 'http' in str(likes):
        driver.get(str(likes))
        time.sleep(1)
        likes = len(driver.find_elements('xpath', "//*[text()='Folgen']"))
    if comments == 15:
        driver.get(row['Link'])
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        post_text = get_visible_text(Comment, soup)
        comments = get_commentnumber(soup, post_text)
    fill_data.append([id, row['ID_A'], likes, comments])

df_filled = pd.DataFrame(fill_data, columns=['id','ID_A', 'Likes', 'Kommentare'])
df_filled.to_excel('filled_Likes_comments.xlsx')
print('Done')
driver.quit()