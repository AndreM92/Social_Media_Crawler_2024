
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
startpage = 'https://www.instagram.com/'
platform = 'Instagram'
dt_str_now = None

upper_datelimit = '2025-08-01'
file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_Automatisierungstechnik 2025'
file_name = 'Auswahl_SMP Automatisierungstechnik 2025_2025-08-06'
file_type = '.xlsx'
source_file = file_path + '/' + file_name + file_type
branch_keywords = ['Automatisierung', 'System', 'Technik', 'Maschine', 'Industrie', 'Automation', 'Technologie',
                   'Technology', 'Roboter', 'Steuerung', 'technik']
########################################################################################################################

def remove_insta_cookies():
    cookiebuttons = driver.find_elements('xpath', "//*[contains(text(), 'Jetzt nicht') or contains(text(), 'jetzt nicht')]")
    if len(cookiebuttons) >= 1:
        for c in cookiebuttons:
            try:
                c.click()
            except:
                pass

# Login function
def login(username, password):
    WebDriverWait(driver,5).until(EC.presence_of_element_located((By.XPATH,'//*[@id="loginForm"]/div/div[1]/div/label/input')))
    try:
        nameslot = driver.find_element(By.CSS_SELECTOR,'input[aria-label*="Benutzername"]')
    except:
        nameslot = driver.find_element('xpath', '//*[@id="loginForm"]/div/div[1]/div/label/input')
    pwslot = driver.find_element(By.CSS_SELECTOR,'input[aria-label*="Passwort"]')
    nameslot.clear()
    # Typing char for char to simulate a human like behavior
    # classic and global version:
    # nameslot.send_keys(cred.username_insta)
    for char in username:
        nameslot.send_keys(char)
        time.sleep(.1)
    pwslot.clear()
    for char in password:
        pwslot.send_keys(char)
        time.sleep(.1)
    driver.find_element('xpath', "//*[text()='Anmelden']").click()
    for _ in range(7):
        time.sleep(2)
        remove_insta_cookies()


# post_crawler functions
def clickOnFirst(startlink):
    posts = driver.find_elements(By.CLASS_NAME, '_aagw')
    try:
        posts[0].click()
        time.sleep(3)
    except:
        pass
    if not '/p/' in driver.current_url:
        driver.get(startlink)
        time.sleep(2)
        posts = driver.find_elements(By.CLASS_NAME, '_aagw')
        try:
            posts[0].click()
            time.sleep(3)
        except:
            pass
    post_url = driver.current_url
    if post_url != startlink and 'instagram.com' in str(post_url) and '/p/' in str(post_url):
        return post_url
    pyautogui.moveTo(690, 980)
    pyautogui.click()
    time.sleep(3)
    post_url = driver.current_url
    if post_url != startlink and 'instagram.com' in post_url and '/p/' in str(post_url):
        return post_url
    return None

def nextPost(url, startlink,):
    next_buttons = driver.find_elements(By.CSS_SELECTOR, 'svg[aria-label="Weiter"]')
    if len(next_buttons) == 0:
        next_buttons = driver.find_elements(By.CSS_SELECTOR, 'svg[aria-label="Next"]')
        if len(next_buttons) == 0:
            current_post = driver.current_url
            pyautogui.moveTo(1869, 595)
            pyautogui.click()
            time.sleep(1)
            if url == driver.current_url:
                driver.get(current_post)
                time.sleep(2)
                pyautogui.moveTo(1865, 575)
                pyautogui.click()
    if len(next_buttons) >= 1:
        try:
            next_buttons[0].click()
            time.sleep(2)
        except:

            time.sleep(2)
    post_url = driver.current_url
    if post_url == startlink or post_url == url or not 'instagram.com' in post_url:
        post_url = None
    return post_url

def comment_crawler(driver, post_text):
    orig_page = driver.current_url
    if 'keine kommentare' in post_text.lower():
        return 0
    comments, soup = get_commentnumber()
    if comments <= 5:
        return comments
    time.sleep(1)
    no_more_comments = 0
    for i in range(100):
        soup_buttons = soup.find_all('div',class_='_abm0')
        button = False
        for pos, b in enumerate(soup_buttons):
            if 'Weitere Kommentare laden' in str(b) or 'Load more comments' in str(b):
                button = pos
                break
        if button:
            buttons = driver.find_elements(By.CLASS_NAME,'_abm0')
            try:
                buttons[button].click()
                if i >= 20:
                    time.sleep(1)
                if i >= 40:
                    time.sleep(1)
            except:
                pass
        if orig_page != driver.current_url:
            driver.get(orig_page)
            break
        old_comments = comments
        comments,soup = get_commentnumber(old_comments)
        if old_comments == comments:
            no_more_comments += 1
        if no_more_comments > 3:
            break
        # If there are too much comments, scrape them later
        if comments >= 200:
            comments = 200
            break
        time.sleep(1)
    return comments

# Clicking with pyautogui led to many errors so I will scrape the correct higher comment counts later (with the post links)
def get_commentnumber(old_comments = 0):
    pyautogui.moveTo(1475, 330)
    for _ in range(2):
        pyautogui.scroll(-1500)
    pyautogui.moveTo(1385,755)
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source,'lxml')
    comments = len(soup.find_all('ul', class_='_a9ym'))
    if comments == 0:
        comments_elem = soup.find('div', class_='x78zum5 xdt5ytf x1iyjqo2')
        if comments_elem:
            comments = len(comments_elem)
    if comments == 0:
        comments_elem = soup.find_all('span',class_='_ap3a _aaco _aacw _aacx _aad7 _aade')
        comments = len(comments_elem)
        if comments >= 1:
            comments -= 1
    if comments > 0:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        answer_elems = soup.find_all('span')
        for a in answer_elems:
            a_text = extract_text(a)
            if 'Antworten ansehen' in a_text:
                a_number = extract_number(a_text)
                comments = comments + a_number
    if comments <= old_comments:
        return old_comments, soup
    return comments, soup


def scrape_post(post_url, p_name, upper_dt, lower_dt):
    post_date, likes, comments, image, video, calls, content, reactions_raw = ['' for _ in range(8)]
    post_dt = None
    soup = BeautifulSoup(driver.page_source, 'lxml')
    post_text = get_visible_text(Comment, soup)
    date_elem = soup.find('time', class_='x1p4m5qa')
    if not date_elem:
        return None, None
    post_dt_str = extract_text(date_elem['datetime']).split('T')[0].strip()
    post_dt = datetime.strptime(post_dt_str, '%Y-%m-%d')
    if post_dt >= upper_dt:
        return post_dt, None
    elif post_dt <= lower_dt or not p_name in post_text:
        return None, None
    post_date = post_dt.strftime('%d.%m.%Y')
    content_elem = soup.find('div', class_='_a9zs')
    if not content_elem:
        content_elem = soup.find('article')
        if content_elem:
            inner_content = content_elem.find('div',class_='xt0psk2')
            content = get_visible_text(Comment, inner_content)
            if content_elem and len(str(content)) <= 50:
                content = get_visible_text(Comment, content_elem)
    if not content_elem:
        content_elem = soup.find('div', class_='x4h1yfo')
        content = get_visible_text(Comment, content_elem)
    if len(str(content)) >= 100:
        if 'Wo.' in str(content)[:100]:
            content = content.split('Wo.',1)[1].strip()
        if 'gefällt' in str(content)[:100]:
            content = content.split('gefällt',1)[1].strip()
    if len(str(content)) <= 4:
        if len(post_text) >= 1000:
            content = post_text
    if soup.find('video'):
        video, image = 1,0
    else:
        imagelinks = [l['src'] for l in soup.find('div', class_='_aagv').find_all('img', src=True)]
        if len(imagelinks) >= 1:
            video, image = 0,1
    react_text = extract_text(soup.find('section', class_='_ae5m _ae5n _ae5o'))
    if not react_text:
        react_text = extract_text(soup.find('section', class_='x12nagc'))
    if not react_text:
        pt_l = post_text.split()
        for pos, e in enumerate(pt_l):
            if e == 'Gefällt':
                react_text = pt_l[pos] + ' ' + pt_l[pos+1] + ' ' + pt_l[pos+2]
                break
    if react_text:
        if 'Aufrufe' in react_text:
            video, image = 1,0
            calls = extract_number(react_text)
            show_likes_button = driver.find_element(By.CLASS_NAME, '_aauw')
            if show_likes_button:
                show_likes_button.click()
                # Two clicks to get on the next post
#                x,y = pyautogui.position()
            likes_elem = driver.find_element(By.CLASS_NAME, '_aauu')
            likes = extract_number(extract_text(likes_elem))
            pyautogui.moveTo(1214, 891)
            pyautogui.click()
        elif 'weiteren Personen' in react_text:
            likelink = ['https://www.instagram.com/' + l['href'] for l in soup.find_all('a', href=True) if
                        'liked' in l['href']]
            if len(likelink) >= 1:
                likes = likelink[0]
        elif 'Gefällt' in react_text or 'likes' in react_text.lower():
            likes = extract_number(react_text)
        if likes == '' and 'weiteren Personen' in post_text:
            # This alternative like display will be scraped with the alternative comment display later
            likelink = ['https://www.instagram.com/' + l['href'] for l in soup.find_all('a', href=True) if
                        'liked' in l['href']]
            if len(likelink) == 0:
                time.sleep(1)
                soup = BeautifulSoup(driver.page_source, 'lxml')
                likelink = ['https://www.instagram.com/' + l['href'] for l in soup.find_all('a', href=True) if
                            'liked' in l['href']]
            if len(likelink) >= 1:
                likes = likelink[0]
    if not likes or str(likes) == '':
        likes = int(0)
    comments = comment_crawler(driver, post_text)
    if comments > 0 and post_text != content:
        if len(str(content)) > 10:
            reactions_raw = post_text.split(content[-10:])[-1].split('Weitere Beiträge')[0]
    # Not all comments are shown, so I have to estimate the real number:
    if comments and 200 > comments > 14 :
        comments = round(comments * 1.2)

    scraped_data = [post_date, likes, comments, image, video, calls, post_url, content,reactions_raw]
    return post_dt, scraped_data


def check_conditions(ID, old_ID, row, col_names, lower_dt):
    p_name = extract_text(row['profile_name'])
    url = extract_text(str(row['url']))
    last_post = extract_text(row['last_post'])
    if 'ID_new' in col_names:
        ID = row['ID_new']
    elif 'ID' in col_names:
        ID = row['ID']
    if ID <= old_ID:
        return [False, ID, p_name, url]
    if len(url) < 10 and len(p_name) < 4:
        print([ID, url, 'no profile'])
        return [False, ID, p_name, url]
    if len(last_post) <= 4 or 'Keine Beiträge' in last_post:
        print([ID, url, 'no posts(1)'])
        return [False, ID, p_name, url]
    try:
        last_datestr = extract_text(last_post)
        last_dt = datetime.strptime(last_datestr, "%d.%m.%Y")
        if lower_dt > last_dt:
            print([ID, url, 'no posts(2)'])
            return [False, ID, p_name, url]
    except:
        print([ID, url, 'no posts(3)'])
        return [False, ID, p_name, url]
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Instagram"]')))
        # Additional waiting
        time.sleep(1)
        url = clickOnFirst(driver.current_url)
        return [True, ID, p_name, post_url]
    except:
        print([ID, url, 'no posts(4)'])
        return [False, ID, p_name, url]
########################################################################################################################

# Post Crawler
if __name__ == '__main__':
    # Settings for the post crawler
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    # Be careful with that!
    pyautogui.FAILSAFE = False
    try:
        from credentials_file import username_insta, password_insta
    except:
        username_insta = str(input('Enter your username:')).strip()
        password_insta = str(input('Enter your password:')).strip()
    os.chdir(file_path)
    file ='Profile_' + platform + '_' + str(datetime.now().year)
    for f in os.listdir():
        if file in f:
            file = extract_text(f)
            break
    # If dt_str_now isn't defined by the profile crawler, set it to none
    dt_str_now = None
    df_source, dt, dt_str, upper_dt, lower_dt = post_crawler_settings(file, platform, dt_str_now, upper_datelimit)
    col_names = list(df_source.columns)

    # Driver and Browser setup
    all_data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(username_insta, password_insta)
    if '/auth_platform' in driver.current_url:
        input('Press ENTER after 2FA')
    input('Press ENTER if the Login was successful')

    # Instagram will likely block your account after two hours of scraping
    start_time = time.time()
    old_ID = 0
    # Iterate over the companies
    for ID, row in df_source.iterrows():
        url = extract_text(row['url'])
        crawl, ID, p_name, post_url = check_conditions(ID, old_ID, row, col_names, lower_dt)
        if not crawl:
            continue
        data_per_company = []
        oor_posts = 0
        p_num = 0
        first_post = True
        last_post_url = ''
        while True:
            post_dt, scraped_data = scrape_post(post_url, p_name, upper_dt, lower_dt)
            print(scraped_data)
            if not post_dt:
                # Pinned posts can be out of the date range
                if oor_posts > 30:
                    break
                oor_posts += 1
                post_url = nextPost(url, driver.current_url)
                continue
            if post_dt >= upper_dt:
                post_url = nextPost(url, post_url)
                if not post_url:
                    break
                continue
            p_num += 1
            full_row = [ID, p_name, p_num, dt_str] + scraped_data
            data_per_company.append(full_row)
            if p_num > 1000:
                break
            post_url = nextPost(url, driver.current_url)
            if not post_url or url in post_url or post_url == last_post_url:
                break
            last_post_url = post_url

        all_data += data_per_company

        # Create a DataFrame with all posts
        header1 = ['ID_A', 'profile_name', 'ID_P', 'Erhebung', 'Datum']
        header2 = ['Likes', 'Kommentare', 'Bild', 'Video', 'Aufrufe', 'Link', 'Content', 'Comments_Text']
        dfPosts = pd.DataFrame(all_data, columns=header1 + header2)

        # Export dfPosts to Excel (with the current time)
        dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        file_name = 'Beiträge_' + platform + '_' + dt_str_now + '.xlsx'
        dfPosts.to_excel(file_name)

        # Close the crawler after two hours
        end_time = time.time()
        time_diff = end_time - start_time
        if time_diff >= (180 * 60):
            start_time = time.time()
            driver.quit()

    driver.quit()