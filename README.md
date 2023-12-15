# Social_Media_Crawler_2023
This repository contains my new Social Media Crawler for Data Analytics

## The functionalities of the crawlers include:
- Automated logins
- Several ways to get around cookie banners
- Searching for and getting on a profile (not included in all files)
- Collection of the profile stats
- Scrolling down the feed until you reach a specific date
- Scraping of the date, content, images, links, likes, number of comments and number of shares 
of every posting
- Saving the data in DataFrames
- and finally an export of the DataFrames to an excel file

## Issues
- The DateTime on Facebook isn't displayed as text anymore, so I had to solve this problem with 
inaccurate text scraping, screenshots and image reading (Pillow/ Pytesseract)
- the links are partially provided only in XML format: 
<use xlink:href="#gid111" xmlns:xlink="http://www.w3.org/1999/xlink"></use>.
<br>

I am grateful for any proposed solutions to overcome these seemingly insurmountable problems for me.


