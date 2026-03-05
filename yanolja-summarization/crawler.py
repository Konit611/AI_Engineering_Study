import json
import time

from bs4 import BeautifulSoup
from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.support.color import Color

URL = "https://nol.yanolja.com/reviews/domestic/27802?sort=LATEST"

def crawl_yanolja_reviews():
    review_list = []
    driver = webdriver.Chrome()
    driver.get(URL)

    time.sleep(3)

    scroll_count = 10
    for i in range(scroll_count):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    review_containers = soup.select('#__next > section > div > div.css-1js0bc8 > div > div > div')
    review_date = soup.select('#__next > section > div > div.css-1js0bc8 > div > div > div > div.css-1toaz2b > div > div.css-1ivchjf')
    
    for i in range(len(review_containers)):
        review_text = review_containers[i].find('p', class_='content-text').text
        review_starts = review_containers[i].find_all('path', d=lambda x: x and x.startswith('M12.638'))
        star_cnt = len(review_starts)
        date = review_date[i].text

        review_dict = {
            'review': review_text,
            'star': star_cnt,
            'date': date
        }

        review_list.append(review_dict)

    with open('./res/reviews.json', 'w') as f:
        json.dump(review_list, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    crawl_yanolja_reviews()