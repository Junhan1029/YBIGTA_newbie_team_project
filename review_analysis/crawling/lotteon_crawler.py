import os
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from review_analysis.crawling.base_crawler import BaseCrawler
from typing import List, Dict, Any

class LotteonCrawler(BaseCrawler):
    """
    롯데온 제품 리뷰를 크롤링하는 클래스입니다.
    BaseCrawler를 상속받아 구현되었습니다.
    """
    def __init__(self, output_dir: str):
        super().__init__(output_dir)
        # 크롤링 URL - 롯데온 코카콜라 제로
        self.base_url = "https://www.lotteon.com/m/product/LD755642049?sitmNo=LD755642049_0&mall_no=1&entryPoint=ad&dp_infw_cd=SCH%5Ecpc_sad%5E%EC%BD%94%EC%B9%B4%EC%BD%9C%EB%9D%BC%20%EC%A0%9C%EB%A1%9C&areaCode=AD&clickId=S126912062382"
        self.reviews: List[Dict[str, Any]] = []
        self.target_count = 500  # 목표 수집 개수

    def start_browser(self):
        """
        Selenium WebDriver를 실행하고 설정된 URL로 이동합니다.
        """
        try:
            # 드라이버가 초기화되지 않았다면 초기화
            if not hasattr(self, 'driver'):
                self.driver = webdriver.Chrome()
            
            self.driver.get(self.base_url)
            self.driver.implicitly_wait(10)
            time.sleep(3)  # 페이지 로딩 대기
            
        except Exception as e:
            print(f"브라우저 시작 중 오류 발생: {e}")

    def scrape_reviews(self):
        """
        리뷰 데이터를 수집합니다.
        - 리뷰 내용이 있는 데이터만 수집 (빈 내용은 스킵)
        - 700개 이상 수집 시 종료
        - 페이지네이션 처리
        """
        # 데이터 수집 시작 전 브라우저 실행
        self.start_browser()

        print(f"크롤링 시작: 목표 {self.target_count}개")
        
        # 리뷰 리스트가 보일 때까지 대기
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.reviewList"))
            )
        except TimeoutException:
            print("리뷰 목록을 찾을 수 없습니다. 페이지 구조를 확인해주세요.")
            return

        current_page = 1
        
        while len(self.reviews) < self.target_count:
            try:
                # 현재 페이지의 리뷰 리스트 로딩 대기
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.reviewList"))
                )
                
                # 리뷰 요소 가져오기
                review_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.reviewList")
                
                for element in review_elements:
                    # 목표 개수 달성 시 중단
                    if len(self.reviews) >= self.target_count:
                        break

                    try:
                        # 1. 리뷰 내용 추출 (span.texting)
                        try:
                            content_element = element.find_element(By.CSS_SELECTOR, "span.texting")
                            content = content_element.text.strip()
                        except NoSuchElementException:
                            content = ""

                        # 텍스트가 없는 리뷰는 수집 제외
                        if not content:
                            continue

                        # 2. 별점 추출(em)
                        try:
                            rating_element = element.find_element(By.CSS_SELECTOR, "em")
                            rating = rating_element.text.strip()
                        except NoSuchElementException:
                            rating = "N/A"

                        # 3. 날짜 추출(span.date)
                        try:
                            date_element = element.find_element(By.CSS_SELECTOR, "span.date")
                            date = date_element.text.strip()
                        except NoSuchElementException:
                            date = "N/A"

                        # 데이터 저장
                        self.reviews.append({
                            "rating": rating,
                            "date": date,
                            "content": content
                        })
                        
                    except Exception as e:
                        continue

                print(f"현재 수집된 리뷰 개수: {len(self.reviews)} / {self.target_count} (페이지: {current_page})")

                if len(self.reviews) >= self.target_count:
                    break

                # 페이지 넘기기
                if not self._move_to_next_page(current_page):
                    print("더 이상 다음 페이지가 없습니다.")
                    break
                
                current_page += 1
                
                # 차단 방지를 위한 랜덤 대기
                time.sleep(random.uniform(1.5, 2.5))

            except Exception as e:
                print(f"크롤링 중 오류 발생: {e}")
                break
        
        # 크롤링 완료 후 브라우저 종료하기
        if hasattr(self, 'driver'):
            self.driver.quit()

    def _move_to_next_page(self, current_page_num):
        """
        다음 페이지로 이동하는 헬퍼 메서드입니다.
        현재 페이지 번호 + 1 버튼을 찾거나, 다음 그룹(>) 버튼을 찾습니다.
        """
        next_page_num = current_page_num + 1
        
        try:
            # 1. 숫자 버튼 클릭 시도 (현재 1페이지면 2페이지 버튼 클릭...)
            target_xpath = f"//div[contains(@class, 'paging')]//a[contains(text(), '{next_page_num}')]"
            
            try:
                next_btn = self.driver.find_element(By.XPATH, target_xpath)
                self.driver.execute_script("arguments[0].click();", next_btn)
                return True
            except NoSuchElementException:
                pass 

            # 2. 다음(>) 화살표 버튼 클릭(페이지 그룹 이동)
            next_arrow_xpaths = [
                "//a[contains(@class, 'next')]",
                "//a[contains(@class, 'Next')]",
                "//button[contains(@class, 'next')]",
                "//a[contains(text(), '>')]"
            ]

            for xpath in next_arrow_xpaths:
                try:
                    next_arrow = self.driver.find_element(By.XPATH, xpath)
                    self.driver.execute_script("arguments[0].click();", next_arrow)
                    return True
                except NoSuchElementException:
                    continue
            
            return False

        except Exception:
            return False

    def save_to_database(self):
        """
        수집된 데이터를 CSV 파일로 저장합니다.
        경로가 없으면 생성하고, 파일명은 reviews_Lotteon.csv로 저장합니다.
        """
        if not self.reviews:
            print("저장할 데이터가 없습니다.")
            return

        try:
            # 1. output_dir 경로가 존재하는지 확인 및 생성
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            # 2. 경로 결합(OS 호환성 확보)
            file_path = os.path.join(self.output_dir, "reviews_Lotteon.csv")

            # 3. CSV 저장(한글 깨짐 방지)
            df = pd.DataFrame(self.reviews)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            print(f"데이터 저장 완료: {file_path}")
            
        except Exception as e:
            print(f"데이터 저장 중 오류 발생: {e}")