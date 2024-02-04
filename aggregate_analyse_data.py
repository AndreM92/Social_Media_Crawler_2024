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


if __name__ == '__main__':
    file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
    os.chdir(file_path)
    platforms = ['LinkedIn']

    for platform in platforms:
        df_selection, df_profiles, df_posts = get_tables(platform)
        df_profiles.rename(columns={'ID': 'ID_A', 'company': 'Name in Studie', 'profile_name': 'Profilname',
                                    'url': platform}, inplace=True)

        # Create a DF with selected Profiles
        df_sel_profiles = df_selection[['ID_new', 'ID_A', 'Firma/Marke']].merge(df_profiles, on='ID_A', how='left')
        columns_to_remove = ['Unnamed', 'Number', 'date', 'employees']
        for c in df_sel_profiles.columns:
            for cn in columns_to_remove:
                if cn in c:
                    df_sel_profiles.drop(columns=c, inplace=True)
        desc, d1, d2, tl = 'description', 'description1', 'description2', 'tagline'
        if d1 in df_sel_profiles.columns and d2 in df_sel_profiles.columns:
            df_sel_profiles[desc] = (df_sel_profiles[d1].fillna('') + ' ' +
                                              df_sel_profiles[d1].fillna('')).str.strip()
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
        df_sel_posts = df_sel_profiles[['ID_new', 'ID_A', 'Name in Studie', 'Fans']].merge(df_posts, on='ID_A', how='inner')
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

        # Calculations of post numbers
        if 'Shares' in df_sel_posts.columns:
            df_agg = df_sel_posts.groupby('ID_new').agg(
                {'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum', 'Shares': 'sum', 'Interaktionen': 'sum'}
            ).rename(columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare',
                'Shares': 'Anzahl Shares', 'Interaktionen': 'Anzahl Interaktionen'})
        elif 'Retweets' in df_sel_posts.columns:
            df_posts_retweets = df_sel_posts[df_sel_posts['Beitragsart'] == 'retweet']
            count_retweets = df_posts_retweets.groupby('ID_A').size()
            count_retweets.name = 'Retweet Posts'
            df_sel_posts = df_sel_posts[df_sel_posts['Beitragsart'] != 'retweet']
            df_agg = df_sel_posts.groupby('ID_new').agg(
                {'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum', 'Retweets': 'sum','Interaktionen': 'sum'}
            ).rename(columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare',
                'Retweets': 'Anzahl Retweets', 'Interaktionen': 'Anzahl Interaktionen'})
        else:
            df_agg = df_sel_posts.groupby('ID_new').agg({'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum'}).rename(
                columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare'})
            df_agg['Interaktionen'] = df_agg[['Anzahl Likes', 'Anzahl Kommentare']].sum(axis=1)

        # Merge dfs
        df_sel_posts = df_sel_posts.merge(df_agg, on='ID_new', how='inner')

        # Calculate the Interaction rate for each post
        df_sel_posts['Interaktionsrate'] = (df_sel_posts['Interaktionen'] /
                                            (df_sel_posts['Fans'] * df_sel_posts['Anzahl Posts']) * 1000)

        df_sel_posts.to_excel('Postdata_agg_' + platform + '.xlsx')
