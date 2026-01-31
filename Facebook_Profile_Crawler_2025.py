
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
startpage = 'https://www.facebook.com/'
platform = 'Facebook'

upper_datelimit = '2026-02-01'
folder_name = "SMP_ÖPNV_2026"
file_name = "Website_Links_2026-01-29"
file_path = r"C:\Users\andre\OneDrive\Desktop/" + folder_name
source_file = file_name + ".xlsx"
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


def date_hint(date_text):
    day, month, year, date_str = ['' for _ in range(4)]
    mDictGer = {'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5, 'Juni': 6, 'Juli': 7, \
                    'August': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12}
    if 'Reel' in date_text:
        for key, value in mDictGer.items():
            month_key = '. '+ key[:3]
            if month_key in date_text:
                month = value
                month = str(month).zfill(2)
                curr_dt_str = f'01.{month}.2025'
                return curr_dt_str

    for key, value in mDictGer.items():
        if key in date_text:
            month = value
            month = str(month).zfill(2)
    if not month:
        for key, value in mDictGer.items():
            if key in date_text:
                month = value
                month = str(month).zfill(2)
    years = ['2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017']
    for y in years:
        if y in date_text:
            year = y
    if year and month:
        date_str = f'01.{month}.{year}'
    elif month:
        date_str = f'01.{month}.2025'
    else:
        recent = ['gestern', 'stunde', 'minute', 'tage', 'std.']
        if any(r in date_text.lower() for r in recent):
            curr_dt = datetime.now().date()
            date_str = curr_dt.strftime('%d.%m.%Y')
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
    except:
        return ''
    if datetime.now() < datetime.strptime(date_str, '%d.%m.%Y'):
        return ''
    return date_str


def scrapeProfile(url, take_screenshot):
    p_name, pagelikes, follower, last_post, raw_desc = ['' for _ in range(5)]
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if ('gelöscht' in pagetext and 'nicht verfügbar' in pagetext) and len(pagetext) <= 500 or len(pagetext) <= 200:
        p_name = 'page not available'
        return [p_name, pagelikes, follower, '', url, pagetext]
    p_name = get_p_name(driver, comp_keywords)
    if len(str(p_name)) <= 2:
        return [p_name, pagelikes, follower, '', url, pagetext]
    upper_posts = soup.find_all('div', class_='x1c4vz4f x2lah0s xeuugli x1bhewko xq8finb xnqqybz')
    posts = soup.find_all('div', {'class': 'x1n2onr6 x1ja2u2z',
                                  'aria-label': lambda x: x is None or 'Kommentar' not in x})
    if len(upper_posts) >= 1:
        driver.execute_script("window.scrollBy(0, 1000);")
    else:
        driver.execute_script("window.scrollBy(0, 300);")
    time.sleep(1)
    date_text = pagetext.rsplit('Facebook')[-1].strip()
    if len(date_text) < 50:
        date_text = pagetext.rsplit('Mehr Beiträge')[-1].strip()
    last_post = date_hint(date_text)
    if not last_post:
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
        last_post = date_hint(date_text)
    if not last_post and take_screenshot:
        scr_text = get_text_from_screenshot(driver, p_name)
        if len(posts) >= 1:
            last_post = date_hint(scr_text)
    #raw_desc_elements = soup.find_all('div',class_='x1yztbdb')
    raw_desc_elements = soup.find_all('div', class_='x7wzq59')
    if len(raw_desc_elements) >= 1:
        for e in raw_desc_elements:
            raw_desc = get_visible_text(Comment, e)
            if len(raw_desc) >= 31:
                if "Intro" in raw_desc[:30] or 'Steckbrief' in raw_desc[30] or 'Beschreibung' in raw_desc[30] \
                        or 'Details' in raw_desc[:30] or len(raw_desc) > 100:
                    break
    if not raw_desc:
        try:
            raw_desc_elem = driver.find_element(By.CLASS_NAME, 'x1yztbdb')
            raw_desc = extract_text(raw_desc_elem)
        except:
            return [p_name, pagelikes, follower, '', url, pagetext]
    if 'Details' in raw_desc:
        raw_desc = raw_desc.split('Details',1)[1]
    description = raw_desc.replace('Steckbrief ', '').replace('Intro', '').strip()
    stats_elem = soup.find('div',class_='x9f619 x1n2onr6 x1ja2u2z x78zum5 xdt5ytf x2lah0s x193iq5w x1cy8zhl xyamay9 x1614ocl')
    stats_text = extract_text(stats_elem)
    if stats_text:
        stats_list = str(stats_text).split('•')
        for e in stats_list:
            if "gefällt" in e.lower():
                pagelikes = extract_every_number(e)
            elif 'follower' in e.lower():
                follower = extract_every_number(e)
    if len(description) <= 5:
        description = extract_text(pagetext)
    if 'Fotos Alle Fotos' in description:
        description = description.rsplit('Fotos Alle Fotos',1)[0]
    new_url = driver.current_url
    if '?locale' in new_url:
        new_url = new_url.split('?locale')[0]
    return [p_name, pagelikes, follower, last_post, new_url, description]

########################################################################################################################
# Profile Crawler
if __name__ == '__main__':
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    try:
        from credentials_file import *
    except:
        useremail_fb = str(input('Enter your user-email:')).strip()
        password_fb = str(input('Enter your password:')).strip()
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)
    col_list = list(df_source.columns)

    # Open the browser, go to the startpage and login
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(useremail_fb, password_fb, driver, pyautogui)
    input('Press ENTER after the page is loaded')

    start_ID = 0
    # Loop through the companies
    for ID, row in df_source.iterrows():
        if 'ID' in col_list and col_list[0] != 'ID':
            ID = int(row['ID'])
        elif not 'nan' in str(ID):
            try:
                ID = int(ID)
                if ID < start_ID:  # If you want to skip some rows
                    continue
#                start_ID = ID + 1
            except:
                ID = str(ID)

        company = extract_text(row[comp_header])
        comp_keywords = get_company_keywords(company, row, col_list)
        url = extract_text(row[platform])
        if len(url) < 10 or '/search' in url or '/events' in url or '/public' in url:
            if len(url) < 5:
                url = ''
            data.append([ID, company, dt_str] + ['' for _ in range(4)] + [url,''])
            continue
        # Correct the url
        url = url.split('/followers')[0].split('/impressu')[0].split('locale=')[0]
        scraped_data = scrapeProfile(url, take_screenshot = False)
        full_row = [ID, company, dt_str] + scraped_data
        data.append(full_row)
        print(full_row)


    # DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'likes', 'follower', 'last_post', 'url', 'description']
    df_profiles = pd.DataFrame(data, columns=header)
#            df_profiles.set_index('ID')

    # Export to Excel
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
#    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_Facebook_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()