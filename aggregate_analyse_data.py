import numpy as np
import pandas as pd
import re
import os
from collections import OrderedDict
from datetime import datetime

from langdetect import detect
from crawler_functions import lang_interpreter

import locale
########################################################################################################################

def get_tables(platform):
    file_keys = ['Auswahl_', 'Profile_', 'Beiträge_']
    file_names = ['' for _ in range(3)]
    dfs = ['' for _ in range(len(file_names))]
    for f in os.listdir():
        if file_names[0] == '' and file_keys[0] in f:
            file_names[0] = f
        for id, n in enumerate(file_keys):
            if file_names[id] == '' and n + platform in f:
                file_names[id] = f
    for id, f in enumerate(file_names):
        if not f:
            print(file_keys[id] + platform + ' not in path')
            exit()
        dfs[id] = pd.read_excel(f)
    return dfs


def format_language(profile_desc, post_content):
    # Specific keywords
    branch_eng = ['vitamins', 'nutrients', 'nutritional', 'mineralization', 'products', 'Athletes', 'Healthy']
    branch_ger = [' Vitamine ', 'Ernährung ', 'Nährstoff', 'Sport', 'Leistung', 'Gesundheit', 'Bestform', 'Motivation']
    profile_desc = profile_desc.split('Link')[0]
    sc = profile_desc.split('·')[0]
    if len(sc) >= 50:
        profile_desc = sc
    post_content = post_content.split('Mehr anzeigen')[0]
    pc = post_content.split('·')[0]
    if len(pc) >= 30:
        post_content = pc
    lang_profile = lang_interpreter(detect, branch_eng, branch_ger, profile_desc)
    lang_posts = lang_interpreter(detect, branch_eng, branch_ger, post_content)
    languages = [lang_profile, lang_posts]
    if '-' in languages:
        languages.remove('-')
    if len(languages) == 0:
        lang = '-'
    elif 'de' in languages and not 'en' in languages:
        lang = 'Deutsch'
    elif 'de' in languages and 'en' in languages:
        lang = 'Deutsch/ Internat.'
    elif 'en' in languages:
        lang = 'Englisch/ Internat.'
    elif 'fr' in languages:
        lang = 'Französisch'
    elif 'es' in languages:
        lang = 'Spanisch'
    elif 'pl' in languages:
        lang = 'Polnisch'
    else:
        lang = ', '.join(languages)
    return lang


def freq_in_posts(_by, platform, df):
    title = 'Häufigkeiten Top-100 Posts nach ' + _by
    df_sorted = df.sort_values(_by, ascending=False).copy()
    if platform == 'X':
        df_sorted = df_sorted[df_sorted['Beitragsart'] != 'retweet']
    df_top100 = df_sorted[:100]
    df_frequencies = df_top100.groupby(['ID_new', 'Name in Studie']).size().reset_index(name=title)
    df_frequencies = df_frequencies.sort_values(by=title, ascending=False).reset_index(drop=True)
    df_frequencies['Rang'] = df_frequencies[title].rank(ascending=False, method='min').astype(int)
    df_frequencies = df_frequencies[['ID_new', 'Rang'] + list(df_frequencies.columns)[1:-1]]
    return df_frequencies

def get_words_and_hashtags(content_list):
    word_dict = {}
    hash_dict = {}
    content_list = [c for c in content_list if isinstance(c, str)]
    full_content = ' '.join(content_list).replace('#', ' #')
    cleaned_content = re.sub(r'(?<!#)\b(?<!\w)(\w+)\b(?!\w)', r' \1 ', full_content)
    cleaned_content2 = re.sub('\s+', ' ', cleaned_content).strip()
    word_list = [str(w).strip() for w in cleaned_content2.split(' ') if
                 (len(str(w).strip()) >= 3 and not str(w).isdigit())]
    word_list = [w for w in word_list if str(w)[0] == '#' or not any(w.lower() == e.lower() for e in excludelist)]
    for w in word_list:
        if w[0] == '#':
            if w in hash_dict:
                hash_dict[w] += 1
            else:
                hash_dict[w] = 1
        else:
            if w in word_dict:
                word_dict[w] += 1
            else:
                word_dict[w] = 1
    word_dict = sorted(word_dict.items(), key=lambda item: item[1], reverse=True)
    hash_dict = sorted(hash_dict.items(), key=lambda item: item[1], reverse=True)
    word_dict = word_dict[:150]
    hash_dict = hash_dict[:150]
    df_topwords = pd.DataFrame(word_dict, columns=['words', 'count'])
    df_tophashtags = pd.DataFrame(hash_dict, columns=['hashtags', 'count2'])
    df_w_h = pd.concat([df_topwords, df_tophashtags], axis=1)
    return df_w_h


if __name__ == '__main__':
    working_path = r"C:\Users\andre\Documents\Python\Web_Crawler\Social_Media_Crawler_2024"
    file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
    os.chdir(file_path)
    platforms = ['Facebook', 'Instagram', 'LinkedIn', 'TikTok', 'X', 'YouTube']
    # I set my locale to German
    locale.setlocale(locale.LC_NUMERIC, 'de_DE.UTF-8')
    # Dictionaries (to concatenate the tables for each platform later)
    dict_summary = {}
    dict_postinfo = {}
    dict_posts = {}
    dict_ranking = {}

    for platform in platforms:
        df_selection, df_profiles, df_posts = get_tables(platform)
        df_profiles.rename(columns={'ID': 'ID_A', 'company': 'Name in Studie', 'profile_name': 'Profilname', }, inplace=True)

        # Create a DF with the selected Profiles
        df_sel_profiles = df_selection[['ID_new', 'ID_A', 'Firma/Marke']].merge(df_profiles, on='ID_A', how='left')
        columns_to_remove = ['Unnamed', 'Number', 'date', 'employees']  #last_post?
        for c in df_sel_profiles.columns:
            for cn in columns_to_remove:
                if cn in c:
                    df_sel_profiles.drop(columns=c, inplace=True)
        desc, d1, d2, tl = 'description', 'description1', 'description2', 'tagline'
        if d1 in df_sel_profiles.columns and d2 in df_sel_profiles.columns:
            df_sel_profiles[desc] = (df_sel_profiles[d1].fillna('') + ' ' +
                                              df_sel_profiles[d2].fillna('')).str.strip()
            df_sel_profiles.drop(columns={d1,d2}, inplace=True)
        if tl in df_sel_profiles.columns:
            df_sel_profiles[desc] = (df_sel_profiles[tl].fillna('') + ' ' +
                                          df_sel_profiles[desc].fillna('')).str.strip()
            df_sel_profiles.drop(columns={tl}, inplace=True)
        if not 'follower' in df_profiles.columns:
            print('Missing column in ' + platform)
            exit()
        if not 'fans' in df_profiles.columns:
            df_sel_profiles.rename(columns={'follower': 'fans'}, inplace=True)
        df_sel_profiles.rename(columns={'fans':'Fans', 'description':'Beschreibung'},inplace=True)

        # Create a DF with selected Posts
        df_sel_posts = df_sel_profiles[['ID_new', 'ID_A', 'Name in Studie', 'Fans']].merge(
            df_posts, on='ID_A', how='inner') #remove platform
        columns_to_remove = ['Unnamed', 'Number', 'Erhebung']
        for c in df_sel_posts.columns:
            for cn in columns_to_remove:
                if cn in c:
                    df_sel_posts.drop(columns=c, inplace=True)
        if 'Shares' in df_sel_posts.columns:
            df_sel_posts['Interaktionen'] = df_sel_posts[['Likes', 'Kommentare', 'Shares']].sum(axis=1)
        elif 'Retweets' in df_sel_posts.columns:
            df_sel_posts['Interaktionen'] = df_sel_posts[['Likes', 'Kommentare', 'Retweets']].sum(axis=1)
        else:
            df_sel_posts['Interaktionen'] = df_sel_posts[['Likes', 'Kommentare']].sum(axis=1)

        # Interpret the language of the profile based on the profile description
        # To interpret the language of the posts also, I first need to add the content of the last post
        # of every company to the profile df
        first_post_content = df_sel_posts.groupby('ID_new').first()['Content']
        df_sel_profiles = df_sel_profiles.merge(first_post_content, on='ID_new', how='left')
        df_sel_profiles.rename(columns={'Content': 'first_post_content'}, inplace=True)
        lang_list = []
        for id, row in df_sel_profiles.iterrows():
            lang = format_language(str(row['Beschreibung']), str(row['first_post_content']))
            lang_list.append(lang)
        df_sel_profiles['Sprache'] = lang_list

        # Sum up the posts/tweets, likes, comments, shares and the interaction number as a summary
        if 'Shares' in df_sel_posts.columns:
            df_agg = df_sel_posts.groupby('ID_new').agg(
                {'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum', 'Shares': 'sum', 'Interaktionen': 'sum'}
            ).rename(columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare',
                'Shares': 'Anzahl Shares', 'Interaktionen': 'Anzahl Interaktionen'})
        elif 'Retweets' in df_sel_posts.columns:
            df_posts_retweets = df_sel_posts[df_sel_posts['Beitragsart'] == 'retweet']
            count_retweets = df_posts_retweets.groupby('ID_new').size()
            count_retweets.name = 'Retweet Posts'
            df_sel_profiles = df_sel_profiles.merge(count_retweets, on='ID_new', how='left')
            df_sel_posts = df_sel_posts[df_sel_posts['Beitragsart'] != 'retweet']
            df_agg = df_sel_posts.groupby('ID_new').agg(
                {'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum', 'Retweets': 'sum','Interaktionen': 'sum'}
            ).rename(columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare',
                'Retweets': 'Anzahl Shares', 'Interaktionen': 'Anzahl Interaktionen'})
        else:
            df_agg = df_sel_posts.groupby('ID_new').agg({'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum'}).rename(
                columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare'})
            df_agg['Anzahl Interaktionen'] = df_agg[['Anzahl Likes', 'Anzahl Kommentare']].sum(axis=1)

        interactions_above_zero = df_sel_posts[df_sel_posts['Interaktionen'] >= 1].groupby('ID_new').size()
        interactions_above_zero.name = 'Interaktionen>0'
        df_agg = df_agg.merge(interactions_above_zero, on='ID_new', how='left')
        df_agg['Anteil Post_Interakt.'] = ((df_agg['Interaktionen>0'] / df_agg['Anzahl Posts']) * 100).round(2)

        if 'Aufrufe' in df_sel_posts.columns:
            view_col = df_sel_posts.groupby('ID_new')['Aufrufe'].sum()
            view_col.name = 'Anzahl Aufrufe'
            df_agg = df_agg.merge(view_col, on='ID_new', how='left')
            df_agg['Aufrufe pro Post'] = (df_agg['Anzahl Aufrufe'] / df_agg['Anzahl Posts']).round(2)

        # Amounts per Post
        df_agg['Likes pro Post'] = (df_agg['Anzahl Likes'] / df_agg['Anzahl Posts']).round(2)
        df_agg['Kommentare pro Post'] = (df_agg['Anzahl Kommentare'] / df_agg['Anzahl Posts']).round(2)
        df_agg['Interaktionen pro Post'] = (df_agg['Anzahl Interaktionen'] / df_agg['Anzahl Posts']).round(2)

        # Count the amounts of post elements and calculate their rates
        if 'Bild' in df_sel_posts.columns:
            image_perc = ((df_sel_posts.groupby('ID_new')['Bild'].sum() / df_agg['Anzahl Posts']) * 100).round(2)
            image_perc.name = 'Anteil Bilder'
            video_perc = ((df_sel_posts.groupby('ID_new')['Video'].sum() / df_agg['Anzahl Posts']) * 100).round(2)
            video_perc.name = 'Anteil Videos'
            df_agg = df_agg.merge(image_perc, how='left', on='ID_new').merge(video_perc, how='left', on='ID_new')
            df_agg['Keine/andere Elemente'] = 100 - (df_agg[['Anteil Bilder', 'Anteil Videos']].sum(axis=1)).round(2)
        if platform == 'YouTube' or platform == 'TikTok':
            df_agg['Anteil Videos'] = 100

        # Merge the tables and create a DF that contains all the data of the profiles and their ativity
        df_profiles_summary = df_sel_profiles.merge(df_agg, on='ID_new', how='left')
        df_profiles_summary['Network'] = platform
        df_profiles_summary.rename(columns={'url': 'Link'}, inplace=True)
        df_profiles_summary['Interaktionsrate'] = np.where((df_profiles_summary['Anzahl Posts'] >= 1),
                                                           (df_profiles_summary['Anzahl Interaktionen'] /
                        (df_profiles_summary['Fans'] * df_profiles_summary['Anzahl Posts']) * 1000).round(5), np.nan)
        df_profiles_summary['Interaktionsrate'].fillna('-', inplace=True)
        col_order_overview = ['ID_new', 'ID_A', 'Firma/Marke', 'Name in Studie', 'Network', 'Profilname', 'Sprache',
                              'Fans', 'Anzahl Posts', 'Retweet Posts', 'Anzahl Likes', 'Anzahl Kommentare',
                              'Anzahl Shares', 'Anzahl Interaktionen', 'Anzahl Aufrufe', 'Interaktionsrate',
                              'Interaktionen pro Post', 'Likes pro Post', 'Kommentare pro Post', 'Aufrufe pro Post',
                              'Anteil Post_Interakt.',
                              'Anteil Bilder', 'Anteil Videos', 'Keine/andere Elemente', 'Link', 'Beschreibung']
        for e in col_order_overview:
            if e not in df_profiles_summary:
                df_profiles_summary[e] = '-'
        df_profiles_summary = df_profiles_summary[col_order_overview]

        # Add zeros to the profile count if they havent posted anything
        linklist = list(df_profiles_summary['Link'])
        post_numbers = list(df_profiles_summary['Anzahl Posts'])
        for id, l in enumerate(linklist):
            if 'http' in str(l) and not(str(post_numbers[id])[0].isdigit()):
                post_numbers[id] = 0
        df_profiles_summary['Anzahl Posts'] = post_numbers

        # A short summary of the profiles and their posting activity
        df_posts_compact = df_profiles_summary[['ID_new', 'ID_A', 'Name in Studie', 'Anzahl Posts', 'Link']].copy()
        df_posts_compact.rename(columns={'Name in Studie': 'Anbieter', 'Anzahl Posts': platform + '_posts',
                                        'Link': platform}, inplace=True)

        # Calculate the Interaction rate for each post
        df_sel_posts = df_sel_posts.merge(df_agg[['Anzahl Posts']], on='ID_new', how='left')
        df_sel_posts['Interaktionsrate'] = (df_sel_posts['Interaktionen'] /
                                            (df_sel_posts['Fans'] * df_sel_posts['Anzahl Posts']) * 1000).round(5)
        # Customized deletion and ordering of the columns
        if any(c == 'ID' for c in df_sel_posts.columns):
            df_sel_posts.drop(columns={'ID', 'Fans', 'Anzahl Posts'}, inplace=True)
        else:
            df_sel_posts.drop(columns={'Anzahl Posts','Fans'},inplace=True)
        col_unorder_p = list(df_sel_posts.columns)
        if 'Retweets' in col_unorder_p:
            pos = col_unorder_p.index('Retweets') + 1
        elif 'Shares' in col_unorder_p:
            pos = col_unorder_p.index('Shares') + 1
        else:
            pos = col_unorder_p.index('Kommentare') + 1
        col_order_p = col_unorder_p[:pos] + ['Interaktionen', 'Interaktionsrate'] + col_unorder_p[pos:-2]
        df_sel_posts = df_sel_posts[col_order_p]

        # Ranking
        df_ranking_s = df_profiles_summary[
                            ['ID_new', 'Name in Studie', 'Fans', 'Anzahl Posts', 'Anzahl Interaktionen']].copy()
        df_ranking_s.rename(columns={'Name in Studie': 'Anbieter', 'Anzahl Posts': 'Posts',
                                     'Anzahl Interaktionen': 'Interaktionen'}, inplace=True)
        df_ranking_s['Index_F'] = (df_ranking_s['Fans'] / df_ranking_s['Fans'].mean() * 100).round(2)
        df_ranking_s['Index_P'] = (df_ranking_s['Posts'] / df_ranking_s['Posts'].mean() * 100).round(2)
        df_ranking_s['Index_I'] = (df_ranking_s['Interaktionen'] / df_ranking_s['Interaktionen'].mean() * 100).round(2)
        df_ranking_s['Rang_F'] = df_ranking_s['Fans'].rank(ascending=False, na_option='bottom', method='dense')
        df_ranking_s['Rang_P'] = df_ranking_s['Posts'].rank(ascending=False, na_option='bottom', method='dense')
        df_ranking_s['Rang_I'] = df_ranking_s['Interaktionen'].rank(ascending=False, na_option='bottom', method='dense')
        df_ranking_s['Index'] = df_ranking_s[['Index_F', 'Index_P', 'Index_I']].sum(axis=1)
        df_ranking_s['Rang'] = df_ranking_s['Index'].rank(ascending=False, na_option='bottom', method='dense')
        col_order_ranking_s = ['Rang', 'ID_new', 'Anbieter', 'Fans', 'Index_F', 'Rang_F', 'Posts',
                               'Index_P', 'Rang_P', 'Interaktionen', 'Index_I', 'Rang_I', 'Index']
        df_ranking_s = df_ranking_s[col_order_ranking_s]
        df_ranking_s = df_ranking_s.sort_values(by='Rang').reset_index(drop=True)

        # Store the tables in dictionaries with the platform name as the key
        dict_summary[platform] = df_profiles_summary
        dict_postinfo[platform] = df_posts_compact
        dict_posts[platform] = df_sel_posts
        dict_ranking[platform] = df_ranking_s
        print(platform + ' Done')

    ########################################################################################################################
    # Concat/ Merge the full tables

    # Complete profile data
    table_profiles = dict_summary[platforms[0]]
    for p, df in dict_summary.items():
        if p == platforms[0]:
            continue
        table_profiles = pd.concat([table_profiles, df], axis=0)

    # Custom function for na-filling
    table_profiles['Link'].fillna('-', inplace=True)

    def custom_fill(row):
        if len(str(row['Link'])) < 5:
            return row.fillna('-')
        elif pd.isna(row['Anzahl Posts']):
            row['Anzahl Posts'] = 0
        return row.fillna('-')

    # Apply the custom function to each row
    table_profiles = table_profiles.apply(custom_fill, axis=1)
    table_profiles.columns.values[0]

    # Create an Ordered Dict and start with the profile table
    ordered_dict_profiles = OrderedDict([('Kanäle Übersicht',table_profiles)])


    # Summarize the posting activity
    n_posts = [p + '_posts' for p in platforms]
    table_postinfo = dict_postinfo[platforms[0]][['ID_new', 'Anbieter']]
    for p, df in dict_postinfo.items():
        table_postinfo = table_postinfo.merge(df[['ID_new', p + '_posts', p]], on='ID_new', how='left')
    table_postinfo['Anzahl Kanäle'] = table_postinfo[platforms].apply(lambda row: sum('http' in str(val) for val in row), axis=1)
    table_postinfo['Aktiv genutzte Kanäle'] = table_postinfo[n_posts].apply(
        lambda row: sum(~row.astype(str).isna() & (pd.to_numeric(row, errors='coerce') > 0)), axis=1)
    table_postinfo['Beiträge gesamt'] = table_postinfo[n_posts].sum(axis=1)
    col_order = ['ID_new', 'Anbieter', 'Anzahl Kanäle', 'Aktiv genutzte Kanäle', 'Beiträge gesamt'] + n_posts + platforms
    table_postinfo = table_postinfo[col_order]

    # Create a df about the usage rate of each platform
    existing_accounts = {}
    active_accounts = {}
    for id, platform in enumerate(platforms):
        existing_accounts[platform] = table_postinfo[platform].count()
        active_accounts[platform] = table_postinfo[table_postinfo[n_posts[id]] > 0][n_posts[id]].count()
    df_usage_rate = pd.DataFrame({'Account vorhanden': existing_accounts, 'Account aktiv genutzt': active_accounts})
    ordered_dict_profiles.update({'Nutzungsgrad':df_usage_rate})

    # Create a dict with dfs about the statistics for each platform
    dict_statistics = {}
    table_names = ['Fans', 'Anzahl Posts', 'Anzahl Interaktionen']
    col_names = ['Min', 'Max', 'Mittelwert', 'Median']
    for t in table_names:
        statistics_data = []
        for p, df in dict_summary.items():
            st = t.replace('Anzahl ', '')
            min = df[t].min().round(2)
            max = df[t].max().round(2)
            mean = df[t].mean().round(2)
            median = df[t].median().round(2)
            row = [p,min,max,mean,median]
            statistics_data.append(row)
        df_statistics_s = pd.DataFrame(statistics_data, columns=[st] + col_names)
        dict_statistics[t] = df_statistics_s

#        table_statistics = pd.concat([table_statistics, df_statistics_s], axis=0)


    # Create an Ordered dict for the posts
    table_postinfo.fillna('-', inplace=True)
    ordered_dict_posts = OrderedDict([('Übersicht', table_postinfo)])
    # Update the OrderedDict with the posts on every platform
    ordered_dict_posts.update((p, df) for p, df in dict_posts.items())


    # Final Ranking table
    table_ranking = table_postinfo[['ID_new', 'Anbieter', 'Anzahl Kanäle', 'Aktiv genutzte Kanäle']].copy()
    for platform, df in dict_ranking.items():
        df_ranking_i = df[['ID_new', 'Rang', 'Index']].copy()
        df_ranking_i.rename(columns={'Rang': 'Rang_' + platform[:1], 'Index': 'Index_' + platform[:1]}, inplace=True)
        table_ranking = table_ranking.merge(df_ranking_i, on='ID_new', how='left')

    table_ranking['Rang_avg'] = (table_ranking[['Rang_F', 'Rang_I', 'Rang_L',
                                                'Rang_T', 'Rang_X', 'Rang_Y']].mean(axis=1)).round(2)
    table_ranking['Index_avg'] = (table_ranking[['Index_F', 'Index_I', 'Index_L',
                                                 'Index_T', 'Index_X', 'Index_Y']].mean(axis=1)).round(2)
    table_ranking['Rang'] = table_ranking['Index_avg'].rank(ascending=False, na_option='bottom', method='dense')
    # table_ranking['Punkte'] = (table_ranking['Index_avg'] - table_ranking['Rang_avg']**0.5).round(2)
    # table_ranking['Rang'] = table_ranking['Punkte'].rank(ascending=False, na_option='bottom', method='dense')
    col_order_rf = ['Rang'] + list(table_ranking.columns)[:-1]
    table_ranking = table_ranking[col_order_rf]
    table_ranking = table_ranking.sort_values(by='Rang').reset_index(drop=True)

    # Append the ranking tables to ordered_dict_profiles
    ordered_dict_profiles.update({'Gesamtranking': table_ranking})
    ordered_dict_profiles.update((p, df) for p, df in dict_ranking.items())

    ########################################################################################################################
    # Top 100-Posts Frequencies, Words and Hashtags
    os.chdir(working_path)
    with open('exclude_words.txt', 'r', encoding='utf-8') as file:
        excludelist = [line.strip() for line in file]

    dict_frequencies = {}
    dict_w_h = {}
    for platform, df in dict_posts.items():
        rank_by = ['Likes', 'Kommentare', 'Interaktionsrate']
        for _by in rank_by:
            df_frequencies = freq_in_posts(_by, platform, df)
            tab_name = platform[:1] + '_Top100_' + _by
            if len(tab_name) >= 31:
                tab_name = tab_name[:31]
            dict_frequencies[tab_name] = df_frequencies

        content_list = list(df['Content'])
        df_w_h = get_words_and_hashtags(content_list)
        dict_w_h[platform] = df_w_h


    # Export to excel
    date_str = datetime.now().strftime("%Y%m%d")
    name_profiles = 'Kanäle_Supplements ' + date_str + '.xlsx'
    name_posts = 'Beiträge_Supplements ' + date_str + '.xlsx'

    os.chdir(file_path)
    with pd.ExcelWriter(name_profiles, engine='xlsxwriter') as writer:
        for platform, df in ordered_dict_profiles.items():
            df.to_excel(writer, sheet_name=platform)
    with pd.ExcelWriter(name_posts, engine='xlsxwriter') as writer:
        for platform, df in ordered_dict_posts.items():
            df.to_excel(writer, sheet_name=platform)