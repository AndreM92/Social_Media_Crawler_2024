import numpy as np
import pandas as pd
import re
import os

from datetime import datetime

from langdetect import detect


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

# Dictionaries (to concatenate the tables for each platform later)
dict_summary = {}
dict_postinfo = {}
dict_posts = {}
dict_ranking = {}

if __name__ == '__main__':
    file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
    os.chdir(file_path)
    platforms = ['Facebook', 'Instagram', 'LinkedIn', 'TikTok', 'Twitter', 'YouTube']

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

        # Sum up the posts/tweets, likes, comments, shares and calculate and the interaction number as a summary
        if 'Shares' in df_sel_posts.columns:
            df_agg = df_sel_posts.groupby('ID_new').agg(
                {'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum', 'Shares': 'sum', 'Interaktionen': 'sum'}
            ).rename(columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare',
                'Shares': 'Anzahl Shares', 'Interaktionen': 'Anzahl Interaktionen'})
        elif 'Retweets' in df_sel_posts.columns:
            df_posts_retweets = df_sel_posts[df_sel_posts['Beitragsart'] == 'retweet']
            count_retweets = df_posts_retweets.groupby('ID_new').size()
            count_retweets.name = 'Retweet Posts'
            df_agg = df_agg.merge(count_retweets, on='ID_new', how='left')
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
        df_agg['Anteil Post_Interakt.'] = (df_agg['Interaktionen>0'] / df_agg['Anzahl Posts']) * 100

        if 'Aufrufe' in df_sel_posts.columns:
            view_col = df_sel_posts.groupby('ID_new')['Aufrufe'].sum()
            view_col.name = 'Anzahl Aufrufe'
            df_agg = df_agg.merge(view_col, on='ID_new', how='left')
            df_agg['Aufrufe pro Post'] = df_agg['Anzahl Aufrufe'] / df_agg['Anzahl Posts']

        # Amounts per Post
        df_agg['Likes pro Post'] = df_agg['Anzahl Likes'] / df_agg['Anzahl Posts']
        df_agg['Kommentare pro Post'] = df_agg['Anzahl Kommentare'] / df_agg['Anzahl Posts']
        df_agg['Interaktionen pro Post'] = df_agg['Anzahl Interaktionen'] / df_agg['Anzahl Posts']

        # Count the amounts of post elements and calculate their rates
        if 'Bild' in df_sel_posts.columns:
            image_perc = (df_sel_posts.groupby('ID_new')['Bild'].sum() / df_agg['Anzahl Posts']) * 100
            image_perc.name = 'Anteil Bilder'
            video_perc = (df_sel_posts.groupby('ID_new')['Video'].sum() / df_agg['Anzahl Posts']) * 100
            video_perc.name = 'Anteil Videos'
            df_agg = df_agg.merge(image_perc, how='left', on='ID_new').merge(video_perc, how='left', on='ID_new')
            df_agg['Keine/andere Elemente'] = 100 - df_agg[['Anteil Bilder', 'Anteil Videos']].sum(axis=1)
        if platform == 'YouTube' or platform == 'TikTok':
            df_agg['Anteil Videos'] = 100

        # Merge the tables and create a DF that contains all the data of the profiles and their ativity
        df_profiles_summary = df_sel_profiles.merge(df_agg, on='ID_new', how='left')
        df_profiles_summary['Network'] = platform
        df_profiles_summary.rename(columns={'url': 'Link'}, inplace=True)
        df_profiles_summary['Interaktionsrate'] = np.where((df_profiles_summary['Anzahl Posts'] >= 10),
                                                           (df_profiles_summary['Anzahl Interaktionen'] /
                                    (df_profiles_summary['Fans'] * df_profiles_summary['Anzahl Posts']) * 1000), '-')

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

        # A short summary of the profiles and their posting activity
        df_posts_compact = df_profiles_summary[['ID_new', 'ID_A', 'Name in Studie', 'Anzahl Posts', 'Link']].copy()
        df_posts_compact.rename(columns={'Name in Studie': 'Anbieter', 'Anzahl Posts': platform + '_posts',
                                        'Link': platform}, inplace=True)

        # Calculate the Interaction rate for each post
        df_sel_posts = df_sel_posts.merge(df_agg[['Anzahl Posts']], on='ID_new', how='left')
        df_sel_posts['Interaktionsrate'] = (df_sel_posts['Interaktionen'] /
                                            (df_sel_posts['Fans'] * df_sel_posts['Anzahl Posts']) * 1000)

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
        table_profiles = pd.concat([df_all_profiles_sum, df], axis=0)

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


    # Summarize the posting activity
    table_postinfo = dict_postinfo[platforms[0]][['ID_new', 'Anbieter']]
    for p, df in dict_postinfo.items():
        table_postinfo = table_postinfo.merge(df[['ID_new', p + '_posts', p]], on='ID_new', how='left')
    table_postinfo['Anzahl Kanäle'] = table_postinfo[platforms].apply(lambda row: sum('http' in str(val) for val in row), axis=1)
    n_posts = [p + '_posts' for p in platforms]
    table_postinfo['Aktiv genutzte Kanäle'] = table_postinfo[n_posts].apply(
        lambda row: sum(~row.astype(str).isna() & (pd.to_numeric(row, errors='coerce') > 0)), axis=1)
    table_postinfo['Beiträge gesamt'] = table_postinfo[n_posts].sum(axis=1)
    col_order = ['ID_new', 'Anbieter', 'Anzahl Kanäle', 'Aktiv genutzte Kanäle', 'Beiträge gesamt'] + n_posts + platforms
    table_postinfo = table_postinfo[col_order]

    dict_posts['Übersicht'] = table_postinfo


    # Final Ranking table
    table_ranking = table_postinfo[['ID_new', 'Anbieter', 'Anzahl Kanäle', 'Aktiv genutzte Kanäle']].copy()
    for platform, df in dict_ranking.items():
        if platform == 'Twitter':
            platform = 'X'
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
    dict_ranking['Gesamtranking'] = table_ranking


    # Export to excel
    date_str = datetime.now().strftime("%Y%m%d")
    name_profiles = 'Kanäle_Supplements ' + date_str + '.xlsx'
    name_posts = 'Beiträge_Supplements ' + date_str + '.xlsx'
    name_ranks = 'Ranking_Supplements ' + date_str + '.xlsx'

    table_profiles.to_excel(name_profiles)

    with pd.ExcelWriter(name_ranks, engine='xlsxwriter') as writer:
        for platform, df in dict_ranking.items():
            df.to_excel(writer, sheet_name=platform)
    with pd.ExcelWriter(name_posts, engine='xlsxwriter') as writer:
        for platform, df in dict_posts.items():
            df.to_excel(writer, sheet_name=platform)