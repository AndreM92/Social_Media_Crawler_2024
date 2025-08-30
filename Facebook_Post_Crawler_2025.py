
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
dt_str_now = None

upper_datelimit = '2025-08-01'
file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_Automatisierungstechnik 2025'
file_name = 'Auswahl_SMP Automatisierungstechnik 2025_2025-08-06'
file_type = '.xlsx'
source_file = file_path + '/' + file_name + file_type
branch_keywords = ['Automatisierung', 'System', 'Technik', 'Maschine', 'Industrie', 'Automation', 'Technologie',
                   'Technology', 'Roboter', 'Steuerung', 'technik']
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

def check_for_captchas(driver, Comment):
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if not pagetext or 'Puzzleteil' in pagetext or 'Verifiziere' in pagetext or 'Schieberegler' in pagetext:
        driver.maximize_window()
        input('Press ENTER after solving the captcha')
    return None

def inspect_profile(row, lower_dt):
    p_name = extract_text(row['profile_name'])
    url = extract_text(row['url'])
    last_post_dt = row['last_post']
    if not url or len(url) <= 4 or len(str(last_post_dt)) <= 4:
        return None, None, None
    if not isinstance(last_post_dt,datetime):
        try:
            last_post_dt = datetime.strptime(last_post_dt, '%d.%m.%Y')
        except:
            return None, p_name, url
    if (lower_dt - timedelta(days=31)) > last_post_dt:
        return None, p_name, url
    driver.get(url)
    time.sleep(3)
    driver.execute_script("window.scrollBy(0, 1800);")
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    posts = soup.find_all('div', {'class': 'x1n2onr6 x1ja2u2z',
                                  'aria-label': lambda x: x is None or 'Kommentar' not in x})
    if len(posts) == 0:
        return None, p_name, url
    return last_post_dt, p_name, url

def scrape_reel(rawtext, p):
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
    p_text = p_text.rsplit('·', 1)[0].strip()
    r_links = [l['href'] for l in p.find_all('a', href=True) if 'reel' in l['href']]
    if len(r_links) >= 1:
        link = "https://www.facebook.com" + r_links[0].split('?', 1)[0]
    reel_data = [post_date, likes, comments, shares, link, p_text]
    return reel_data

# Scrape the posts
def get_p_link(p):
    links = [str(l['href']) for l in p.find_all('a', href=True)]
    f_links = [l for l in links if ('post' in l or '/p/' in l) and 'www.' in l]
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
        p_text_s = p_text.split('·', 1)[1].strip()
        if 'Reaktionen' in p_text_s or 'reactions' in p_text_s:
            p_text = p_text_s
    p_text1 = p_text
    if 'Teilen' in p_text:
        if p_text.count('Teilen') > 1:
            p_text = 'Teilen ' + ' '.join(p_text.split('Teilen')[:2]).strip()
        else:
            p_text = p_text.split('Teilen')[0].strip()
    else:
        if 'Kommentieren' in p_text:
            p_text = p_text.split('Kommentieren')[0].strip()
    forbidden_chars = ['+', '-', '*', '=']
    if any(c in p_text[0] for c in forbidden_chars):
        p_text = '$$' + p_text
    comments = False
    if len(p_text1) - len(p_text) >= 145 or 'Kommentar' in p_text1:
        comments = True
    if 'Alle Reaktionen:' in p_text:
        reactions = p_text.split('Alle Reaktionen:')[1].strip()
    elif 'All reactions' in p_text:
        reactions = p_text.split('All reactions:')[1].strip()
    elif 'Kommentar' in p_text:
        reactions = [p_text.split('Kommentar')[0].split()[-1]]
    else:
        reactions = None
    return p_text1, p_text, reactions, comments

def get_reactions(p_text1, reactions, comments):
    if not reactions or len(reactions) <= 4 :
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

def post_scraper(p):
    rawtext = str(get_visible_text(Comment, p))
    if len(rawtext) <= 30 or not p_name[:4].lower() in rawtext.lower():
        return None
    post_date = ''
    if 'Reels' in rawtext:
        p_type = 'reel'
        video, image = 1, 0
        post_date, likes, comments, shares, link, p_text = scrape_reel(rawtext, p)
    else:
        p_type = 'post'
        link = get_p_link(p)
        image, video = find_p_elements(p, rawtext)
        p_text1, p_text, reactions, comments = split_p_text(rawtext)
        likes, comments, shares = get_reactions(p_text1, reactions, comments)
    return [post_date, likes, comments, shares, image, video, p_type, link, p_text]

def check_distinct(distinct_content, scraped_post):
    p_text = str(scraped_post[-1])
    content_short = p_text
    if len(p_text) >= 200:
        content_short = p_text[:99] + p_text[-100:]
    if content_short not in distinct_content:
        distinct_content.append(content_short)
        return distinct_content
    return None

# All comments
def comments_scraper(c_l):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    comments_el = soup.find_all(attrs={"aria-label": lambda value: value and "Kommentar" in value})
    if len(comments_el) >= 1:
        for c in comments_el:
            #text_element = c.find('div', {'class': 'x1lliihq xjkvuk6 x1iorvi4'})
            c_t = str(get_visible_text(Comment, c))
            if len(c_t) < 30:
                continue
            print(c_t)
            if c_t not in c_l:
                c_l.append(c_t)
    return c_l
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    try:
        from credentials_file import *
    except:
        username_fb = str(input('Enter your username:')).strip()
        password_fb = str(input('Enter your password:')).strip()
    os.chdir(file_path)
    file ='Profile_' + platform + '_' + str(datetime.now().year)
    for f in os.listdir():
        if file in f:
            file = extract_text(f)
            break
    df_source, dt, crawl_dt_str, upper_dt, lower_dt = post_crawler_settings(file, platform, dt_str_now, upper_datelimit)
    col_names = list(df_source.columns)

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(username_fb, password_fb, driver, pyautogui)
    time.sleep(3)
    check_for_captchas(driver, Comment)
    input('Press ENTER if the Login was successful')

    start_time = time.time()
    old_ID = 0
    # Iterate over the companies
    for ID, row in df_source.iterrows():
        if 'ID_new' in col_names:
            ID = row['ID_new']
        elif 'ID' in col_names:
            ID = row['ID']
        if ID <= old_ID:  # If you want to skip some rows
            continue

        last_post_dt, p_name, url = inspect_profile(row, lower_dt)
        if not last_post_dt:
            print(ID, p_name, url, ' No Posts')
            continue

        data_per_company = []
        distinct_content = []
        count_p = 0
        no_p = 0
        days_delta = (last_post_dt - lower_dt).days
        scrolls = round(days_delta / 2)
        if scrolls < 100:
            scrolls = 100

        for _ in range(scrolls):
            len_post_list = len(data_per_company)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            posts = soup.find_all('div', class_='x1n2onr6 x1ja2u2z')
            if count_p == 0:
                upper_posts = soup.find_all('div', class_='x1c4vz4f x2lah0s xeuugli x1bhewko xq8finb xnqqybz')
                if len(upper_posts) >= 1:
                    posts = upper_posts + posts
            for p in posts:
                scraped_post = post_scraper(p)
                if not scraped_post:
                    continue
                distinct_content_new = check_distinct(distinct_content, scraped_post)
                if distinct_content_new:
                    count_p += 1
                    full_row = [ID, p_name, count_p, crawl_dt_str] + scraped_post
                    print(full_row)
                    data_per_company.append(full_row)
                    distinct_content = distinct_content_new
            if len_post_list == len(data_per_company) and no_p >= 10:
                print('No more new posts')
                break
            if len_post_list == len(data_per_company):
                no_p += 1
            else:
                no_p = 0
            driver.execute_script("window.scrollBy(0, 1600);")
            wait_time = round(((len_post_list)*0.01)**0.5)
            time.sleep(wait_time)

        old_id = ID
        ##### Safe #####
        all_data += data_per_company

        # Create a DataFrame with all posts
        header1 = ['ID_A', 'profile_name', 'ID_P', 'Erhebung', 'Datum']
        header2 = ['Likes', 'Kommentare', 'Shares', 'Bild', 'Video', 'Beitragsart', 'Link', 'Content']
        dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

        # Export dfPosts to Excel (with the current time)
        dt_str_now2 = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_Facebook_' + dt_str_now2
        dfPosts.to_excel(file_name + '.xlsx')

        # Close the crawler after two hours
        end_time = time.time()
        time_diff = end_time - start_time
        if time_diff >= (180 * 60):
            start_time = time.time()
            driver.quit()

    driver.quit()