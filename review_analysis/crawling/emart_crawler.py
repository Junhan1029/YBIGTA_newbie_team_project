import time
import pandas as pd
from typing import List, Dict 
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from review_analysis.crawling.base_crawler import BaseCrawler
from utils.logger import setup_logger

class EmartCrawler(BaseCrawler):
    """
    이마트몰(SSG.com)의 상품 리뷰 데이터를 수집하는 크롤러 클래스입니다.

    review_analysis.crawling.base_crawler.BaseCrawler를 상속받아 구현되었습니다.
    Selenium을 사용하여 동적 페이지를 제어하고, BeautifulSoup을 사용하여 HTML을 파싱합니다.
    봇 탐지 회피 기술과 500개 데이터 수집 제한 로직이 포함되어 있습니다.
    """
    def __init__(self, output_dir: str):
        """
        크롤러 인스턴스를 초기화합니다.

        Args:
            output_dir (str): 수집된 데이터(CSV)가 저장될 디렉토리 경로.
        
        Attributes:
            logger: 로그 출력을 위한 로거 인스턴스
            data (List[Dict[str, str]]): 수집된 리뷰 데이터를 저장하는 리스트
            target_url (str): 크롤링할 대상 상품 페이지 URL
            driver (webdriver.Chrome): Selenium 크롬 드라이버 인스턴스
        """
        super().__init__(output_dir)
        self.logger = setup_logger()
        self.data: List[Dict[str, str]] = [] 
        self.target_url = "https://emart.ssg.com/item/itemView.ssg?itemId=1000523382272&siteNo=6001&salestrNo=6005"
        self.driver = None

    def start_browser(self):
        """
        Selenium WebDriver(Chrome)를 설정하고 실행합니다.

        이마트몰의 봇 탐지를 우회하기 위해 다음과 같은 설정을 적용합니다:
        1. User-Agent 변경: 일반 브라우저 사용자로 위장
        2. AutomationControlled 비활성화: 자동화 도구 탐지 방지
        3. 창 최대화: 반응형 웹 요소 가림 방지
        """
        self.logger.info("브라우저 실행 중...")
        options = Options()
        # [봇 탐지 회피: 필수 2종 세트]
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(5)

    def scrape_reviews(self):
        """
        실제 크롤링 로직을 수행하는 핵심 메서드입니다.

        [동작 순서]
        1. 타겟 URL로 이동하여 리뷰 탭을 클릭합니다.
        2. 페이지네이션을 순회하며 리뷰 데이터를 수집합니다.
        3. BeautifulSoup을 통해 평점(별점/숨겨진 텍스트), 날짜, 본문을 추출합니다.
        4. 데이터가 500개 이상 모이면 수집을 즉시 중단합니다.

        Note:
            - 평점의 경우 '.cdtl_star_on' 클래스뿐만 아니라, '.blind' 태그 내의 텍스트("5점")까지 전수 조사하여 결측치를 최소화합니다.
            - 페이지 이동은 자바스크립트 클릭을 사용하여 안정성을 높였습니다.
        """
        if not self.driver:
            self.start_browser()
        
        try:
            self.logger.info(f"접속 시도: {self.target_url}")
            self.driver.get(self.target_url)
            
            # [1] 리뷰 탭 클릭 (심플하게 변경)
            self.logger.info("리뷰 탭 이동 중...")
            review_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='cdtl_ItemComment']"))
            )
            self.driver.execute_script("arguments[0].click();", review_tab) # JS 클릭이 제일 확실함
            time.sleep(2)

            # [2] 리스트 로딩 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "item_rvw_list"))
            )

            # [3] 데이터 수집
            page_num = 1
            
            while True:
                time.sleep(1.5) # 페이지 로딩 대기 (1.5초면 충분)
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                rows = soup.select("#item_rvw_list > li")
                
                if not rows:
                    self.logger.warning("리뷰 데이터가 없습니다. 종료.")
                    break
                
                new_count = 0
                for row in rows:
                    if len(self.data) >= 500: break # 500개 제한

                    # (1) 평점 추출 (핵심 로직 유지)
                    rating = "N/A"
                    # 일반적인 경우
                    star_elem = row.select_one(".cdtl_star_on .blind em") or row.select_one(".star_point .blind")
                    if star_elem:
                        rating = star_elem.text.strip()
                    # 숨겨진 텍스트 전수 조사 (N/A일 때만 실행)
                    elif rating == "N/A":
                        for t in row.select(".blind"):
                            if "점" in t.text:
                                rating = t.text.replace("점", "").strip()
                                break
                    
                    # (2) 내용 추출
                    desc_elem = row.select_one(".rvw_item_text") or row.select_one(".cdtl_txt_desc")
                    content = desc_elem.text.strip() if desc_elem else ""
                    
                    # (3) 날짜 추출
                    date_elem = row.select_one(".rvw_item_date") or row.select_one(".cdtl_info_date")
                    date = date_elem.text.strip() if date_elem else "N/A"
                    
                    if content:
                        self.data.append({"rating": rating, "date": date, "content": content})
                        new_count += 1
                
                self.logger.info(f"Page {page_num}: {new_count}개 수집 (누적 {len(self.data)}개)")
                
                if len(self.data) >= 500:
                    self.logger.info("목표 달성 (500개)!")
                    break

                # [4] 페이지 이동 (심플하게 변경)
                try:
                    # 다음 페이지 숫자 버튼 찾기
                    next_btn = self.driver.find_element(By.XPATH, f"//*[@id='comment_navi_area']//a[text()='{page_num + 1}']")
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    page_num += 1
                except:
                    # 숫자 없으면 화살표(>) 찾기
                    try:
                        next_arrow = self.driver.find_element(By.CLASS_NAME, "rvw_btn_next")
                        if "disabled" in next_arrow.get_attribute("class"):
                            break # 끝
                        self.driver.execute_script("arguments[0].click();", next_arrow)
                        page_num += 1
                        time.sleep(2)
                    except:
                        break # 화살표도 없으면 진짜 끝

        except Exception as e:
            self.logger.error(f"에러 발생: {e}")
        
        finally:
            self.driver.quit()

    def save_to_database(self):
        """
        수집된 메모리 상의 데이터(self.data)를 CSV 파일로 저장합니다.

        - 저장 경로: {self.output_dir}/reviews_emart.csv
        - 인코딩: utf-8-sig (엑셀 한글 깨짐 방지)
        - 저장 컬럼: rating, date, content

        데이터가 없을 경우 경고 로그를 출력하고 저장하지 않습니다.
        """
        if not self.data: return
        df = pd.DataFrame(self.data)
        path = f"{self.output_dir}/reviews_emart.csv"
        df.to_csv(path, index=False, encoding='utf-8-sig')
        self.logger.info(f"저장 완료: {path}")  