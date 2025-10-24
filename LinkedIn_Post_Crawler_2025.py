
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
startpage = 'https://www.linkedin.com/login/de'
platform = 'LinkedIn'

upper_datelimit = '2025-10-01'
file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_Mineralwasser 2025'
file_name = 'Auswahl SMP Mineralwasser_2025-10-14'
file_type = '.xlsx'
source_file = file_path + '/' + file_name + file_type
########################################################################################################################

# Login function
def login(driver, username, password):
    WebDriverWait(driver,5).until(EC.presence_of_element_located((By.CSS_SELECTOR,'form.login__form')))
    nameslot = driver.find_element(By.CSS_SELECTOR, 'input#username')
    pwslot = driver.find_element(By.CSS_SELECTOR,'input#password')
    nameslot.clear()
#    nameslot.send_keys(cred.useremail_li)
    for char in username:
        nameslot.send_keys(char)
        time.sleep(.1)
    pwslot.clear()
    for char in password:
        pwslot.send_keys(char)
        time.sleep(.1)
    driver.find_element(By.XPATH, '//button[contains(text(), "Einloggen")]').click()
    time.sleep(2)

def find_post_date(p):
    post_date_dt = None
    last_post = None
    date_elements = ['Min.', 'Std.', 'Tag', 'Woche', 'Monat', 'Jahr']
    span_elems = p.find_all('span')
    for e in span_elems:
        if any(d in str(e) for d in date_elements):
            date_str = get_visible_text(Comment, e)
            if '•' in date_str:
                date_str = date_str.split('•')[1].strip()
            try:
                post_date_dt, last_post = get_approx_date(datetime.now(), date_str)
                break
            except:
                pass
    return post_date_dt, last_post

def start_at(df_source, ID, row, start_ID):
    col_names = list(df_source.columns)
    p_name = str(row['profile_name']).strip()
    if 'ID_new' in col_names:
        ID = extract_number(row['ID_new'])
    elif 'ID' in col_names:
        ID = extract_number(row['ID'])
    if ID < start_ID:  # If you want to skip some rows
        return False, start_ID, ID, p_name
    start_ID = ID + 1
    return True, start_ID, ID, p_name

def check_conditions(ID, p_name, row, lower_dt):
    if len(p_name) == 0 or p_name.lower() == 'nan' or p_name == 'None':
        return False
    url = str(row['url'])
    last_post = str(row['last_post'])
    if len(url) < 10 or 'Keine Beiträge' in str(last_post):
        return False
    if not isinstance(last_post, datetime):
        last_datestr = extract_text(last_post)
        try:
            last_post = datetime.strptime(last_datestr, "%d.%m.%Y")
        except:
            print([ID, url, 'no posts'])
            return False
#    if not last_datestr or len(url) < 10 or len(last_posts) <= 4 or 'Keine Beiträge' in last_posts:
    if (lower_dt - timedelta(days=31)) > last_post:
        return False
    try:
        driver.get(url + 'posts/?feedView=all')
        time.sleep(2)
    except:
        return False
    return True

# Full scrolls (posts don't disappear)
# Only posts within a year are shown on the page
def scroll_to_bottom():
    start_height = driver.execute_script('return document.body.scrollHeight')
    new_height = ''
    safety_counter = 0
    while start_height != new_height and safety_counter <= 50:
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
        time.sleep(1)
        new_height = driver.execute_script('return document.body.scrollHeight')
        safety_counter += 1

def check_distinct(distinct_content, scraped_post):
    p_text = str(scraped_post[-1])
    content_short = p_text
    if len(p_text) >= 200:
        content_short = p_text[:99] + p_text[-100:]
    if content_short not in distinct_content:
        distinct_content.append(content_short)
        return distinct_content
    return None

def scrape_post(p, p_name):
    post_date_dt, post_date = find_post_date(p)
    post_type, likes, comments, shares = ['' for _ in range(4)]
    post_text = get_visible_text(Comment, p)
    if p_name in post_text:
        post_type = 'post'
    if 'repostet' in post_text:
        post_type = 'repost'
    react_elements = p.find_all('button', attrs={'aria-label': True})
    aria_labels = [a['aria-label'] for a in react_elements]
    for a in aria_labels:
        ptext = extract_text(a)
        if not ptext:
            continue
        num = extract_every_number(ptext.split()[0])
        if 'Reaktionen' in ptext and likes == '':
            likes = num
        elif ' Kommentar' in a and comments == '':
            comments = num
            if str(comments)[-1] == '.':
                comments = extract_number(comments)
        elif 'Repost' in a or 'Veröffentlichungen' in a and shares == '':
            shares = num
            if str(shares)[-1] == '.':
                shares = extract_number(shares)
    if 'Menü' in str(likes):
        likes = ''
    if not likes and '1 Gefällt' in post_text:
        likes = 1
    if not shares and 'direkt geteilter' in post_text:
        shares = 1

    content_elem = p.find('span', class_='break-words')
    if content_elem:
        content = get_visible_text(Comment, content_elem)
    if not content_elem or len(str(content)) <= 4:
        content = get_visible_text(Comment, p)

    imagelinks = [e['src'] for e in p.find_all('img', src=True) if not 'company-logo' in e['src']]
    if p.find('video'):
        video, image = 1,0
    elif len(imagelinks) >= 1 or p.find('ul', class_='carousel-track') or p.find('iframe', src=True):
        image, video = 1,0
    else:
        image, video = 0,0
    link = ''
    content = content.replace('Hashtag # ','#')
    scraped_post = [post_date, post_type, likes, comments, shares, image, video, link, content]
    return post_date_dt, scraped_post

def scrape_all_posts(ID, p_name, lower_dt, upper_datelimit):
    upper_dt = datetime.strptime(upper_datelimit, '%Y-%m-%d')
    data_per_company = []
    distinct_content = []
    id_p = 0
    no_p = 0
    for _ in range(100):
        len_post_list = len(data_per_company)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        posts = soup.find_all('div', class_='ember-view occludable-update')
        for p in posts:
            post_dt, postdata = scrape_post(p, p_name)
            if not postdata or (post_dt and post_dt >= upper_dt):
                continue
            if post_dt and post_dt < lower_dt:
                break
            distinct_content_new = check_distinct(distinct_content, postdata)
            if distinct_content_new:
                full_row = [ID, p_name, id_p, dt_str] + postdata
                print(full_row)
                data_per_company.append(full_row)
                distinct_content = distinct_content_new
                id_p += 1

        if len_post_list == len(data_per_company) and no_p > 10:
            print('No more new posts')
            break
        if len_post_list == len(data_per_company):
            no_p += 1
        else:
            no_p = 0
        driver.execute_script("window.scrollBy(0, 2000);")
        wait_time = round(((len_post_list) * 0.01) ** 0.5)
        time.sleep(wait_time)
    return data_per_company
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    file = None
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    try:
        from credentials_file import useremail_li, password_li
    except:
        useremail_li = str(input('Enter your useremail:')).strip()
        password_li = str(input('Enter your password:')).strip()
    os.chdir(file_path)
    name_structure = 'Profile_' + platform + '_' + str(datetime.now().year)
    for f in os.listdir():
        if name_structure in f:
            file = extract_text(f)
    if not file:
        print('No profile file found')
        exit()

    df_source, dt, dt_str, upper_dt, lower_dt = post_crawler_settings(file, platform, None, upper_datelimit)

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)
    login(driver, useremail_li, password_li)

    start_ID = 0
    # Iterate over the companies
    for ID, row in df_source.iterrows():
        start, start_ID, ID, p_name = start_at(df_source, ID, row, start_ID)
        if not start:
            continue
        try:
            go_crawl = check_conditions(ID, p_name, row, lower_dt)
        except Exception as e:
            print(f"Error: {e}")
            driver.quit()
            time.sleep(5)
            driver = start_browser(webdriver, Service, chromedriver_path)
            go_to_page(driver, startpage)
            login(driver, useremail_li, password_li)
            go_crawl = check_conditions(ID, p_name, row, lower_dt)
        if not go_crawl:
            continue

        data_per_company = scrape_all_posts(ID, p_name, lower_dt, upper_datelimit)
        all_data += data_per_company

        # Create a DataFrame with all posts
        header1 = ['ID_A', 'Profilname', 'ID_P', 'Erhebung', 'Datum']
        header2 = ['post_type', 'Likes', 'Kommentare', 'Shares', 'Bild', 'Video', 'Link', 'Content']
        dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

        # Export dfPosts to Excel (with the current time)
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_' + platform + '_' + dt_str_now + '.xlsx'
        dfPosts.to_excel(file_name)

    driver.quit()