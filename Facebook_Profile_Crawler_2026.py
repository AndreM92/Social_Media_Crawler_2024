
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
startpage = 'https://www.facebook.com/'
platform = 'Facebook'

folder_name = "SMP_Rüstungsunternehmen_2026"
file_name = "Auswahl_1_Rüstungsunternehmen_2026"
upper_datelimit = '2026-10-01'
file_path = r"C:\Users\andre\OneDrive\Desktop/" + folder_name
source_file = file_name + ".xlsx"

sys.path.insert(0, path_to_crawler_functions)
from crawler_functions import *

########################################################################################################################
# Facebook Login function
def login(useremail, password, driver, pyautogui):
    try:
        nameslot = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']")))
        nameslot.clear()
        for char in useremail:
            time.sleep(0.1)
            nameslot.send_keys(char)
        pwslot = driver.find_element(By.CSS_SELECTOR, "input[name='pass']")
        pwslot.clear()
        for char in password:
            pwslot.send_keys(char)
            time.sleep(.1)
        driver.find_element(By.CSS_SELECTOR, "[aria-label='Anmelden'][role='button']").click()
        time.sleep(3)
    except:
        input('log in manually')
    if '/auth_platform' in driver.current_url:
        input('Press ENTER after 2FA')
    if "_verification" in driver.current_url:
        input('Press ENTER after manual login')
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

########################################################################################################################
# Parsing helpers
# Facebook does not render the profile name in an <h1> anymore (change in 2026) and hides the dates of the posts
# behind shuffled, partly invisible single-character spans. The helpers below read the data from the parts of the
# page that are still stable: the header block "<name> <n> Follower", the link to the follower list and the CSS
# order values of the date spans.
FOLLOWER_RE = re.compile(
    r'([0-9][0-9.,\s ]*(?:Mio\.?|Mrd\.?|Tsd\.?|[KMB])?)\s*'
    r'(?:Follower|Followers|Abonnenten|Abonnent:innen)\b', re.IGNORECASE)
LIKE_RES = [
    re.compile(r'Gefällt\s+([0-9][0-9.,\s ]*(?:Mio\.?|Tsd\.?)?)\s*Mal', re.IGNORECASE),
    re.compile(r'([0-9][0-9.,\s ]*(?:Mio\.?|Tsd\.?)?)\s*[„"]?Gefällt\s*mir[“"]?\s*[-‑]?Angaben',
               re.IGNORECASE),
    re.compile(r'([0-9][0-9.,\s ]*(?:Mio\.?|Tsd\.?)?)\s*Personen\s+gefällt\s+das', re.IGNORECASE),
    re.compile(r'([0-9][0-9.,\s ]*[KMB]?)\s*(?:people\s+like\s+this|likes)\b', re.IGNORECASE),
]
# Navigation bar of a profile page: "Mehr Alle Info Reels Fotos Follower Mehr"
NAV_RE = re.compile(r'\bMehr\s+(?:Alle\s+)?(?:Info|Beiträge|Reels|Fotos|Videos|Mentions)[^|]{0,90}?\bMehr\b')
NAME_JUNK = ('Bestätigtes Konto', 'Verifiziertes Konto', 'Verified account')
DESC_CUTS = ('Beiträge Filter', 'Fotos Alle Fotos', 'Alle Fotos ansehen', 'Informationen zu Daten',
             'Featured', 'Beiträge')
BUTTON_WORDS = ('Folgen', 'Suchen', 'Nachricht senden', 'Mehr dazu', 'Kontaktiere uns', 'Jetzt kaufen',
                'Jetzt ansehen', 'Gefolgt', 'Abonnieren', 'Anrufen', 'Mehr ansehen')
SECTION_HEADERS = ('Details', 'Links', 'Kontaktinformationen', 'Fotos', 'Beiträge', 'Featured', 'Videos',
                   'Reels', 'Info')
STATS_CLASS = 'x9f619 x1n2onr6 x1ja2u2z x78zum5 xdt5ytf x2lah0s x193iq5w x1cy8zhl xyamay9 x1614ocl'

# Dates of the posts, e.g. "5. Februar", "4. Oktober 2025", "25. August um 02:01", "4 Tage"
MONTHS_GER = {'jan': 1, 'feb': 2, 'mär': 3, 'apr': 4, 'mai': 5, 'jun': 6, 'jul': 7,
              'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dez': 12}
DATE_RE = re.compile(
    r'(?:(\d{1,2})\.\s*)?\b(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|'
    r'Dezember|Jan|Feb|Mär|Apr|Jun|Jul|Aug|Sep|Okt|Nov|Dez)\b\.?\s*(20\d{2})?', re.IGNORECASE)
REL_DATE_RE = re.compile(r'(\d{1,3})\s*(Wochen|Woche|Wo\.|Tagen|Tage|Tag|Std\.|Stunden|Stunde|Min\.|'
                         r'Minuten|Sek\.|Sekunden)', re.IGNORECASE)
# Profiles without any post. In that case there is no date of a last post.
NO_POSTS = ('Keine Beiträge verfügbar', 'Keine Beiträge vorhanden', 'Keine Beiträge zum Anzeigen',
            'Keine Beiträge', 'No posts available', 'No posts yet', 'No posts to show')
# The feed of the posts starts below this headline. Everything above it (the menu of the notifications
# with its own dates, the intro column) must not be taken for the date of the last post.
POST_MARKERS = ('Beiträge Filter', 'Mehr Beiträge', 'Beiträge')


def get_main_text(soup):
    main = soup.find(attrs={'role': 'main'}) or soup
    return extract_text(main.get_text(' ', strip=True)) or ''


def clean_name(name):
    name = extract_text(name) or ''
    for junk in NAME_JUNK:
        name = name.replace(junk, ' ')
    name = re.sub(r'Anzahl der ungelesenen Benachrichtigungen\s*\d*', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip(' ·•|,-')


def get_p_name(driver, comp_keywords, soup=None, p_name=''):
    if soup is None:
        soup = BeautifulSoup(driver.page_source, 'lxml')
    main_text = get_main_text(soup)
    headers = [h.text for h in driver.find_elements(By.XPATH, '//h1') if h.text]
    if 'Suchergebnisse' in headers:
        return None
    # 1) Header block of the profile: "<name> [Bestätigtes Konto] 1.234 Follower ..."
    match = FOLLOWER_RE.search(main_text[:300])
    if match:
        p_name = clean_name(main_text[:match.start()])
    # 2) Old layout with an <h1>
    if len(str(p_name)) <= 2 and len(headers) >= 1:
        p_list = [h for h in headers if any(part in h.lower() for part in comp_keywords)]
        if len(p_list) == 0:
            p_list = [h for h in headers
                      if len(h) >= 3 and 'neu' not in h.lower() and 'benachrichtigung' not in h.lower()]
        if len(p_list) >= 1:
            p_name = clean_name(p_list[0])
    # 3) Headlines of the posts, they carry the name of the author
    if len(str(p_name)) <= 2:
        headers2 = [h.text for h in driver.find_elements(By.XPATH, '//h2') if h.text]
        p_list = [h for h in headers2 if any(part in h.lower() for part in comp_keywords)]
        if len(p_list) == 0:
            p_list = [h for h in headers2 if len(h) >= 3 and h.strip() not in SECTION_HEADERS]
        if len(p_list) >= 1:
            p_name = clean_name(p_list[0].split(' hat ')[0].split(' ist hier')[0].split(' teilt')[0])
    # 4) Last resort: the name in the title of the page
    if len(str(p_name)) <= 2:
        title = extract_text(driver.title).replace('| Facebook', '').replace('Facebook', '').strip()
        if len(title) >= 3:
            p_name = clean_name(title)
    return p_name


def get_stats(driver, soup, main_text):
    pagelikes, follower = '', ''
    stats_text = ''
    # 1) The link to the list of followers carries the number of followers
    for a in soup.select("a[href*='followers'], a[href*='sk=followers']"):
        link_text = extract_text(a) or ''
        if any(c.isdigit() for c in link_text):
            stats_text = link_text
            break
    # 2) Old stats container below the profile name
    if not stats_text:
        stats_text = extract_text(soup.find('div', class_=STATS_CLASS)) or ''
    # 3) Header text of the profile
    if not stats_text:
        stats_text = main_text[:300]
    for e in str(stats_text).split('•'):
        if 'gefällt' in e.lower():
            pagelikes = extract_every_number(e)
        elif 'follower' in e.lower() or 'abonnent' in e.lower():
            match = FOLLOWER_RE.search(e)
            follower = extract_every_number(match.group(1).strip() if match else e)
    if follower == '':
        match = FOLLOWER_RE.search(stats_text) or FOLLOWER_RE.search(main_text[:300])
        if match:
            follower = extract_every_number(match.group(1).strip())
    if pagelikes == '':
        for rx in LIKE_RES:
            match = rx.search(main_text[:1500])
            if match:
                pagelikes = extract_every_number(match.group(1).strip())
                break
    return pagelikes, follower


def get_tagline(main_text):
    # Short self description between the buttons and the navigation bar of the profile
    nav = NAV_RE.search(main_text)
    if not nav:
        return ''
    head = main_text[:nav.start()]
    follower_match = FOLLOWER_RE.search(head)
    if follower_match:
        head = head[follower_match.end():]
    for btn in BUTTON_WORDS:
        if btn in head:
            head = head.rsplit(btn, 1)[1]
    return extract_text(head) or ''


def get_description(main_text):
    # Intro column of the profile ("Details", address, links, contact information)
    text = main_text
    for nav in NAV_RE.finditer(main_text):
        text = main_text[nav.end():]
    for cut in DESC_CUTS:
        if cut in text:
            text = text.split(cut)[0]
    if 'Details' in text:
        text = text.split('Details', 1)[1]
    description = extract_text(text.replace('Steckbrief', '').replace('Intro', '')) or ''
    tagline = get_tagline(main_text)
    if tagline and tagline.lower() not in description.lower():
        description = (tagline + ' ' + description).strip()
    return extract_text(description) or ''


def check_date(date_str):
    try:
        date_dt = datetime.strptime(date_str, '%d.%m.%Y')
    except:
        return ''
    if datetime.now() < date_dt:
        return ''
    return date_str


def parse_dates(date_text):
    # Collects every date of a post that is written out in the text ("5. Februar", "4. Oktober 2025")
    # and every relative date ("4 Tage", "3 Std.")
    dates = []
    now = datetime.now()
    for m in DATE_RE.finditer(date_text):
        month = MONTHS_GER.get(str(m.group(2))[:3].lower())
        if not month:
            continue
        day = int(m.group(1)) if m.group(1) else 1
        year = int(m.group(3)) if m.group(3) else now.year
        try:
            date_dt = datetime(year, month, day)
        except:
            continue
        # Facebook only leaves out the year for posts of the current year
        if date_dt > now and not m.group(3):
            try:
                date_dt = datetime(year - 1, month, day)
            except:
                continue
        if date_dt <= now:
            dates.append(date_dt)
    for m in REL_DATE_RE.finditer(date_text):
        unit = str(m.group(2)).lower()
        number = int(m.group(1))
        if unit.startswith('wo'):
            dates.append(now - timedelta(weeks=number))
        elif unit.startswith('tag'):
            dates.append(now - timedelta(days=number))
        else:
            dates.append(now)
    if 'gestern' in date_text.lower():
        dates.append(now - timedelta(days=1))
    if 'gerade eben' in date_text.lower():
        dates.append(now)
    return dates


def date_hint(date_text):
    # The most recent date of the given text, that is the date of the latest post
    dates = parse_dates(date_text)
    if not dates:
        return ''
    return check_date(max(dates).strftime('%d.%m.%Y'))


def get_post_text(pagetext):
    # Only the feed of the posts, the parts of the page above it carry dates of their own
    for marker in POST_MARKERS:
        if marker in pagetext:
            return pagetext.split(marker, 1)[1].strip()
    return pagetext.rsplit('Facebook')[-1].strip()


def get_last_post(driver, pagetext, p_name, take_screenshot):
    post_text = get_post_text(pagetext)
    # 1) The profile has not published any post, so there is no date of a last post
    if any(marker.lower() in post_text.lower() for marker in NO_POSTS):
        return ''
    # 2) Dates that are written out in the text of the page. Facebook shuffles the dates in the header of a
    # post, but the dates of the linked posts below the feed are still readable.
    last_post = date_hint(post_text)
    # 3) Read the dates from a screenshot
    if not last_post and take_screenshot:
        last_post = date_hint(get_text_from_screenshot(driver, p_name))
    return last_post


def scrapeProfile(url, take_screenshot, driver=None, comp_keywords=None):
    if driver is None:
        driver = globals()['driver']
    if comp_keywords is None:
        comp_keywords = globals().get('comp_keywords', [])
    p_name, pagelikes, follower, last_post, description = ['' for _ in range(5)]
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    if ('gelöscht' in pagetext and 'nicht verfügbar' in pagetext) and len(pagetext) <= 500 or len(pagetext) <= 200:
        p_name = 'page not available'
        return [p_name, pagelikes, follower, '', url, pagetext]
    upper_posts = soup.find_all('div', class_='x1c4vz4f x2lah0s xeuugli x1bhewko xq8finb xnqqybz')
    if len(upper_posts) >= 1:
        driver.execute_script("window.scrollBy(0, 1000);")
    else:
        driver.execute_script("window.scrollBy(0, 300);")
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = get_visible_text(Comment, soup)
    main_text = get_main_text(soup)
    p_name = get_p_name(driver, comp_keywords, soup)
    if len(str(p_name)) <= 2:
        return [p_name, pagelikes, follower, '', url, pagetext]
    pagelikes, follower = get_stats(driver, soup, main_text)
    last_post = get_last_post(driver, pagetext, p_name, take_screenshot)
    description = get_description(main_text)
    if len(description) <= 5:
        description = extract_text(pagetext)
    if 'Fotos Alle Fotos' in description:
        description = description.rsplit('Fotos Alle Fotos', 1)[0]
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