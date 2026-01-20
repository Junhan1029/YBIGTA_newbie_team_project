import os
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options  
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from review_analysis.crawling.base_crawler import BaseCrawler
from typing import List, Dict, Any

class EnuriCrawler(BaseCrawler):
    """
    에누리 제품 리뷰를 크롤링하는 클래스입니다.
    BaseCrawler를 상속받아 구현되었습니다.
    """
    def __init__(self, output_dir: str):
        super().__init__(output_dir)
        # 크롤링 URL - 에누리 코카콜라 제로 (사용자가 제공한 링크)
        self.base_url = "https://www.enuri.com/detail.jsp?modelno=40629426"
        self.reviews: List[Dict[str, Any]] = []
        self.target_count = 500  # 목표 수집 개수

    def start_browser(self):
        """
        [최적화 적용] Selenium WebDriver를 실행하고 설정된 URL로 이동합니다.
        """
        try:
            if not hasattr(self, 'driver'):
                options = Options()
                
                # [속도 향상 1] Headless 모드 (창을 띄우지 않음)
                # 오류 확인을 위해 화면을 보고 싶다면 아래 줄을 주석 처리하세요.
                options.add_argument("--headless=new") 
                
                # [속도 향상 2] 이미지 로딩 차단 (가장 큰 속도 향상 요인)
                options.add_argument("--blink-settings=imagesEnabled=false")
                
                # [속도 향상 3] 리소스 로딩 전략 수정 (HTML만 로드되면 바로 시작)
                options.page_load_strategy = 'eager'
                
                # 기타 안정성 옵션
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")

                self.driver = webdriver.Chrome(options=options)
            
            self.driver.get(self.base_url)
            self.driver.implicitly_wait(5) # 대기 시간 단축 (10 -> 5)
            # time.sleep(3) -> 제거 (WebDriverWait이 처리하므로 불필요)
            
        except Exception as e:
            print(f"브라우저 시작 중 오류 발생: {e}")

    def scrape_reviews(self):
        """
        리뷰 데이터를 수집합니다.
        """
        self.start_browser()
        print(f"에누리 크롤링 시작: 목표 {self.target_count}개")
        
        # 명시적 대기 시간 설정
        wait = WebDriverWait(self.driver, 10)

        # 리뷰 리스트가 로딩될 때까지 대기
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.tx_sub")))
        except TimeoutException:
            print("리뷰 목록을 찾을 수 없습니다. 페이지 구조를 확인해주세요.")
            return

        current_page = 1
        
        while len(self.reviews) < self.target_count:
            try:
                # [속도 향상] 무조건적인 2초 대기 대신, 요소를 찾을 때까지 기다림
                # 페이지 넘김 후 DOM이 꼬이는 것을 방지하기 위해 짧은 대기만 유지
                time.sleep(0.5)
                
                # 리뷰 컨테이너 찾기
                review_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.review_body, ul.review_list_ul > li")
                
                if not review_elements:
                    review_elements = self.driver.find_elements(By.XPATH, "//span[contains(@class,'tx_sub')]/ancestor::li")

                for element in review_elements:
                    if len(self.reviews) >= self.target_count:
                        break

                    try:
                        # 1. 리뷰 내용 추출
                        try:
                            content = element.find_element(By.CSS_SELECTOR, "span.tx_sub").text.strip()
                        except NoSuchElementException:
                            content = ""

                        if not content:
                            continue

                        # 2. 별점 추출
                        try:
                            rating = element.find_element(By.CSS_SELECTOR, "p.tx_aval").text.strip()
                        except NoSuchElementException:
                            rating = "N/A"

                        # 3. 날짜 추출
                        date = "N/A"
                        try:
                            # li 태그 전체를 돌지 않고 필요한 텍스트만 빠르게 찾도록 최적화 가능하나, 
                            # 기존 로직 안정성을 위해 유지하되 break로 즉시 탈출
                            li_tags = element.find_elements(By.TAG_NAME, "li")
                            for li in li_tags:
                                li_text = li.text.strip()
                                if "." in li_text and len(li_text) <= 12:
                                    date = li_text
                                    break
                        except NoSuchElementException:
                            date = "N/A"

                        self.reviews.append({
                            "rating": rating,
                            "date": date,
                            "content": content
                        })
                        
                    except Exception:
                        continue

                print(f"현재 수집된 리뷰 개수: {len(self.reviews)} / {self.target_count} (페이지: {current_page})")

                if len(self.reviews) >= self.target_count:
                    break

                # 페이지 넘기기
                if not self._move_to_next_page(current_page):
                    print("더 이상 다음 페이지가 없습니다.")
                    break
                
                current_page += 1
                
                # [속도 향상] 랜덤 대기 시간 단축 (Headless 모드에서는 더 빨라도 안전함)
                time.sleep(random.uniform(0.5, 1.0))

            except Exception as e:
                print(f"크롤링 중 오류 발생: {e}")
                break
        
        if hasattr(self, 'driver'):
            self.driver.quit()

    def _move_to_next_page(self, current_page_num):
        """
        다음 페이지로 이동하는 헬퍼 메서드
        """
        next_page_num = current_page_num + 1
        
        try:
            # 1. 숫자 버튼 클릭 시도
            target_xpath = f"//button[contains(@class, 'p_num') and text()='{next_page_num}']"
            
            try:
                next_btn = self.driver.find_element(By.XPATH, target_xpath)
                self.driver.execute_script("arguments[0].click();", next_btn)
                return True
            except NoSuchElementException:
                pass 

            # 2. 다음(>) 버튼 클릭
            try:
                next_arrow = self.driver.find_element(By.CSS_SELECTOR, "button.btn.btn__next")
                if next_arrow.is_enabled():
                    self.driver.execute_script("arguments[0].click();", next_arrow)
                    return True
            except NoSuchElementException:
                pass
            
            return False

        except Exception:
            return False

    def save_to_database(self):
        """
        수집된 데이터를 CSV 파일로 저장합니다.
        """
        if not self.reviews:
            print("저장할 데이터가 없습니다.")
            return

        try:
            current_file_path = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
            target_dir = os.path.join(project_root, "database")

            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            file_path = os.path.join(target_dir, "reviews_Enuri.csv")

            df = pd.DataFrame(self.reviews)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print(f"데이터 저장 완료: {file_path}")
            
        except Exception as e:
            print(f"데이터 저장 중 오류 발생: {e}")