
import os
import sys
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

folder_name = "SMP_Rüstungsunternehmen_2026"
file_name = "Auswahl_1_Rüstungsunternehmen_2026_20261001"
upper_datelimit = '2026-10-01'
file_path = r"C:\Users\andre\OneDrive\Desktop/" + folder_name
source_file = file_name + ".xlsx"

sys.path.insert(0, path_to_crawler_functions)
from crawler_functions import *

########################################################################################################################
# Since 2026 LinkedIn delivers the company pages with hashed css classes (e.g. 'b4la49 b4lguo'), which change
# regularly. Therefore the elements are found via the page structure and fixed texts instead of class names.

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

# Build the clean start page url (https://www.linkedin.com/company/<name>/) from every kind of LinkedIn link
def clean_url(url):
    match = re.search(r'linkedin\.com/(company|school|showcase)/([^/?#]+)', str(url))
    if not match:
        return None
    return f'https://www.linkedin.com/{match.group(1)}/{match.group(2)}/'

def wait_for_page(driver, xpath, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
    except:
        pass
    time.sleep(1)

# Old layout: top card with fixed class names
def get_profile_info_old(soup):
    p_name = extract_text(soup.select_one('.org-top-card-summary__title'))
    tagline = extract_text(soup.select_one('.org-top-card-summary__tagline'))
    follower, employees = '', ''
    info_list = soup.select_one('.org-top-card-summary-info-list')
    info_parts = []
    if info_list:
        info_parts = [extract_text(e) for e in info_list.select('.org-top-card-summary-info-list__info-item')]
        if not info_parts:
            info_parts = [extract_text(info_list)]
    for i in info_parts:
        if 'Follower' in i:
            follower = extract_every_number(i.split('Follower')[0])
        if 'Beschäftigte' in i:
            employees = i.replace('Beschäftigte', '').strip()
    desc1 = ' '.join([i for i in info_parts if i])
    return p_name or '', follower, employees, desc1, tagline or ''

# Top card on the start page: h2 (name), p (tagline), info row (industry · location · follower · employees)
def get_profile_info(soup, company):
    p_name, follower, employees, desc1, tagline = ['' for _ in range(5)]
    if soup.select_one('.org-top-card-summary__title'):
        p_name, follower, employees, desc1, tagline = get_profile_info_old(soup)
        if p_name and desc1:
            return p_name, follower, employees, desc1, tagline
    follower_elem = soup.find(lambda t: t.name == 'p' and 'Follower' in t.get_text())
    if follower_elem:
        follower = extract_every_number(extract_text(follower_elem).split('Follower')[0])
        info_row = follower_elem.parent
        info_parts = [extract_text(p) for p in info_row.find_all('p')]
        info_parts = [i for i in info_parts if i and i != '·']
        desc1 = ' '.join(info_parts)
        for i in info_parts:
            if 'Beschäftigte' in i:
                employees = i.replace('Beschäftigte', '').strip()
        top_card = info_row
        for _ in range(6):
            top_card = top_card.parent
            if not top_card or top_card.find('h2'):
                break
        if top_card:
            p_name = extract_text(top_card.find('h2'))
            tagline_parts = [extract_text(p.get_text(' ')) for p in top_card.find_all('p') if not info_row in p.parents]
            tagline = ' '.join([t for t in tagline_parts if t and t != p_name])
    if not p_name:
        names = [extract_text(h) for h in soup.find_all(['h1', 'h2'])]
        sel_names = [n for n in names if n and company[:4].strip().lower() in n.lower()]
        if sel_names:
            p_name = sel_names[0]
    if not p_name and soup.title:
        title = re.sub(r'^\(\d+\)\s*', '', extract_text(soup.title))
        p_name = title.rsplit(':', 1)[0].strip() if ':' in title else ''
    return p_name, follower, employees, desc1, tagline

# Full description with details (website, industry, size, specialties ...) in the section "Übersicht" on /about
def get_about_description(soup):
    overview = soup.find(lambda t: t.name == 'h2' and extract_text(t) == 'Übersicht')
    if not overview:
        return ''
    about_parts = []
    # Old layout: description (p) and details (dt/dd) in a section, until the next h3 outside of the details
    section = overview.find_parent('section')
    if section and section.find('dl'):
        for e in section.find_all(['p', 'dt', 'dd', 'h3']):
            if e.name == 'h3':
                if e.find_parent('dt'):
                    continue
                break
            if e.name == 'p' and (e.find_parent('dt') or e.find_parent('dd')):
                continue
            about_parts.append(extract_text(e.get_text(' ')))
        return ' '.join([a for a in about_parts if a])
    for e in overview.find_all_next(['p', 'h2']):
        if e.name == 'h2':
            break
        about_parts.append(extract_text(e.get_text(' ')))
    return ' '.join([a for a in about_parts if a])

# Short description in the section "Übersicht" on the start page (fallback, if /about is not available)
def get_description(soup, pagetext):
    desc2 = ''
    overview = soup.find(lambda t: t.name == 'h2' and extract_text(t) == 'Übersicht')
    if overview:
        section = overview
        for _ in range(5):
            section = section.parent
            if not section:
                break
            text_box = section.find(attrs={'data-testid': 'expandable-text-box'})
            if text_box:
                desc2 = extract_text(text_box.get_text(' '))
                break
            section_text = extract_text(section)
            if len(section_text) > len('Übersicht') + 4:
                desc2 = section_text.split('Übersicht', 1)[-1].replace('Alle anzeigen', '').strip()
                break
    if len(desc2) <= 4:
        desc2 = pagetext
        if 'Übersicht' in desc2:
            desc2 = desc2.split('Übersicht', 1)[1].strip()
    return desc2

# LinkedIn delivers two layouts depending on the login session:
# new layout: div[role=listitem] with the hidden headline "Feed-Beitrag", old layout: div.occludable-update
POST_XPATH = "//h2[normalize-space()='Feed-Beitrag']/ancestor::div[@role='listitem'][1]"
OLD_POST_XPATH = "//div[contains(@class, 'occludable-update')]"

def is_old_layout():
    return bool(driver.find_elements(By.CSS_SELECTOR, 'div.occludable-update, #sort-dropdown-trigger'))

# Old layout: dropdown "Sortieren nach: Relevanteste" -> "Aktuellste"
def sort_by_newest_old():
    try:
        trigger = driver.find_element(By.ID, 'sort-dropdown-trigger')
        if 'Aktuellste' in trigger.text:
            return True
        driver.execute_script('arguments[0].scrollIntoView({block:"center"})', trigger)
        trigger.click()
        time.sleep(1.5)
        options = [o for o in driver.find_elements(By.XPATH, "//button[@role='option'][normalize-space(.)='Aktuellste']")
                   if o.is_displayed()]
        if options:
            options[0].click()
            time.sleep(4)
        return 'Aktuellste' in driver.find_element(By.ID, 'sort-dropdown-trigger').text
    except:
        return False

# Switch the feed from "Beliebteste" to "Aktuell" (= Neueste)
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
        wait_for_page(driver, POST_XPATH)
    return sorted_feed

# Every post container is a div[role=listitem] with the hidden headline "Feed-Beitrag"
def get_posts(soup):
    posts = []
    for h in soup.find_all('h2'):
        if extract_text(h) != 'Feed-Beitrag':
            continue
        post = h.find_parent(attrs={'role': 'listitem'})
        if post and post not in posts:
            posts.append(post)
    # Old layout: only rendered posts contain the urn (posts outside the visible area are emptied)
    for post in soup.find_all('div', class_='occludable-update'):
        if post.find(attrs={'data-urn': re.compile(r'urn:li:(activity|ugcPost|share):\d+')}):
            posts.append(post)
    return posts

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

# Pages with many followers only show a rounded number on the start page (e.g. "2,1 Mio. Follower:innen")
# Old layout: the exact number is part of the post header ("2.128.666 Follower:innen")
# New layout: the exact number is shown in the hover card of the company logo in a post
def get_exact_follower_from_post(soup):
    for e in soup.select('.update-components-actor__description'):
        e_text = extract_text(e)
        if 'Follower' in e_text and not any(r in e_text for r in ['Tsd.', 'Mio.']):
            return extract_every_number(e_text.split('Follower')[0])
    from selenium.webdriver.common.action_chains import ActionChains
    for post in driver.find_elements(By.XPATH, POST_XPATH)[:3]:
        try:
            logo = post.find_element(By.XPATH, ".//a[@aria-haspopup='dialog']")
            driver.execute_script('arguments[0].scrollIntoView({block:"center"})', logo)
            time.sleep(1.5)
            ActionChains(driver).move_to_element(logo).perform()
            t0 = time.time()
            while time.time() - t0 < 6:
                time.sleep(1)
                for dialog in driver.find_elements(By.XPATH, "//*[@role='dialog']"):
                    if not dialog.is_displayed():
                        continue
                    for line in dialog.text.split('\n'):
                        if 'Follower' in line and not any(r in line for r in ['Tsd.', 'Mio.']):
                            return extract_every_number(line.split('Follower')[0])
            # Move the mouse away, so the next hover card can open
            ActionChains(driver).move_by_offset(0, 300).perform()
        except:
            pass
    return None

# The post id in the id of the text block contains the exact publishing time (first 41 bits = milliseconds since 1970)
# e.g. "...UserGeneratedContentPostUrn(userGeneratedContentId=7510705806120517632)" or "...shareId=7511780785352544256"
# Old layout: data-urn="urn:li:activity:7509292695576834048"
def get_exact_post_date(p):
    id_texts = [e['id'] for e in p.find_all(id=re.compile('commentary'))]
    id_texts += ['id=' + e['data-urn'].rsplit(':', 1)[-1] for e in p.find_all(attrs={'data-urn': re.compile(r'urn:li:\w+:\d+')})]
    for id_text in id_texts:
        post_id = re.search(r'(?:userGeneratedContentId|shareId|id)=(\d{15,})', id_text)
        if post_id:
            try:
                post_dt = datetime.fromtimestamp((int(post_id.group(1)) >> 22) / 1000)
                post_dt = datetime(post_dt.year, post_dt.month, post_dt.day)
                return post_dt, post_dt.strftime("%d.%m.%Y")
            except:
                pass
    return None


def scrapeProfile(company, link):
    p_name, follower, employees, last_post, desc1, desc2, tagline = ['' for _ in range(7)]
    new_url = clean_url(link)
    driver.get(new_url or link)
    wait_for_page(driver, "//*[contains(text(), 'Follower')]")
    # Links with IDs or subpages get redirected, so the url is cleaned again
    if clean_url(driver.current_url) and clean_url(driver.current_url) != new_url:
        new_url = clean_url(driver.current_url)
        driver.get(new_url)
        wait_for_page(driver, "//*[contains(text(), 'Follower')]")
    if not new_url:
        new_url = driver.current_url
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    not_used = 'wurde noch nicht in Anspruch genommen'
    if not_used in pagetext:
        return ['Seite ' + not_used, follower, employees, last_post, new_url, tagline, desc1, desc2]

    p_name, follower, employees, desc1, tagline = get_profile_info(soup, company)
    desc2 = get_description(soup, pagetext)

    # The complete description is only available on the subpage /about
    try:
        driver.get(new_url + 'about/')
        wait_for_page(driver, "//h2[contains(., 'Übersicht')]")
        about_desc = get_about_description(BeautifulSoup(driver.page_source, 'lxml'))
        if len(about_desc) > 4:
            desc2 = about_desc
    except:
        pass

    try:
        driver.get(new_url + 'posts/?feedView=all')
        wait_for_page(driver, "//h2[contains(., 'Feed-Beitrag')] | " + OLD_POST_XPATH +
                      " | //*[contains(text(), 'Noch keine Beiträge')]")
        # The feed is sorted by "Beliebteste", so the first post is not always the latest one
        if driver.find_elements(By.XPATH, POST_XPATH + ' | ' + OLD_POST_XPATH):
            sort_by_newest()
            # Load some more posts (new layout: the feed scrolls inside main#workspace)
            if not is_old_layout():
                driver.execute_script("const m = document.querySelector('main#workspace') || document.scrollingElement;"
                                      "m.scrollTop = m.scrollHeight;")
                time.sleep(3)
    except:
        return [p_name, follower, employees, last_post, new_url, tagline, desc1, desc2]
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = str(get_visible_text(Comment, soup))
    posts = get_posts(soup)
    if len(posts) == 0 or not 'posts/?' in driver.current_url or "Noch keine Beiträge" in pagetext:
        last_post = 'Keine Beiträge'
        return [p_name, follower, employees, last_post, new_url, tagline, desc1, desc2]

    if any(r + ' Follower' in str(desc1) for r in ['Tsd.', 'Mio.']):
        exact_follower = get_exact_follower_from_post(soup)
        if exact_follower:
            follower = exact_follower

    post_dates = [get_exact_post_date(p) or find_post_date(p) for p in posts]
    post_dates = [d for d in post_dates if d[0]]
    if not post_dates:
        last_post = 'Keine Beiträge'
        return [p_name, follower, employees, last_post, new_url, tagline, desc1, desc2]
    post_date_dt, last_post = max(post_dates, key=lambda d: d[0])

    return [p_name, follower, employees, last_post, new_url, tagline, desc1, desc2]
########################################################################################################################

# Profile crawler
if __name__ == '__main__':
    # Settings for profile scraping
    os.chdir(path_to_crawler_functions)
    try:
        from credentials_file import *
    except:
        useremail_li = str(input('Enter your user-email:')).strip()
        password_li = str(input('Enter your password:')).strip()
    os.chdir(file_path)
    df_source, col_list, comp_header, name_header, dt, dt_str = settings(source_file)
    col_list = list(df_source.columns)

    # Open the browser, go to the startpage and login
    data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    try:
        login(useremail_li, password_li, driver)
        input('Press ENTER after the page is loaded')
    except:
        input('Press ENTER after manual login')

    start_ID = 0
    # Loop through the profiles
    for ID, row in df_source.iterrows():
        if 'ID' in col_list and col_list[0] != 'ID':
            ID = int(row['ID'])
        if not 'nan' in str(ID):
            ID = int(ID)
        if not str(ID).isdigit():
            break
        if ID < start_ID:  # If you want to skip some rows
            continue

        company = extract_text(row[name_header])
        link = str(row[platform])
        if len(link) < 10:
            empty_row = [ID, company, dt_str] + ['' for _ in range(8)]
            data.append(empty_row)
            print(empty_row)
            continue
        try:
            scraped_row = scrapeProfile(company, link)
        except Exception as e:
            print(f"Error: {e}")
            driver.quit()
            time.sleep(3)
            driver = start_browser(webdriver, Service, chromedriver_path)
            go_to_page(driver, startpage)
            try:
                login(useremail_li, password_li, driver)
                input('Press ENTER after the page is loaded')
            except:
                input('Press ENTER after manual login')
            scraped_row = scrapeProfile(company, link)

        data.append([ID, company, dt_str] + scraped_row)
#        start_ID = ID + 1
        print([ID, company, dt_str] + scraped_row)


    # Create a DataFrame
    header = ['ID', 'company', 'date', 'profile_name', 'follower', 'employees', 'last_post', 'url', 'tagline',
              'description1', 'description2']
    df_profiles = pd.DataFrame(data, columns=header)

    # Export to Excel
    dt_str_now = datetime.now().strftime("%Y-%m-%d")
    recent_filename = 'Profile_' + platform + '_' + dt_str_now + '.xlsx'
    df_profiles.to_excel(recent_filename)

    driver.quit()
