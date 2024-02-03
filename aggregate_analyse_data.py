import numpy as np
import pandas as pd
import re
import os

from datetime import datetime

from langdetect import detect


def get_tables(platform):
    filename_posts, filename_profile = None, None
    for f in os.listdir():
        if 'Beiträge_' + platform in f:
            filename_posts = f
        elif 'Profile_' + platform in f:
            filename_profile = f
    if not filename_profile:
        print('Profile_' + platform + ' not in path')
        exit()
    if not filename_posts:
        print('Beiträge_' + platform + ' not in path')
        exit()
    df_profiles = pd.read_excel(filename_profile)
    df_posts = pd.read_excel(filename_posts)
    return df_profiles, df_posts


if __name__ == '__main__':
    file_path = r"C:\Users\andre\OneDrive\Desktop\Nahrungsergaenzungsmittel"
    os.chdir(file_path)
    platforms = ['LinkedIn']

    for platform in platforms:
        df_profiles, df_posts = get_tables(platform)
        # Get the first table with the selections and firm names also

        if 'description1' in df_profiles.columns and 'description2' in df_profiles.columns:
            df_profiles['description'] = (df_profiles['description1'].fillna('') + ' ' + \
                                         df_profiles['description2'].fillna('')).str.strip()
        if 'tagline' in df_profiles.columns:
            df_profiles['description'] = (df_profiles['tagline'].fillna('') + ' ' +
                                          df_profiles['description'].fillna('')).str.strip()

        if 'fans' in df_profiles.columns:
            df_profiles_red = df_profiles[['ID', 'company', 'profile_name', 'fans', 'url', 'description']].copy()
        else:
            df_profiles_red = df_profiles[['ID', 'company', 'profile_name', 'follower', 'url', 'description']].copy()
            df_profiles_red.rename(columns={'follower':'fans'},inplace=True)
        df_profiles_red.rename(columns={'ID': 'ID_A', 'company': 'Name in Studie', 'profile_name': 'Profilname',
                                        'fans':'Fans', 'description':'Beschreibung'},inplace=True)

        df_agg = pd.merge(df_posts, df_profiles_red[['ID_A', 'Fans']], on='ID_A', how='inner')
        if 'Shares' in df_agg.columns:
            df_agg['Interaktionen'] = df_agg[['Likes', 'Kommentare', 'Shares']].sum(axis=1)
        elif 'Retweets' in df_agg.columns:
            df_agg['Interaktionen'] = df_agg[['Likes', 'Kommentare', 'Retweets']].sum(axis=1)
        else:
            df_agg['Interaktionen'] = df_agg[['Likes', 'Kommentare']].sum(axis=1)

        # Calculations of post numbers
        if 'Shares' in df_agg.columns:
            df_posts_calc = df_agg.groupby('ID_A').agg(
                {'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum', 'Shares': 'sum', 'Interaktionen': 'sum'}
            ).rename(columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare',
                'Shares': 'Anzahl Shares', 'Interaktionen': 'Anzahl Interaktionen'})
        elif 'Retweets' in df_agg.columns:
            df_posts_retweets = df_agg[df_posts['Beitragsart'] == 'retweet']
            count_retweets = df_posts_retweets.groupby('ID_A').size()
            count_retweets.name = 'Retweet Posts'
            df_agg = df_posts[df_posts['Beitragsart'] != 'retweet']
            df_posts_calc = df_posts.groupby('ID_A').agg(
                {'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum', 'Retweets': 'sum','Interaktionen': 'sum'}
            ).rename(columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare',
                'Retweets': 'Anzahl Retweets', 'Interaktionen': 'Anzahl Interaktionen'})
        else:
            df_posts_calc = df_agg.groupby('ID_A').agg({'ID_A': 'size', 'Likes': 'sum', 'Kommentare': 'sum'}).rename(
                columns={'ID_A': 'Anzahl Posts', 'Likes': 'Anzahl Likes', 'Kommentare': 'Anzahl Kommentare'})
            df_posts_calc['Interaktionen'] = df_posts_calc[['Anzahl Likes', 'Anzahl Kommentare']].sum(axis=1)

        df_agg.fillna(0, inplace=True)




