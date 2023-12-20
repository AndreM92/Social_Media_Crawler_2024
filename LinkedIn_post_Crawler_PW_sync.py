import os
os.chdir(r'C:\Users\andre\Documents\Python\Web_Scraper\Social_Media_Crawler_2023')
from crawler_functions import *
import credentials_file as cred

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
dt = datetime.now()
dt_str = dt.strftime("%d.%m.%Y")
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
    previous_height = page.evaluate('document.body.scrollHeight')
    scroll_height = ''
    safety_counter = 0
    while scroll_height != previous_height and safety_counter <= 20:
        previous_height = page.evaluate('document.body.scrollHeight')
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(3000)
        scroll_height = page.evaluate('document.body.scrollHeight')
        safety_counter += 1

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
    print(id,p_name,url)
    break

#def scrape_posts():
    if url[-1] == '/':
        url = url[:-1]
    post_page = url + '/posts/?feedView=all'
    post_page = post_page.replace('/?originalSubdomain=de','')
    page.goto(post_page)
    time.sleep(1)
    scroll_to_bottom(page)
    # Scroll up again
    page.evaluate('window.scrollTo(0, 0)')





browser.close()
pw.stop