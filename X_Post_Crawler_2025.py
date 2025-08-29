
import os
import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import time
import pandas as pd
import re
from datetime import datetime, timedelta

chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
startpage = 'https://x.com/i/flow/login'
platform = 'X'
dt_str_now = None

upper_datelimit = '2025-08-01'
file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_Automatisierungstechnik 2025'
file_name = 'Auswahl_SMP Automatisierungstechnik 2025_2025-08-06'
file_type = '.xlsx'
source_file = file_path + '/' + file_name + file_type
branch_keywords = ['Automatisierung', 'System', 'Technik', 'Maschine', 'Industrie', 'Automation', 'Technologie',
                   'Technology', 'Roboter', 'Steuerung', 'technik']
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
    time.sleep(1)
    conf = driver.find_elements('xpath', "//*[contains(text(), 'Weiter') or contains(text(), 'weiter')]")
    for c in conf:
        try:
            c.click()
        except:
            pass
    time.sleep(2)
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
    time.sleep(2)
    try:
        driver.find_element('xpath', "//*[text()='Refuse non-essential cookies']").click()
    except Exception as e:
        print(repr(e))

def restart_browser(driver, webdriver, Service, chromedriver_path, username_tw, pasword_tw):
    driver.quit()
    time.sleep(3)
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)
    login(driver, startpage, username_tw, password_tw)
    time.sleep(3)
    return driver

def check_conditions(count, row, start_at = 0):
    if count < start_at:      # If you want to skip some rows
        return True
    if len(str(row['url'])) < 10:
        return True
    try:
        last_datestr = extract_text(row['last_post'])
        last_dt = datetime.strptime(last_datestr, "%d.%m.%Y")
        if (lower_dt - timedelta(days=31)) > last_dt:
            return True
    except:
        return False

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


# Post crawler functions
def inspect_page(ID, row, lower_dt):
    url = str(row['url'])
    p_name = row['profile_name']
    if len(url) < 10 or len(str(row['last_post'])) <= 4 or '2022' in str(row['last_post']):
        print([ID, p_name, '', '', url])
        return ['' for _ in range(4)]
    driver.get(url)
    time.sleep(3)
    last_post, current_dt, posts = get_last_date()
    if not current_dt:
        driver.execute_script("window.scrollBy(0,1500)", "")
        time.sleep(1)
        last_post, current_dt, posts = get_last_date()
    if not current_dt:
        return ['' for _ in range(4)]
    if current_dt < lower_dt:
        posts = ''
    url = driver.current_url
    return p_name, url, posts, last_post

# Scrape the post interactions
def get_reactions(p):
    react_elements = p.find_all('div', {'aria-label': True})
    aria_content = [str(e['aria-label']).lower().strip() for e in react_elements]
    react_elements2 = p.find_all('a', {'aria-label': True})
    aria_content2 = [str(e['aria-label']).lower().strip() for e in react_elements2]
    for a in aria_content:
        if ',' in a:
            aria_content += a.split(',')
    react_list = [a for a in aria_content if (20 > len(a) > 4 and not ('like' and 'view' in a))]
    react_list += [a for a in aria_content2 if 'view' in a]
    likes, comments, shares, views = [0 for _ in range(4)]
    for a in react_list:
        if 'like' in a and likes == 0:
            likes = extract_every_number(a)
        elif 'repl' in a and comments == 0:
            comments = extract_every_number(a)
        elif 'repost' in a and shares == 0:
            shares = extract_every_number(a)
        elif ('view' in a or 'View' in a) and views == 0:
            views = extract_every_number(a)
    return likes, comments, shares, views

def get_post_elements(p, full_text, tweet_type):
    image, video = 0, 0
    imagelinks_all = [p['src'] for p in p.find_all('img', src=True)]
    imagelinks = [p for p in imagelinks_all if not 'profile_image' in str(p) and not 'hashtag' in str(p) and not 'emoji' in str(p)]
    if len(imagelinks) >= 1:
        image, video = 1,0
    if p.find('video', src=True) or p.find('div', {'aria-label': 'Play'}) or 'livestream' in full_text:
        video, image = 1,0
    if p.find('div', {'data-testid': 'cardPoll'}):
        tweet_type = 'poll'
    return image, video, tweet_type

def get_link(p):
    links_raw = [l['href'] for l in p.find_all('a', href=True)]
    links = ['https://twitter.com' + l if not 'http' in l else l for l in links_raw]
    links_f = [l for l in links if 'status' in l]
    if len(links_f) >= 1:
        return links_f[0]
    if len(links) >= 1:
        return links[0]
    return ''

# post_scraper function scrapes the details of every post
def post_scraper(p, p_name, lower_dt):
    full_text = get_visible_text(Comment, p)
    if not full_text:
        return None, None
    try:
        date_elem = p.find('time')['datetime']
        date = date_elem.split('T')[0].strip()
        date_dt = datetime.strptime(date, "%Y-%m-%d")
        date = date_dt.strftime("%d.%m.%Y")
        if not 'retweet' in full_text and (date_dt >= upper_dt or date_dt < lower_dt):
            return None, date_dt
    except:
        return None, None
    tweet_type = 'tweet'
    if 'retweet' in full_text.lower() or 'repost' in full_text:
        tweet_type = 'retweet'
    ns = re.sub(r'[.-_]', '', p_name).strip().lower()
    if not (ns[:3] in full_text[:50].lower() or ns[-4:] in full_text[:50].lower()):
        tweet_type = 'ad'
    p_name2 = p_name
    if '·' in full_text:
        p_name2 = full_text[:50].split('·')[0].split('@')[0].strip()
        full_text = full_text.split('·',1)[1].strip()
    likes, comments, shares, views = get_reactions(p)
    image, video, tweet_type = get_post_elements(p, full_text, tweet_type)
    link = get_link(p)
    content_elem = p.find_all('span')
    content_all = [extract_text(t) for t in content_elem]
    content = ' '.join(
        [e for e in content_all if (e.strip() != p_name and e.strip() != '@' + p_name)
         and (e.strip() != p_name2 and e.strip() != '@' + p_name2) and len(e) >= 3])
    if len(str(content)) <= 4:
        content = full_text
    post_data = [date, tweet_type, likes, comments, shares, views, image, video, link, content]
    return post_data, date_dt

def scroller(scrolls, height2):
    height1 = height2
    height2 = driver.execute_script("return document.documentElement.scrollHeight")
    driver.execute_script("window.scrollBy(0,2000)", "")
    scrolls += 1
    time.sleep(1)
    if scrolls >= 50:
        time.sleep(1)
    if scrolls >= 150:
        time.sleep(1)
    height3 = driver.execute_script("return document.documentElement.scrollHeight")
    if height1 == height3 or scrolls == 280:
        return True, scrolls, height2
    return False, scrolls, height2

# Crawler function for the whole profile (scrolls down and scrapes the post data)
def page_crawler(id, p_name, dt_str, upper_dt, lower_dt):
    crawl = True
    distinct_posts = []
    distinct_linklist = []
    id_p = 0
    id_ad = 0
    scrolls = 0
    height2 = False
    pinned_comments = 0
    while crawl:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        posts = soup.find_all('article')
        if not posts and scrolls == 0:
            crawl = False
        for p in posts:
            post_data, date_dt = post_scraper(p, p_name, lower_dt)
            if date_dt and date_dt < lower_dt:
                if pinned_comments >= 3:
                    crawl = False
                    break
                pinned_comments += 1
            if not post_data or not date_dt or date_dt >= upper_dt:
                continue
            link = post_data[-2]
            if link in distinct_linklist:
                continue
            if post_data[1] == 'ad':
                full_row = [id, p_name, id_ad, dt_str] + post_data
                id_ad += 1
            else:
                full_row = [id, p_name, id_p, dt_str] + post_data
                id_p += 1
            print(full_row)
            distinct_linklist.append(link)
            distinct_posts.append(full_row)
        stopped, scrolls, height2 = scroller(scrolls, height2)
        scrolls += 1
        # I just want to make sure that the scroller doesn't stop too early
        #if scrolls >= 300 or stopped:
        if scrolls >= 400:
            break
    return distinct_posts

def check_conditions(count, row, start_at = 0):
    if count < start_at:      # If you want to skip some rows
        return True
    if len(str(row['url'])) < 10:
        return True
    try:
        last_datestr = extract_text(row['last_post'])
        last_dt = datetime.strptime(last_datestr, "%d.%m.%Y")
        if (lower_dt - timedelta(days=31)) > last_dt:
            return True
    except:
        return False
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    try:
        from credentials_file import *
    except:
        username_tw = str(input('Enter your username:')).strip()
        password_tw = str(input('Enter your password:')).strip()
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
    driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
    go_to_page(driver, startpage)
    login(driver, startpage, username_tw, password_tw)
    input('Press ENTER if the Login was successful')

    old_ID = 46
    # Iterate over the companies
    for ID, row in df_source.iterrows():
        if 'ID_new' in col_names:
            ID = extract_number(row['ID_new'])
        elif 'ID' in col_names:
            ID = extract_number(row['ID'])
        if ID <= old_ID:  # If you want to skip some rows
            continue
        p_name, url, posts, last_post = inspect_page(ID, row, lower_dt)
        if not posts:
            continue

        data_per_company = page_crawler(ID, p_name, crawl_dt_str, upper_dt, lower_dt)
        all_data += data_per_company
        old_ID = ID

        # Create a DataFrame with all posts
        header1 = ['ID_A', 'profile_name', 'ID_P', 'Erhebung', 'Datum']
        header2 = ['Beitragsart', 'Likes', 'Kommentare', 'Retweets', 'Aufrufe', 'Bild', 'Video', 'Link', 'Content']
        dfPosts = pd.DataFrame(all_data,columns=header1+header2)

        # Export dfPosts to Excel (with the current time)
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_X_' + dt_str_now + '.xlsx'
        dfPosts.to_excel(file_name)

    driver.quit()