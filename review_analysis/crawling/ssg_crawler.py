import time
import pandas as pd # type: ignore
from typing import List, Dict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# BaseCrawler 경로에 맞게 임포트
from review_analysis.crawling.base_crawler import BaseCrawler

class SSGCrawler(BaseCrawler):
    """
    SSG.com 상품 리뷰를 크롤링하는 클래스입니다.
    
    Attributes:
        output_dir (str): 크롤링 결과를 저장할 디렉토리 경로
        base_url (str): 크롤링할 대상 상품 URL
        driver (webdriver.Chrome): Selenium 웹 드라이버 인스턴스
        reviews (List[Dict]): 수집된 리뷰 데이터를 저장하는 리스트
        target_count (int): 목표 수집 리뷰 개수 (기본값: 500)
    """
    def __init__(self, output_dir: str):
        """
        SSGCrawler 초기화 메서드입니다.
        
        Args:
            output_dir (str): 데이터 저장 경로
        """
        super().__init__(output_dir)
        self.base_url = "https://shinsegaemall.ssg.com/item/itemView.ssg?itemId=1000523382272"
        self.driver = None
        self.reviews: List[Dict] = []
        self.target_count = 500

    def start_browser(self):
        """
        Selenium Chrome 웹 드라이버를 설정하고 실행합니다.
        
        - 윈도우 사이즈 설정 (1920x1080)
        - User-Agent 설정으로 봇 탐지 회피
        """
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        # 크롤링 차단 방지용 User-Agent 설정
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)

    def scrape_reviews(self):
        """
        SSG.com 상품 페이지에서 리뷰를 수집하는 메인 로직입니다.
        
        Process:
            1. 브라우저 실행 및 상품 페이지 접속
            2. '고객리뷰' 탭 클릭
            3. 현재 페이지의 리뷰(별점, 날짜, 내용) 수집
            4. 목표 개수(target_count)에 도달할 때까지 페이지네이션 반복
            5. 크롤링 종료 후 브라우저 종료
            
        Note:
            - SSG 페이지네이션의 'fn_GoCommentPage' 자바스크립트 함수 호출 구조를 분석하여 
              다음 페이지 버튼을 식별하고 클릭합니다.
            - HTML 구조 변경에 유연하게 대응하기 위해 예외 처리가 포함되어 있습니다.
        """
        if not self.driver:
            self.start_browser()
        
        print(f"Update: {self.base_url} 접속 중...")
        self.driver.get(self.base_url)
        time.sleep(3)

        try:
            # 1. '고객리뷰' 탭 클릭
            review_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#cdtl_ItemComment']"))
            )
            self.driver.execute_script("arguments[0].click();", review_tab)
            print("Update: 고객리뷰 탭 클릭 완료")
            time.sleep(2)

            page_num = 1
            
            while len(self.reviews) < self.target_count:
                # 리뷰 리스트 로딩 대기
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "item_rvw_list"))
                    )
                    time.sleep(1) # 렌더링 안정화
                except:
                    print("Warning: 리뷰 리스트 로딩 실패, 재시도합니다.")
                    time.sleep(2)

                # 파싱
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                review_list = soup.select("#item_rvw_list > li")

                if not review_list:
                    print("Warning: 리뷰가 더 이상 없습니다.")
                    break

                for review in review_list:
                    try:
                        # [수정됨] 날짜 추출 로직 개선 (이미지 참고)
                        # 클래스명: rvw_item_date
                        date_elem = review.select_one(".rvw_item_date")
                        date = date_elem.get_text(strip=True) if date_elem else ""
                        
                        # 내용 추출
                        content_elem = review.select_one(".rvw_item_text")
                        content = content_elem.get_text(strip=True) if content_elem else ""

                        # 별점 추출
                        star_elem = review.select_one(".rvw_item_star .blind")
                        star = star_elem.get_text(strip=True).replace("별 5개 중", "").replace("개", "").strip() if star_elem else "5"

                        # 내용이 있으면 추가
                        if content:
                            self.reviews.append({
                                "star": star,
                                "date": date,
                                "content": content
                            })
                    except Exception:
                        continue

                print(f"Update: {page_num}페이지 완료. 누적 {len(self.reviews)}개")

                if len(self.reviews) >= self.target_count:
                    break

                # 2. 페이지네이션 (이미지 분석 반영: 작은따옴표 포함)
                next_page_num = page_num + 1
                try:
                    # [Image 1, 2 분석] onclick="fn_GoCommentPage('2')" 형태임
                    # CSS Selector에 따옴표를 이스케이프(\")하여 정확히 넣음
                    selector = f"#comment_navi_area a[onclick*=\"fn_GoCommentPage('{next_page_num}')\"]"
                    
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    
                    # JS로 클릭 (가려짐 방지)
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    
                    page_num += 1
                    time.sleep(2) # 페이지 로딩 대기

                except TimeoutException:
                    print("Update: 더 이상 다음 페이지 버튼을 찾을 수 없습니다.")
                    break
                except Exception as e:
                    print(f"Error: 페이지 이동 중 에러 - {e}")
                    break

        except Exception as e:
            print(f"Error: 크롤링 전체 프로세스 중 오류 - {e}")
        finally:
            self.driver.quit()

    def save_to_database(self):
        """
        수집된 리뷰 데이터를 CSV 파일로 저장합니다.
        
        Process:
            1. 출력 디렉토리가 없으면 생성
            2. pandas DataFrame 생성
            3. CSV 파일로 저장 (utf-8-sig 인코딩 사용)
            
        Output:
            - {output_dir}/reviews_ssg.csv 파일 생성
        """
        import os
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        df = pd.DataFrame(self.reviews)
        file_path = os.path.join(self.output_dir, "reviews_ssg.csv")
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"Success: 총 {len(df)}개의 리뷰 저장 완료 -> {file_path}")