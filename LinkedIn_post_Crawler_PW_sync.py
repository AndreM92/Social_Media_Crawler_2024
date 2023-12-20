import os
os.chdir(r'C:\Users\andre\Documents\Python\Web_Scraper\Social_Media_Crawler_2023')
from crawler_functions import *
import credentials_file as cred

import pyperclip

from playwright.sync_api import sync_playwright
from playwright.sync_api import ElementHandle
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import re

import numpy as np
import pandas as pd

import time
from datetime import datetime, timedelta
########################################################################################################################

# Settings
newpath = r"C:\Users\andre\OneDrive\Desktop\SSM_Energieanbieter"
os.chdir(newpath)
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
loginpage = 'https://www.linkedin.com/login/de'
network = 'LinkedIn'

source_file = "Profildaten_Energieanbieter_1.xlsx"
df_source = pd.read_excel(source_file, sheet_name=network)
df_source.set_index('ID',inplace=True)
dt_now = datetime.now()
dt_now_str = dt_now.strftime("%d.%m.%Y")
lower_dt = datetime.strptime('2022-10-31','%Y-%m-%d')
upper_dt = datetime.strptime('2023-11-01','%Y-%m-%d')

########################################################################################################################
# Functions

def login(page, useremail, password):
    inp_username = page.locator('#username')
    inp_username.clear()
    inp_username.type(useremail, delay=0.2)
    inp_password = page.locator('#password')
    inp_password.clear()
    inp_password.type(password, delay=0.2)
    login_button_selector = 'button[type="submit"]'
    page.wait_for_selector(login_button_selector)
    page.locator(login_button_selector).click()

def scroll_to_bottom(page):
    # Zoom out to scroll more quickly and prevent errors during the link collection process.
    page.evaluate(f'document.body.style.zoom = 0.5')
    previous_height = page.evaluate('document.body.scrollHeight')
    scroll_height = ''
    safety_counter = 0
    while scroll_height != previous_height and safety_counter <= 20:
        previous_height = page.evaluate('document.body.scrollHeight')
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(3000)
        scroll_height = page.evaluate('document.body.scrollHeight')
        safety_counter += 1

def get_postlinks(page):
    linklist = []
    open_menus = page.query_selector_all('svg[aria-label="Kontrollmenü öffnen"]')
    if len(open_menus) == 0:
        open_menus = page.query_selector_all('svg[a11y-text="Kontrollmenü öffnen"]')
    for o in open_menus:
        page.evaluate("(element) => { element.scrollIntoView(); }", o)
        o.click()
        # Error
        dropdown_selector = 'div.artdeco-dropdown__content-inner:visible'
        try:
            link_selector = dropdown_selector + " :text('Link zum Artikel kopieren')"
            page.wait_for_selector(link_selector, timeout=3000)
            page.locator(link_selector).click()
            link = pyperclip.paste()
            # If you want to use the clipboard
            #link = page.evaluate('() => navigator.clipboard.readText()')
        except:
            link = ''
            pass
        linklist.append(link)
    return linklist

def scrape_post(id_p, p, linklist, dt_now):
    likes, comments, shares, content, image, video = ['' for i in range(6)]
    date_elem = p.find('div', class_='ml4 mt2 text-body-xsmall t-black--light')
    if not date_elem:
        date_elem = p.find('div',class_='t-black--light t-14')
    date_text = extract_text(date_elem)
    post_date_dt, post_date = get_approx_date(dt_now, date_text)
    content_elem = p.find('span', class_='break-words')
    content = extract_text(content_elem)
    react_elements = p.find_all('button', attrs={'aria-label': True})
    aria_labels = [e['aria-label'] for e in react_elements]
    for a in aria_labels:
        e = extract_text(a)
        if 'Reaktionen' in a and likes == '':
            likes = extract_number(e)
        elif ' Kommentar' in a and comments == '':
            comments = extract_number(e)
        elif ' geteilt' in a or 'Veröffentlichungen' in a and shares == '':
            shares = extract_number(e)
    imagelinks = [e['src'] for e in p.find_all('img', src=True) if not 'company-logo' in e['src']]
    if p.find('video'):
        video = 1
        image = 0
    elif len(imagelinks) >= 1 or p.find('ul',class_='carousel-track') or p.find('iframe',src=True):
        image = 1
        video = 0
    else:
        image = 0
    if len(linklist) > id_p:
        link = linklist[id_p]
    else:
        link = ''
    if content == '':
        content = extract_text(p)
    result = [post_date, likes, comments, shares, image, video, link, content]
    return result


def main_postscraper(id, p_name, url, upper_dt, dt_now):
    dt_now_str = dt_now.strftime("%d.%m.%Y")
    if url[-1] == '/':
        url = url[:-1]
    post_page = url + '/posts/?feedView=all'
    post_page = post_page.replace('/?originalSubdomain=de','')
    page.goto(post_page)
    time.sleep(1)
    scroll_to_bottom(page)
    # Scroll up again
    page.evaluate('window.scrollTo(0, 0)')
    page_content = page.inner_text('html')
    page_text = extract_text(page_content)
    linklist = get_postlinks(page)
    soup = BeautifulSoup(page.content(), 'lxml')
    posts = soup.find_all('div', class_='ember-view occludable-update')
    if not linklist or len(posts) != len(linklist):
        linklist = get_postlinks(page)

    data_per_company = []
    for id_p, p in enumerate(posts):
        postdata = scrape_post(id_p, p, linklist, dt_now)
        print(postdata)
        post_date = postdata[0]
        if not post_date:
            continue
        post_dt = datetime.strptime(post_date, '%d.%m.%Y')
        if post_dt >= upper_dt:
            continue
        full_row = [id, p_name, id_p, dt_now_str] + postdata
        data_per_company.append(full_row)
    #       print(full_row[:-1])

    return data_per_company

########################################################################################################################
# Login and go to the first page
data = []
pw, browser, page = start_pw_browser(sync_playwright, loginpage)
login(page, cred.useremail_li, cred.password_li)


# Loop
for id, row in df_source.iterrows():
    if len(str(row['last post'])) <= 4 or str(row['last post']).strip() == 'Keine Beiträge':
        continue
    p_name = row['Profilname']
    url = row['url']

    data_per_company = main_postscraper(id, p_name, url, upper_dt, dt_now)
    data += data_per_company


# Create a DataFrame with all posts
header1 = ['ID_A', 'Profilname', 'ID_P', 'Datum_Erhebung', 'Datum_Beitrag']
header2 = ['Likes', 'Kommentare', 'Shares', 'Bild', 'Video', 'Link', 'Content']
dfPosts = pd.DataFrame(data, columns=header1 + header2)


# Export dfPosts to Excel (with the current time)
dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
file_name = 'Beiträge_LinkedIn' + dt_str_now + '.xlsx'
dfPosts.to_excel(file_name)



browser.close()
pw.stop