# Social_Media_Crawler_2023
This repository contains my new Social Media Crawler for Data Analytics <br>
(Written for German social media pages, but easily transferable to other languages)

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
- The DateTime on Facebook is no longer displayed as text, 
requiring me to address this issue through less precise methods 
such as text scraping, screenshots, and image reading (utilizing Pillow/Pytesseract)
- the links are partially provided only in XML format: 
"use xlink:href="#gid111" xmlns:xlink="http://www.w3.org/1999/xlink"></use"
<br>
Consequently, I am unable to scrape their text content directly. Although I devised a method 
to associate visible dates with posts, this approach introduces some inaccuracies.
- Certain crawlers necessitate a headed browser due to my use of PyAutoGUI 
to navigate around bot blocking and handle exceptional page settings.

I appreciate any suggested solutions to overcome these seemingly insurmountable challenges.

