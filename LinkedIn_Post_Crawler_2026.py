
import os
import sys
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import time
import pandas as pd
import re
import random
from datetime import datetime, timedelta

# Settings
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
startpage = 'https://www.linkedin.com/login/de'
platform = 'LinkedIn'

upper_datelimit = '2026-10-01'
file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_Rüstungsunternehmen_2026'

sys.path.insert(0, path_to_crawler_functions)
from crawler_functions import *
from selenium.webdriver.common.keys import Keys

########################################################################################################################
# LinkedIn delivers two different layouts, depending on the login session:
# New layout (2026): hashed css classes (e.g. 'b4la49 b4lguo'), which change regularly, so the elements are found
# via the page structure and fixed texts instead of class names:
# - every post is a div[role=listitem] with the hidden headline "Feed-Beitrag"
# - the feed scrolls inside main#workspace (not the window)
# - the post urn is part of the id of the text block or of the embed link in the control menu
# Old layout: every post is a div.occludable-update with the urn in data-urn. Posts outside of the visible area
# get emptied ("occluded"), so they have to be read while scrolling through the feed.

POST_XPATH = "//h2[normalize-space()='Feed-Beitrag']/ancestor::div[@role='listitem'][1]"
OLD_POST_CSS = 'div.occludable-update'

# LinkedIn only loads a limited number of posts per feed (400 sorted by date, 500 sorted by relevance)
FEED_LIMIT = 380

def is_old_layout():
    return bool(driver.find_elements(By.CSS_SELECTOR, OLD_POST_CSS + ', #sort-dropdown-trigger'))

# Stop everything, if LinkedIn shows a security check (it has to be solved manually)
def check_for_checkpoint():
    if 'checkpoint' in driver.current_url or 'authwall' in driver.current_url:
        raise RuntimeError('LinkedIn security check (checkpoint) - please solve it manually and restart the crawler')

def count_posts():
    if is_old_layout():
        return len(driver.find_elements(By.CSS_SELECTOR, OLD_POST_CSS))
    return len(driver.find_elements(By.XPATH, POST_XPATH))

# Some feeds stop loading automatically and show a button instead
def click_load_more_button():
    buttons = [b for b in driver.find_elements(By.XPATH, "//button[contains(., 'Weitere Ergebnisse anzeigen')]")
               if b.is_displayed()]
    if not buttons:
        return False
    try:
        driver.execute_script('arguments[0].scrollIntoView({block:"center"})', buttons[0])
        driver.execute_script('arguments[0].click()', buttons[0])
        time.sleep(2)
        return True
    except:
        return False

# Login function
def login(username, password, driver):
    WebDriverWait(driver,5).until(EC.presence_of_element_located((By.CSS_SELECTOR,'form.login__form')))
    nameslot = driver.find_element(By.CSS_SELECTOR, 'input#username')
    pwslot = driver.find_element(By.CSS_SELECTOR,'input#password')
    nameslot.clear()
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
    date_elements = ['Min', 'Std', 'Tag', 'Woche', 'Monat', 'Jahr']
    span_elems = p.find_all('span')
    for e in span_elems:
        if any(d in str(e) for d in date_elements):
            date_str = get_visible_text(Comment, e)
            if '•' in date_str:
                date_str_options = date_str.split('•')
                for de in date_str_options:
                    if any(d in str(de) for d in date_elements):
                        date_str = str(de).strip()
                        break
            if not re.match(r'^\d+\s*(Min|Std|Tag|Woche|Monat|Jahr)', date_str):
                continue
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
    if not ID:
        ID = 0
    if ID < start_ID:  # If you want to skip some rows
        return False, ID, p_name
    return True, ID, p_name

def check_conditions(ID, p_name, row, lower_dt):
    if len(p_name) == 0 or p_name.lower() == 'nan' or p_name == 'None':
        return False
    url = str(row['url'])
    last_post = row['last_post']
    if len(url) < 10 or 'Keine Beiträge' in str(last_post):
        return False
    if not isinstance(last_post, datetime):
        last_post = str(last_post).strip()
        last_datestr = extract_text(last_post)
        try:
            last_post = datetime.strptime(last_datestr, "%d.%m.%Y")
        except:
            print([ID, url, 'no posts'])
            return False
    if (lower_dt - timedelta(days=31)) > last_post:
        return False
    if not url[-1] == '/':
        url = url + '/'
    # A short random break between the companies
    time.sleep(random.uniform(3, 7))
    driver.get(url + 'posts/?feedView=all')
    check_for_checkpoint()
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located(
            (By.XPATH, "//h2[normalize-space()='Feed-Beitrag'] | //div[contains(@class, 'occludable-update')]"
                       " | //*[contains(text(), 'Noch keine Beiträge')]")))
        time.sleep(3)
    except:
        return False
    if count_posts() == 0:
        return False
    return True

# Old layout: dropdown "Sortieren nach: Relevanteste" -> "Aktuellste"
def sort_by_newest_old():
    for attempt in range(2):
        try:
            trigger = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'sort-dropdown-trigger')))
            if 'Aktuellste' in trigger.text:
                return True
            driver.execute_script('arguments[0].scrollIntoView({block:"center"})', trigger)
            time.sleep(1)
            trigger.click()
            time.sleep(2.5)
            options = [o for o in driver.find_elements(By.XPATH, "//button[@role='option'][normalize-space(.)='Aktuellste']")
                       if o.is_displayed()]
            if options:
                options[0].click()
                time.sleep(6)
            if 'Aktuellste' in driver.find_element(By.ID, 'sort-dropdown-trigger').text:
                return True
        except:
            time.sleep(3)
    return False

# The feed is sorted by "Beliebteste" by default, so it gets switched to "Aktuell" (= Neueste)
# For some pages the sorted feed stays empty. Then the page is reloaded and the default feed is used.
def sort_by_newest():
    if is_old_layout():
        return sort_by_newest_old()
    sorted_feed = False
    try:
        sort_button = driver.find_element(By.XPATH, "//p[contains(., 'Sortieren nach')]/ancestor::*[@role='button'][1]")
        if 'Neueste' in sort_button.text:
            return True
        driver.execute_script('arguments[0].scrollIntoView({block:"center"})', sort_button)
        sort_button.click()
        time.sleep(1.5)
        options = [o for o in driver.find_elements(By.XPATH, "//*[@role='menuitem']//*[normalize-space(text())='Aktuell']")
                   if o.is_displayed()]
        if options:
            options[0].click()
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, POST_XPATH)))
                time.sleep(1)
                sorted_feed = 'Neueste' in driver.find_element(By.XPATH, "//p[contains(., 'Sortieren nach')]").text
            except:
                pass
    except:
        pass
    if not sorted_feed and not driver.find_elements(By.XPATH, POST_XPATH):
        driver.refresh()
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, POST_XPATH)))
        except:
            pass
        time.sleep(1)
    return sorted_feed

# Scroll the feed container and wait until new posts are loaded
# The longer the feed, the longer LinkedIn needs to load the next posts, so the waiting time grows
def load_more_posts(n_posts):
    check_for_checkpoint()
    max_wait = min(8 + n_posts * 0.03, 40)
    for attempt in range(3):
        driver.execute_script("const m = document.querySelector('main#workspace') || document.scrollingElement;"
                              "m.scrollTop = m.scrollHeight;")
        click_load_more_button()
        t0 = time.time()
        while time.time() - t0 < max_wait:
            time.sleep(1)
            if len(driver.find_elements(By.XPATH, POST_XPATH)) > n_posts:
                time.sleep(1)
                return True
            if click_load_more_button():
                t0 = time.time()
        # Small scroll up and down again to trigger the loading
        driver.execute_script("const m = document.querySelector('main#workspace') || document.scrollingElement;"
                              "m.scrollBy(0, -1500);")
        time.sleep(1)
    return False

# Link from the id of the text block, e.g. "...UserGeneratedContentPostUrn(userGeneratedContentId=7510705806120517632)"
def get_link_from_id(p):
    for e in p.find_all(id=re.compile('commentary')):
        id_text = e['id']
        ugc_id = re.search(r'userGeneratedContentId=(\d+)', id_text)
        if ugc_id:
            return f'https://www.linkedin.com/feed/update/urn:li:ugcPost:{ugc_id.group(1)}/'
        share_id = re.search(r'shareId=(\d+)', id_text)
        if share_id:
            return f'https://www.linkedin.com/feed/update/urn:li:share:{share_id.group(1)}/'
    return ''

# Link from the control menu ("Diesen Beitrag einfügen" contains the urn)
def get_link_from_menu(post_elem):
    link = ''
    try:
        menu_button = post_elem.find_element(By.XPATH, ".//button[starts-with(@aria-label, 'Kontrollmenü')]")
        driver.execute_script('arguments[0].scrollIntoView({block:"center"})', menu_button)
        driver.execute_script('arguments[0].click()', menu_button)
        time.sleep(1.5)
        embed_links = driver.find_elements(By.XPATH, "//*[@role='menu']//a[contains(@href, 'targetUrn')]")
        if embed_links:
            urn = re.search(r'targetUrn=([^&]+)', embed_links[0].get_attribute('href'))
            if urn:
                link = 'https://www.linkedin.com/feed/update/' + urn.group(1).replace('%3A', ':') + '/'
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.5)
    except:
        pass
    return link

# The post id contains the exact publishing time (first 41 bits = milliseconds since 1970)
# This is more precise than the approximate date on the page (e.g. "11 Monat(e)")
def get_date_from_link(link):
    post_id = re.search(r':(\d{15,})/?$', str(link))
    if not post_id:
        return None
    try:
        post_dt = datetime.fromtimestamp((int(post_id.group(1)) >> 22) / 1000)
        return datetime(post_dt.year, post_dt.month, post_dt.day)
    except:
        return None

def get_count(p, label):
    button = p.find(lambda t: t.name == 'button' and str(t.get('aria-label', '')).startswith(label))
    if not button:
        return ''
    count = extract_text(button)
    if not count:
        return 0
    return extract_every_number(count)

def scrape_post(p, p_name):
    post_date_dt, post_date = find_post_date(p)
    post_text = get_visible_text(Comment, p)
    post_type = 'post'
    if 'repostet' in post_text or 'hat das geteilt' in post_text:
        post_type = 'repost'
    likes = get_count(p, 'Status des Reaktionsbuttons')
    comments = get_count(p, 'Kommentieren')
    shares = get_count(p, 'Reposten')

    content = ''
    content_elem = p.find(attrs={'data-testid': 'expandable-text-box'})
    if content_elem:
        content = extract_text(content_elem.get_text(' '))
    if len(str(content)) <= 4:
        content = post_text.replace('Feed-Beitrag', '', 1).strip()

    imagelinks = [e['src'] for e in p.find_all('img', src=True)
                  if not any(x in e['src'] for x in ['company-logo', 'profile-displayphoto', 'videocover'])]
    is_document = p.find(attrs={'aria-label': re.compile(r'Seite \d+ von \d+')})
    if p.find('video') or p.find(attrs={'aria-label': 'Video abspielen'}):
        video, image = 1,0
    elif len(imagelinks) >= 1 or is_document:
        image, video = 1,0
    else:
        image, video = 0,0
    link = get_link_from_id(p)
    content = content.replace('Hashtag # ','#')
    scraped_post = [post_date, post_type, likes, comments, shares, image, video, link, content]
    return post_date_dt, scraped_post

# Old layout: the counts are in aria-labels like "47 Reaktionen", "5 Kommentare zum Beitrag", "3 Reposts des Beitrags"
def get_count_old(aria_labels, pattern):
    for a in aria_labels:
        match = re.match(r'^\s*([\d.,]+(?:\s*(?:Tsd\.|Mio\.))?)\s+' + pattern, a)
        if match:
            return extract_every_number(match.group(1))
    return 0

def scrape_post_old(p, urn):
    post_date_dt, post_date = find_post_date(p)
    post_text = get_visible_text(Comment, p)
    header = p.select_one('.update-components-header')
    header_text = get_visible_text(Comment, header) if header else post_text[:300]
    post_type = 'post'
    if 'repostet' in header_text or 'hat das geteilt' in header_text:
        post_type = 'repost'
    aria_labels = [extract_text(e['aria-label']) for e in p.find_all(['button', 'a', 'span'], attrs={'aria-label': True})]
    aria_labels = [a for a in aria_labels if a]
    likes = get_count_old(aria_labels, 'Reaktion')
    comments = get_count_old(aria_labels, 'Kommentar')
    shares = get_count_old(aria_labels, 'Repost')

    content = ''
    content_elem = p.select_one('.update-components-text') or p.find('span', class_='break-words')
    if content_elem:
        content = extract_text(content_elem.get_text(' '))
    if len(str(content)) <= 4:
        content = post_text

    imagelinks = [e['src'] for e in p.find_all('img', src=True)
                  if not any(x in e['src'] for x in ['company-logo', 'profile-displayphoto', 'videocover'])]
    if p.find('video') or p.select_one('.update-components-linkedin-video'):
        video, image = 1,0
    elif len(imagelinks) >= 1 or p.select_one('.update-components-document__container, ul.carousel-track'):
        image, video = 1,0
    else:
        image, video = 0,0
    link = f'https://www.linkedin.com/feed/update/{urn}/'
    content = content.replace('Hashtag # ','#').replace('#Hashtag', '#')
    scraped_post = [post_date, post_type, likes, comments, shares, image, video, link, content]
    return post_date_dt, scraped_post

# Same filter rules for both layouts: exact date from the link, time period and duplicates
# Returns 'older' for posts before the time period, 'add' for new posts in the time period, otherwise 'skip'
def check_post(post_dt, postdata, upper_dt, lower_dt, distinct_content):
    exact_dt = get_date_from_link(postdata[7])
    if exact_dt:
        post_dt = exact_dt
        postdata[0] = exact_dt.strftime("%d.%m.%Y")
    if not post_dt or post_dt >= upper_dt:
        return 'skip'
    if post_dt < lower_dt:
        return 'older'
    key = postdata[7] or postdata[-1][:99] + postdata[-1][-100:]
    if key in distinct_content:
        return 'skip'
    distinct_content.append(key)
    return 'add'

def scrape_all_posts_new(ID, p_name, lower_dt, upper_dt, sorted_feed):
    data_per_company = []
    distinct_content = []
    id_p = 0
    n_done = 0
    n_older = 0
    while True:
        post_elems = driver.find_elements(By.XPATH, POST_XPATH)
        for post_elem in post_elems[n_done:]:
            p = BeautifulSoup(post_elem.get_attribute('outerHTML'), 'lxml')
            post_dt, postdata = scrape_post(p, p_name)
            if not postdata[7]:
                postdata[7] = get_link_from_menu(post_elem)
            result = check_post(post_dt, postdata, upper_dt, lower_dt, distinct_content)
            # Count the posts in a row, which are older than the time period (a pinned post may be old as well)
            if result == 'older':
                n_older += 1
                continue
            if result == 'skip':
                continue
            n_older = 0
            full_row = [ID, p_name, id_p, dt_str] + postdata
            print(full_row[:-1] + [str(full_row[-1])[:60]])
            data_per_company.append(full_row)
            id_p += 1
        n_done = len(post_elems)
        if sorted_feed and n_older >= 5:
            print('Reached the end of the time period')
            return data_per_company, n_done, True
        if not load_more_posts(n_done):
            print('No more new posts')
            break
    return data_per_company, n_done, False

# Old layout: read the rendered posts, which were not read yet, and mark them in the browser (data-crawled)
# Only the rendered posts are read (the whole page source gets very large for long feeds)
def read_rendered_posts_old():
    return driver.execute_script(
        "return [...document.querySelectorAll('div.occludable-update')].map(e => {"
        "  if (e.dataset.crawled || !e.querySelector('[data-urn]')) return null;"
        "  e.dataset.crawled = '1'; return e.outerHTML; }).filter(x => x);")

# Posts, which were scrolled past before they were rendered, are emptied again by LinkedIn.
# They are scrolled into view one by one and read afterwards.
def read_skipped_posts_old():
    post_htmls = []
    skipped = driver.execute_script(
        "return [...document.querySelectorAll('div.occludable-update')].map((e, i) => "
        "  [i, e.dataset.crawled, Number(e.dataset.tries || 0), e.getBoundingClientRect().bottom])"
        ".filter(x => !x[1] && x[2] < 2 && x[3] < 0).map(x => x[0]);")
    if not skipped:
        return post_htmls
    scroll_y = driver.execute_script('return window.scrollY')
    for i in skipped:
        driver.execute_script(
            "const e = document.querySelectorAll('div.occludable-update')[arguments[0]];"
            "e.dataset.tries = Number(e.dataset.tries || 0) + 1; e.scrollIntoView({block: 'center'});", i)
        time.sleep(1.2)
        post_htmls += read_rendered_posts_old()
    driver.execute_script('window.scrollTo(0, arguments[0])', scroll_y)
    time.sleep(1)
    return post_htmls

# Old layout: the page is scrolled step by step and the rendered posts are read after every step
def scrape_all_posts_old(ID, p_name, lower_dt, upper_dt, sorted_feed):
    data_per_company = []
    distinct_content = []
    seen_urns = set()
    id_p = 0
    n_older = 0
    bottom_tries = 0
    while bottom_tries < 3:
        post_htmls = read_skipped_posts_old() + read_rendered_posts_old()
        for post_html in post_htmls:
            p = BeautifulSoup(post_html, 'lxml')
            urn_elem = p.find(attrs={'data-urn': re.compile(r'urn:li:(activity|ugcPost|share):\d+')})
            if not urn_elem or urn_elem['data-urn'] in seen_urns:
                continue
            urn = urn_elem['data-urn']
            seen_urns.add(urn)
            post_dt, postdata = scrape_post_old(p, urn)
            result = check_post(post_dt, postdata, upper_dt, lower_dt, distinct_content)
            if result == 'older':
                n_older += 1
                continue
            if result == 'skip':
                continue
            n_older = 0
            full_row = [ID, p_name, id_p, dt_str] + postdata
            print(full_row[:-1] + [str(full_row[-1])[:60]])
            data_per_company.append(full_row)
            id_p += 1
        if sorted_feed and n_older >= 5:
            print('Reached the end of the time period')
            return data_per_company, len(seen_urns), True
        # Scroll one step further; at the end of the page wait for new posts (longer for long feeds)
        check_for_checkpoint()
        height = driver.execute_script('return document.body.scrollHeight')
        driver.execute_script('window.scrollBy(0, 1500);')
        time.sleep(random.uniform(1.5, 2.5))
        at_bottom = driver.execute_script('return window.scrollY + window.innerHeight >= document.body.scrollHeight - 50')
        if not at_bottom:
            bottom_tries = 0
            continue
        max_wait = min(8 + len(seen_urns) * 0.03, 40)
        t0 = time.time()
        loaded = False
        while time.time() - t0 < max_wait:
            if click_load_more_button():
                t0 = time.time()
            time.sleep(1)
            if driver.execute_script('return document.body.scrollHeight') > height + 100:
                loaded = True
                break
        if loaded:
            bottom_tries = 0
        else:
            bottom_tries += 1
            driver.execute_script('window.scrollBy(0, -1500);')
            time.sleep(1)
    # Last check for skipped posts at the end of the feed
    for post_html in read_skipped_posts_old() + read_rendered_posts_old():
        p = BeautifulSoup(post_html, 'lxml')
        urn_elem = p.find(attrs={'data-urn': re.compile(r'urn:li:(activity|ugcPost|share):\d+')})
        if not urn_elem or urn_elem['data-urn'] in seen_urns:
            continue
        seen_urns.add(urn_elem['data-urn'])
        post_dt, postdata = scrape_post_old(p, urn_elem['data-urn'])
        if check_post(post_dt, postdata, upper_dt, lower_dt, distinct_content) == 'add':
            full_row = [ID, p_name, id_p, dt_str] + postdata
            print(full_row[:-1] + [str(full_row[-1])[:60]])
            data_per_company.append(full_row)
            id_p += 1
    print('No more new posts')
    return data_per_company, len(seen_urns), False

# For very active accounts LinkedIn stops loading the feed after about 400 posts, so only a part of the time period
# can be crawled. Then dummy posts with the average values and without content are added, so that the number of posts
# is extrapolated to the whole time period. The dummy posts are spread evenly over the missing time span.
def add_dummy_posts(data_per_company, ID, p_name, lower_dt, upper_dt):
    if not data_per_company:
        return data_per_company
    dates = [datetime.strptime(r[4], "%d.%m.%Y") for r in data_per_company]
    oldest_dt = min(dates)
    covered_days = (upper_dt - oldest_dt).days
    total_days = (upper_dt - lower_dt).days
    if covered_days <= 0 or covered_days >= total_days - 14:
        return data_per_company
    n_posts = len(data_per_company)
    n_dummies = round(n_posts * total_days / covered_days) - n_posts
    if n_dummies <= 0:
        return data_per_company
    def mean_of(col):
        values = [r[col] for r in data_per_company if isinstance(r[col], (int, float))]
        return round(sum(values) / len(values)) if values else 0
    likes, comments, shares = mean_of(6), mean_of(7), mean_of(8)
    # Same share of images and videos as in the crawled posts
    n_images = round(sum(r[9] for r in data_per_company) / n_posts * n_dummies)
    n_videos = round(sum(r[10] for r in data_per_company) / n_posts * n_dummies)
    missing_days = (oldest_dt - lower_dt).days
    id_p = n_posts
    for i in range(n_dummies):
        dummy_dt = lower_dt + timedelta(days=missing_days * (i + 0.5) / n_dummies)
        image = 1 if i < n_images else 0
        video = 1 if n_images <= i < n_images + n_videos else 0
        dummy = [ID, p_name, id_p, dt_str, dummy_dt.strftime("%d.%m.%Y"), 'dummy', likes, comments, shares,
                 image, video, '', '']
        data_per_company.append(dummy)
        id_p += 1
    print(f'{n_dummies} dummy posts added ({n_posts} crawled posts since {oldest_dt.strftime("%d.%m.%Y")})')
    return data_per_company

def scrape_all_posts(ID, p_name, lower_dt, upper_datelimit):
    upper_dt = datetime.strptime(upper_datelimit, '%Y-%m-%d')
    # Only a feed sorted by date can be stopped at the end of the time period, otherwise it is scrolled to the end
    sorted_feed = sort_by_newest()
    if not sorted_feed:
        print('Feed not sorted by date, all posts are loaded')
    if is_old_layout():
        data_per_company, n_loaded, reached_end = scrape_all_posts_old(ID, p_name, lower_dt, upper_dt, sorted_feed)
    else:
        data_per_company, n_loaded, reached_end = scrape_all_posts_new(ID, p_name, lower_dt, upper_dt, sorted_feed)
    # The feed limit was reached before the beginning of the time period
    if not reached_end and n_loaded >= FEED_LIMIT:
        data_per_company = add_dummy_posts(data_per_company, ID, p_name, lower_dt, upper_dt)
    return data_per_company
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    file = None
    os.chdir(path_to_crawler_functions)
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
    try:
        login(useremail_li, password_li, driver)
        input('Press ENTER after the page is loaded')
    except:
        input('Press ENTER after manual login')

    start_ID = 0
    # Iterate over the companies
    for ID, row in df_source.iterrows():
        start, ID, p_name = start_at(df_source, ID, row, start_ID)
        if not start:
            continue
        try:
            go_crawl = check_conditions(ID, p_name, row, lower_dt)
        except RuntimeError as e:
            print(e)
            break
        except Exception as e:
            print(f"Error: {e}")
            driver.quit()
            time.sleep(5)
            driver = start_browser(webdriver, Service, chromedriver_path, headless=False, muted=True)
            go_to_page(driver, startpage)
            try:
                login(useremail_li, password_li, driver)
                input('Press ENTER after the page is loaded')
            except:
                input('Press ENTER after manual login')
            go_crawl = check_conditions(ID, p_name, row, lower_dt)
        if not go_crawl:
            continue

        data_per_company = scrape_all_posts(ID, p_name, lower_dt, upper_datelimit)
        all_data += data_per_company

#        start_ID = ID + 1
        # Create a DataFrame with all posts
        header1 = ['ID_A', 'Profilname', 'ID_P', 'Erhebung', 'Datum']
        header2 = ['post_type', 'Likes', 'Kommentare', 'Shares', 'Bild', 'Video', 'Link', 'Content']
        dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

        # Export dfPosts to Excel (with the current time)
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_' + platform + '_' + dt_str_now + '.xlsx'
        dfPosts.to_excel(file_name)

    driver.quit()
