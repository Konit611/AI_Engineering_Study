import json
import time
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

TARGETS = [
    {
        'name': 'reviews',
        'url': 'https://www.jalan.net/yad324579/kuchikomi/?screenId=UWW3001&yadNo=324579&roomCount=1&adultNum=2&dateUndecided=1&roomCrack=200000&stayCount=1&rootCd=04&smlCd=012602&distCd=01&ccnt=lean-kuchikomi-tab',
    },
    {
        'name': 'kunosato',
        'url': 'https://www.jalan.net/yad332582/kuchikomi/?screenId=UWW3001&rootCd=04&stayYear=2026&stayMonth=3&stayDay=2&stayCount=1&roomCount=1&adultNum=2&roomCrack=200000&yadNo=332582&callbackHistFlg=1&smlCd=012602&distCd=01&ccnt=lean-kuchikomi-tab',
    },
    {
        'name': 'global_view',
        'url': 'https://www.jalan.net/yad303000/kuchikomi/?screenId=UWW3001&rootCd=04&stayYear=2026&stayMonth=3&stayDay=2&stayCount=1&roomCount=1&adultNum=2&roomCrack=200000&yadNo=303000&callbackHistFlg=1&smlCd=012602&distCd=01&ccnt=lean-kuchikomi-tab',
    },
]
MAX_PAGES = 5

# jalan.net 세부 평점 라벨 → 필드명
RATING_MAP = {
    '部屋': 'room',
    '風呂': 'bath',
    '料理(朝食)': 'breakfast',
    '料理（朝食）': 'breakfast',
    '料理(夕食)': 'dinner',
    '料理（夕食）': 'dinner',
    '接客・サービス': 'service',
    '清潔感': 'cleanliness',
}


def crawl_jalan_reviews():
    driver = webdriver.Chrome()

    for target in TARGETS:
        name = target['name']
        url = target['url']
        output_path = f'./res/{name}.json'

        print(f"\n=== Crawling: {name} ===")
        review_list = crawl_single(driver, url)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(review_list, f, ensure_ascii=False, indent=4)

        print(f"Saved {len(review_list)} reviews to {output_path}")

    driver.quit()


def crawl_single(driver, url):
    review_list = []
    driver.get(url)
    time.sleep(3)

    for page in range(1, MAX_PAGES + 1):
        print(f"Parsing page {page}...")

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        containers = soup.select('.jlnpc-kuchikomiCassette')

        if not containers:
            print(f"Page {page}: No reviews found, stopping.")
            break

        for container in containers:
            data = extract_review(container)
            if data:
                review_list.append(data)

        print(f"Page {page}: {len(containers)} reviews (total: {len(review_list)})")

        if not go_next_page(driver):
            print("No more pages.")
            break

        time.sleep(3)

    return review_list


def extract_review(container):
    # 타이틀
    title_el = container.select_one('.jlnpc-kuchikomiCassette__lead')
    title = title_el.get_text(strip=True) if title_el else ''

    # 리뷰 본문
    body_el = container.select_one('.jlnpc-kuchikomiCassette__postBody')
    review = body_el.get_text(strip=True) if body_el else ''

    # 총점 (숫자)
    star = 0
    star_el = container.select_one('.jlnpc-kuchikomiCassette__totalRate')
    if star_el:
        m = re.search(r'(\d+)', star_el.get_text())
        if m:
            star = int(m.group(1))

    # 투숙 날짜 (例: "2025年12月")
    date = ''
    date_node = container.find(string=re.compile(r'\d{4}年\d{1,2}月'))
    if date_node:
        m = re.search(r'(\d{4}年\d{1,2}月)', str(date_node))
        if m:
            date = m.group(1)

    # 세부 평점 (部屋, 風呂, 料理, サービス, 清潔感)
    ratings = extract_ratings(container)

    return {
        'title': title,
        'review': review,
        'star': star,
        'date': date,
        'room': ratings.get('room', 0),
        'bath': ratings.get('bath', 0),
        'breakfast': ratings.get('breakfast', 0),
        'dinner': ratings.get('dinner', 0),
        'service': ratings.get('service', 0),
        'cleanliness': ratings.get('cleanliness', 0),
    }


def extract_ratings(container):
    ratings = {}

    # .jlnpc-kuchikomiCassette__rateList 안의 dt/dd 쌍으로 추출
    rate_list = container.select_one('.jlnpc-kuchikomiCassette__rateList')
    if rate_list:
        dts = rate_list.find_all('dt')
        for dt in dts:
            label = dt.get_text(strip=True)
            dd = dt.find_next_sibling('dd')
            if dd:
                for jp_label, field in RATING_MAP.items():
                    if jp_label in label:
                        score = parse_score(dd.get_text(strip=True))
                        if score is not None:
                            ratings[field] = score
                        break

    # fallback: 텍스트에서 regex로 추출
    if not ratings:
        text = container.get_text()
        for jp_label, field in RATING_MAP.items():
            pattern = rf'{re.escape(jp_label)}\s*(\d)'
            match = re.search(pattern, text)
            if match:
                ratings[field] = int(match.group(1))

    return ratings


def parse_score(text):
    text = text.strip()
    if text in ('-', ''):
        return None
    try:
        score = float(text)
        return int(score) if score == int(score) else score
    except ValueError:
        m = re.search(r'(\d+(?:\.\d+)?)', text)
        if m:
            score = float(m.group(1))
            return int(score) if score == int(score) else score
    return None


def go_next_page(driver):
    """次へ 버튼을 클릭하여 다음 페이지로 이동한다."""
    try:
        next_btn = driver.find_element(By.XPATH, "//a[contains(text(), '次へ')]")
        next_btn.click()
        return True
    except Exception:
        pass

    try:
        next_el = driver.find_element(By.XPATH, "//*[contains(@onclick, 'nextPage')]")
        next_el.click()
        return True
    except Exception:
        pass

    return False


if __name__ == '__main__':
    crawl_jalan_reviews()
