
import os

import pyautogui
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import time
import pandas as pd
import re
from datetime import datetime, timedelta

# Settings and paths for this program
chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
path_to_crawler_functions = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
startpage = 'https://www.instagram.com/'
platform = 'Instagram'

file_path = r'C:\Users\andre\OneDrive\Desktop\SMP_Mineralwasser 2025'
source_file = 'Beiträge_Instagram_2025-11-23' +'.xlsx'
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

# This function scrapes the details of every profile
def scrapeProfile(url, comp_keywords):
    driver.get(url)
    p_name, total_posts, follower, last_post, new_url, desc = ['' for _ in range(6)]
    time.sleep(4)
    new_url = driver.current_url
    soup = BeautifulSoup(driver.page_source, 'lxml')
    pagetext = str(get_visible_text(Comment, soup))
    broken_profile = ['nicht verfügbar', 'Eingeschränktes Profil', 'Konto ist privat', 'Seite wurde entfernt', "isn't available"]
    for m in broken_profile:
        if m in pagetext:
            p_name = m
            print(m)
            return [p_name, total_posts, follower, last_post, new_url, desc]

    full_desc = get_visible_text(Comment, soup.find('header'))
    if not full_desc or len(full_desc) <= 100:
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pagetext = get_visible_text(Comment, soup)
        full_desc = get_visible_text(Comment, soup.find('header'))
    if not platform.lower() + '.com' in driver.current_url:
        p_name = 'Wrong page'
        return [p_name, total_posts, follower, last_post, new_url, desc]

    headers = [h.text for h in driver.find_elements(By.XPATH, '//h2') if h.text]
    if len(headers) == 1:
        p_name = headers[0]
    elif len(headers) > 1:
        p_name = [h for h in headers if any(part in h.lower() for part in comp_keywords)]
        if p_name == '':
            p_list = [h for h in headers if len(h) >= 3 and (not 'neu' in h.lower() and not 'benachrichtigung' in h.lower())]
            if len(p_list) >= 1:
                p_name = p_list[0]
    p_stats = soup.find('ul',class_='x78zum5 x1q0g3np xieb3on')
    if p_stats:
        stats_list = p_stats.find_all('li')
        if stats_list:
            for e in stats_list:
                i = extract_text(e)
                if 'Beiträge' in i:
                    total_posts = extract_every_number(i)
                elif 'Follower' in i:
                    follower = extract_every_number(i)
        else:
            total_posts = full_desc
    header = soup.find('section')
    header_text = get_visible_text(Comment, header)
    if 'Gefolgt' in header_text and 'Beiträge' in header_text:
        desc = header_text.split('Gefolgt',1)[1].rsplit('Beiträge')[0].strip()
    else:
        desc = header_text
    if len(str(desc)) <= 4:
        desc = pagetext
    if 'Noch keine Beiträge' in pagetext:
        return [p_name, total_posts, follower, last_post, new_url, desc]

    link_elems = [str(l['href']) for l in soup.find_all('a',href=True)]
    all_links = ['https://www.instagram.com' + l for l in link_elems if not 'http' in l]
    p_links = [l for l in all_links if '/p/' in l]
    if len(p_links) == 0:
        p_links = [l for l in all_links if '/reel/' in l]
    if len(p_links) >= 1:
        driver.get(p_links[0])
        time.sleep(2)
        soup_post = BeautifulSoup(driver.page_source,'lxml')
        last_post = soup_post.find('time',class_='x1p4m5qa')
        if last_post:
            last_post = last_post['datetime'].split('T')[0]
            last_dt = datetime.strptime(last_post,'%Y-%m-%d')
            last_post = last_dt.strftime('%d.%m.%Y')
    return [p_name, total_posts, follower, last_post, new_url, desc]

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
        post_url == None
    return post_url


def get_commentnumber(old_comments = 0):
    pyautogui.moveTo(1475, 330)
    scrolls = round(old_comments/100) + 5
    for _ in range(scrolls):
        pyautogui.scroll(-1500)
        time.sleep(0.5 + round(scrolls/3))
    pyautogui.moveTo(1900, 225)
    for _ in range(3):
        pyautogui.scroll(1000)
    pyautogui.moveTo(1385,755)
    soup = BeautifulSoup(driver.page_source,'lxml')
    comments = len(soup.find_all('ul', class_='_a9ym'))
    if comments == 0:
        comments_elem = soup.find('div', class_='x78zum5 xdt5ytf x1iyjqo2')
        if comments_elem:
            comments = len(comments_elem)
            if comments >= 1:
                comments = comments - 1
    if comments == 0:
        comments = len(soup.find_all('span',class_='_ap3a _aaco _aacw _aacx _aad7 _aade'))
        if comments >= 1:
            comments -= 1
    if comments <= old_comments:
        return old_comments, soup
    return comments, soup


def comment_crawler(driver, post_text):
    orig_page = driver.current_url
    if 'keine kommentare' in post_text.lower():
        return 0
    comments, soup = get_commentnumber()
    if comments <= 5:
        return comments
    time.sleep(1)
    no_more_comments = 0
    for i in range(500):
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
        if no_more_comments >= 3:
            break
    return comments


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
    elif post_dt < lower_dt or not p_name in post_text:
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
        comments = round(comments * 1.1)
    scraped_data = [post_date, likes, comments, image, video, calls, post_url, content,reactions_raw]
    return post_dt, scraped_data


def check_conditions(id, row,start_at=0):
    if id < start_at:  # If you want to skip some rows
        return False
    url = str(row['url'])
    last_post = str(row['last_post'])
    if len(url) < 10 or len(last_post) <= 4 or 'Keine Beiträge' in last_post:
        print([id, url, 'no posts'])
        return False
    try:
        last_datestr = extract_text(last_post)
        last_dt = datetime.strptime(last_datestr, "%d.%m.%Y")
        if (lower_dt + timedelta(days=31)) < last_dt:
            return False
    finally:
        return True

def check_page(row):
    id = str(row['ID'])
    url = str(row['url'])
    p_name = str(row['profile_name'])
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Instagram"]')))
        # Additional waiting
        time.sleep(1)
        post_url = clickOnFirst(driver.current_url)
    except:
        post_url = None
    return id, post_url, p_name
########################################################################################################################

# Like (and comment count) correction
if __name__ == '__main__':
    os.chdir(path_to_crawler_functions)
    from crawler_functions import *
    # Be careful with that!
    pyautogui.FAILSAFE = False
    from credentials_file import username_insta, password_insta
    os.chdir(file_path)
    df_fillc = pd.read_excel(source_file)

    fill_data = []
    driver = start_browser(webdriver, Service, chromedriver_path)
    go_to_page(driver, startpage)
    login(username_insta, password_insta)
    input('Press ENTER if the Login was successful')

    corr = 0
    for ID, row in df_fillc.iterrows():
        '''
        # Restart the driver after 150 corrections
        if corr > 0 and (corr % 150 == 0 or corr % 151 == 0):
            driver.quit()
            time.sleep(5)
            driver = start_browser(webdriver, Service, chromedriver_path)
            go_to_page(driver, startpage)
            login(cred.username_insta, cred.password_insta)
            time.sleep(3)
        '''
        comments = row['Kommentare']
        likes = row['Likes']
        if 'http' in str(likes):
            try:
                driver.get(str(likes))
                WebDriverWait(driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Instagram"]')))
                time.sleep(2)
            except:
                try:
                    pyautogui.moveTo(1277, 587)
                    pyautogui.click()
                    driver.get(str(likes))
                    WebDriverWait(driver, 7).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Instagram"]')))
                    time.sleep(1)
                except:
                    input('Press ENTER after solving website issues')
                    pass
            likes = len(driver.find_elements('xpath', "//*[text()='Folgen']"))
            if likes == 0:
                time.sleep(2)
                likes = len(driver.find_elements('xpath', "//*[text()='Folgen']"))
                if likes == 0:
                    soup = BeautifulSoup(driver.page_source,'html.parser')
                    likes = len(soup.find_all('div',class_="_ap3a _aaco _aacw _aad6 _aade"))
            corr += 1
#        if comments >= 20000:
        if ((not comments and not '0' in str(comments)) or str(comments) == 'nan' or str(comments) == '' or comments >= 200):
            try:
                driver.get(row['Link'])
                WebDriverWait(driver, 7).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Instagram"]')))
            except:
                try:
                    pyautogui.moveTo(1277, 587)
                    pyautogui.click()
                    driver.get(row['Link'])
                    WebDriverWait(driver, 7).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Instagram"]')))
                except:
                    input('Press ENTER after solving website issues')
                    pass
            soup = BeautifulSoup(driver.page_source, 'lxml')
            post_text = get_visible_text(Comment, soup)
            comments = comment_crawler(driver, post_text)
            corr += 1
        fill_data.append([ID, row['ID_A'], likes, comments])

    df_filled = pd.DataFrame(fill_data, columns=['ID','ID_A', 'Likes', 'Kommentare'])
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    new_filename = 'filled_Likes_comments_' + dt_str_now + '.xlsx'
    df_filled.to_excel(new_filename)
    print('Done')
    driver.quit()

#currentMouseX, currentMouseY = pyautogui.position()