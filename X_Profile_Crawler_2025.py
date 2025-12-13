
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
startpage = 'https://x.com/i/flow/login'
platform = 'Twitter'

upper_datelimit = '2025-12-01'
folder_name = "SMP_Glücksspiel_2025"
file_name = "Auswahl SMP Glücksspiel_2025-12-01"
file_path = r"C:\Users\andre\OneDrive\Desktop/" + folder_name
source_file = file_name + ".xlsx"
########################################################################################################################

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
    conf = driver.find_elements('xpath', "//*[contains(text(), 'Weiter') or contains(text(), 'weiter')]")
    for c in conf:
        try:
            c.click()
        except:
            pass
    time.sleep(2)
    # Error: Unusual Login activities
    try:
        pwslot = driver.find_element(By.CSS_SELECTOR,'input[autocapitalize="sentences"][name="password"]')
    except:
        try:
            pwx = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input'
            WebDriverWait(driver, 5).until(EC.presence_of_element_located(('xpath', pwx)))
            pwslot = driver.find_element('xpath', pwx)
            pwslot.clear()
        except:
            return None
    for char in password:
        pwslot.send_keys(char)
        time.sleep(.2)
    login_buttons = driver.find_elements('xpath', "//*[contains(text(), 'Anmelden') or contains(text(), 'anmelden')]")
    for b in login_buttons:
        try:
            b.click()
        except:
            pass
#       pwslot.send_keys(cred.password_tw)
#        loginx = '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/div/div'
#        driver.find_element('xpath', loginx).click()
    time.sleep(2)
    try:
        driver.find_element('xpath', "//*[text()='Refuse non-essential cookies']").click()
    except Exception as e:
        print(repr(e))

def get_last_date():
    soup = BeautifulSoup(driver.page_source, 'lxml')
    last_post, parsed_datetime = '', ''
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
    return last_post, parsed_datetime, posts

# A function to open the targetpage and scrape the profile stats
def scrapeProfile(driver, url):
    p_name, follower, following, joined, shorter_desc = ['' for _ in range(5)]
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if len(pagetext) <= 1000 or 'not available' in pagetext:
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
    new_url = driver.current_url
    not_existent = 'This account doesn’t exist'
    if len(pagetext) <= 1000 or not_existent in pagetext or (not 'twitter.com' in new_url and not 'x.com' in new_url):
        return [not_existent, follower, following, '', joined, new_url, pagetext]
    full_desc_elem = soup.find('div', class_='css-175oi2r r-3pj75a r-ttdzmv r-1ifxtd0')
    if not full_desc_elem:
        print('no description found')
    full_desc = get_visible_text(Comment, full_desc_elem)
#   full_desc_elem = soup.find('div', class_='css-1dbjc4n r-1ifxtd0 r-ymttw5 r-ttdzmv')
#    full_desc_elem = soup.find('div', class_='css-175oi2r r-ymttw5 r-ttdzmv r-1ifxtd0')
    p_name = str(extract_text(soup.find('div', {'data-testid': 'UserName'})))
    if '@' in full_desc:
        if len(p_name) <= 4 or len(p_name) >= 30:
            p_name, shorter_desc = full_desc.split('@', 1)[1].split(' ', 1)
        else:
            shorter_desc = full_desc.split('@', 1)[1].strip()
    if '@' in p_name:
        p_name = p_name.split('@')[1].strip()
    if len(str(full_desc)) >= 30 and p_name in full_desc[:30]:
        shorter_desc = full_desc.split(p_name,1)[1].strip()
    if len(shorter_desc) >= 10:
        dlist = shorter_desc.split()
        for pos, e in enumerate(dlist):
            e = e.lower()
            if 'followers' in e and not 'followed' in e and follower == '':
                follower = dlist[pos - 1]
                follower = extract_every_number(follower)
            elif 'following' in e and not 'followed' in e and following == '':
                following = dlist[pos - 1]
                following = extract_every_number(following)
            elif 'joined' in e:
                joined = ' '.join(dlist[(pos + 1):(pos + 3)])
    last_post, last_post_dt, posts = get_last_date()
    full_desc = full_desc.replace('Follow Click to Follow ','').replace('Not followed by anyone you’re following',
                                                                        '').replace('Translate bio ','').strip()
    datarow = [p_name, follower, following, joined, last_post, new_url, full_desc]
    return datarow
########################################################################################################################

# Profile crawler
if __name__ == '__main__':
    # Settings for profile scraping
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    try:
        from credentials_file import *
    except:
        username_tw = str(input('Enter your username:')).strip()
        password_tw = str(input('Enter your password:')).strip()
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)
    if 'X' in col_list:
        platform = 'X'
    elif 'Twitter' in col_list:
        platform = 'Twitter'
    else:
        print('No platform found')
        exit()

    # Start crawling
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)
    login(driver, startpage, username_tw, password_tw)
    input('Change your password and login manually')

    # Iterating over the companies
    for n, row in df_source.iterrows():
        if 'ID' in col_list and col_list[0] != 'ID':
            ID = int(row['ID'])
        elif not 'nan' in str(n):
            ID = int(n)
        if ID <= 0:                   # If you want to skip some rows
            continue

        company = extract_text(row[comp_header])
        comp_keywords = get_company_keywords(company, row, col_list)
        url = str(row[platform])
        if len(url) < 10:
            empty_row = [ID, company, dt_str] + ['' for _ in range(7)]
            data.append(empty_row)
            continue

        datarow = scrapeProfile(driver, url)
        full_row = [ID, company, dt_str] + datarow
        data.append(full_row)
        print(datarow)

    # DataFrame
    header = ['ID','company','date','profile_name','follower','following','joined','last_post', 'url','description']
    df_profiles = pd.DataFrame(data,columns=header)
    df_profiles.set_index('ID')

    # Export to Excel
#    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '_2.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()