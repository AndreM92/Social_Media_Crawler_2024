from crawler_functions import *
import credentials_file as cred

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

# General Settings
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
startpage = 'https://twitter.com/i/flow/login'
network = 'X'
dt_str_now = None
########################################################################################################################

def settings(source_file):
    df_source = pd.read_excel(source_file)
    df_source.set_index('ID', inplace=True)
    col_list = list(df_source.columns)
    if 'Anbieter' in col_list:
        comp_header = 'Anbieter'
    elif 'Firma' in col_list:
        comp_header = 'Firma'
    dt = datetime.now()
    dt_str = dt.strftime("%d.%m.%Y")

    return df_source, col_list, comp_header, dt, dt_str

# Login function
def login(driver, startpage, email, password):
    if driver.current_url != startpage:
        driver.get(startpage)
        time.sleep(3)
    try:
        nameslot = driver.find_element(By.CSS_SELECTOR,'input[autocapitalize="sentences"][autocomplete="username"]')
    except:
        try:
            xp1 = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[5]/label/div/div[2]/div/input'
            nameslot = driver.find_element('xpath', xp1)
        except:
            pass
    nameslot.click()
    nameslot.clear()
    for char in email:
        time.sleep(0.1)
        nameslot.send_keys(char)
#    nameslot.send_keys(email)
    time.sleep(1)
    pushx = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[6]/div'
    driver.find_element('xpath',pushx).click()
    # Error: Unusual Login activities
    pwx = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input'
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located(('xpath', pwx)))
        pwslot = driver.find_element('xpath', pwx)
        pwslot.clear()
        for char in password:
            pwslot.send_keys(char)
            time.sleep(.2)
        #       pwslot.send_keys(cred.password_tw)
        loginx = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/div/div'
        driver.find_element('xpath', loginx).click()
    except Exception as e:
        time.sleep(2)
        print(repr(e))
    time.sleep(2)
    cookiebutton = driver.find_element('xpath', "//*[text()='Refuse non-essential cookies']")
    if cookiebutton:
        try:
            cookiebutton.click()
        except Exception as e:
            print(repr(e))

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(driver, url):
    p_name, follower, following, joined, last_post = ['' for _ in range(5)]
    driver.get(url)
    time.sleep(4)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if len(pagetext) <= 1000 or 'not available' in pagetext:
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
    new_url = driver.current_url
    not_existent = 'This account doesn’t exist'
    if len(pagetext) <= 1000 or not_existent in pagetext or not 'twitter.com' in new_url:
        return [not_existent, follower, following, last_post, joined, new_url, pagetext]

    full_desc_elem = soup.find('div', class_='css-1dbjc4n r-1ifxtd0 r-ymttw5 r-ttdzmv')
    if not full_desc_elem:
        full_desc_elem = soup.find('div',class_='css-175oi2r r-ymttw5 r-ttdzmv r-1ifxtd0')
        full_desc = ' '.join([extract_text(e) for e in full_desc_elem]).replace('Following', 'Following ')
    else:
        full_desc = extract_text(full_desc_elem)
    if '@' in full_desc:
        p_name, full_desc = full_desc.split('@',1)[1].split(' ',1)
    if len(p_name) <= 2 or len(p_name) >= 30:
        p_name = extract_text(soup.find('div', {'data-testid': 'UserName'}))
        if '@' in p_name:
            p_name = p_name.split('@')[1]
    if len(full_desc) >= 10:
        dlist = full_desc.split()
        for pos, e in enumerate(dlist):
            e = e.lower()
            if 'followers' in e and not 'followed' in e and follower == '':
                follower = dlist[pos - 1]
                print(follower)
                follower = extract_big_number(follower)
            elif 'following' in e and not 'followed' in e and following == '':
                following = dlist[pos - 1]
                following = extract_big_number(following)
            elif 'joined' in e:
                joined = ' '.join(dlist[(pos + 1):(pos + 3)])
    posts = soup.find_all('article')
    if len(posts) >= 2:
        # Last or second last (not pinned) post
        last_post = posts[1]
        date_str = last_post.find('time')['datetime']
        parsed_datetime = datetime.fromisoformat(date_str.replace('Z', ''))
        last_post = parsed_datetime.strftime('%d.%m.%Y')
    if len(str(last_post)) <= 4:
        date_elements = driver.find_elements('xpath', '//time[@datetime]')
        if len(date_elements) >= 2:
            date_str = date_elements[1].get_attribute('datetime')
            parsed_datetime = datetime.fromisoformat(date_str.replace('Z', ''))
            last_post = parsed_datetime.strftime('%d.%m.%Y')
    datarow = [p_name, follower, following, joined, last_post, new_url, full_desc]
    return datarow
########################################################################################################################

if __name__ == '__main__':
    # Settings for profile scraping
    newpath = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
    os.chdir(newpath)
    source_file = "Liste_Nahrungsergänzungsmittel_2024_20240108.xlsx"
    df_source, col_list, comp_header, dt, dt_str = settings(source_file)

    # Start crawling
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(driver, startpage, cred.username_tw, cred.password_tw)

    # Iterating over the companies
    for id, row in df_source.iterrows():
        if id <= -1:
            continue
        company = extract_text(row[comp_header])
        comp_keywords = get_company_keywords(company, row, col_list)
        url = str(row[network])
        if len(url) < 10:
            empty_row = [id, company, dt_str] + ['' for _ in range(7)]
            data.append(empty_row)
            continue

        datarow = scrapeProfile(driver, url)
        full_row = [id, company, dt_str] + datarow
        data.append(full_row)
        print(datarow)

        if id >= 7:
            break


    # DataFrame
    header = ['ID', 'Anbieter', 'Erh.Datum', 'Profilname', 'follower', 'following', 'joined', 'last post', 'url',
              'description']
    dfProfiles = pd.DataFrame(data, columns=header)
    dfProfiles.set_index('ID')

    # Export to Excel
    #    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_Twitter_' + dt_str_now + '.xlsx'
    with pd.ExcelWriter(recent_filename) as writer:
        dfProfiles.to_excel(writer, sheet_name='Profildaten')


    driver.quit()