import pandas as pd
import re
import os
from datetime import datetime
from review_analysis.preprocessing.base_processor import BaseDataProcessor

class EmartProcessor(BaseDataProcessor):
    """
    이마트 리뷰 데이터를 전처리 및 FE하는 클래스이다.
    전처리 결과를 알기 위해 제거 사유별 통계를 출력한다.
    """

    def __init__(self, input_path: str, output_dir: str) -> None:
        super().__init__(input_path, output_dir)
        self.df: pd.DataFrame = pd.DataFrame()

    def _get_season(self, month: int) -> str:
        """월 정보를 바탕으로 계절 파생변수를 반환한다."""
        if 3 <= month <= 5:
            return 'Spring'
        elif 6 <= month <= 8:
            return 'Summer'
        elif 9 <= month <= 11:
            return 'Fall'
        else:
            return 'Winter'

    def preprocess(self) -> None:
        """
        [EDA 및 전처리]
        1. 헤더가 없는 원본 CSV를 고려하여 컬럼명을 수동 지정하며 로드한다.
        2. 날짜 포맷을 자동으로 인식하도록 수정하여 NaT 발생을 방지한다.
        """
        # 1. 데이터 로드: 원본에 헤더가 없으므로 names를 통해 컬럼명을 직접 부여한다.
        try:
            self.df = pd.read_csv(self.input_path)
        except Exception as e:
            print(f"[Error] 파일 로드 실패: {e}")
            return

        stats = {"초기 데이터 개수": len(self.df)}
        
        # 2. 결측치 제거
        pre_count = len(self.df)
        self.df.dropna(subset=['content', 'date', 'rating'], inplace=True)
        stats["결측치(Null) 제거"] = pre_count - len(self.df)
        
        # 3. 자료형 변환 (날짜 포맷 자동 인식을 위해 format 인자를 제거함)
        pre_count = len(self.df)
        self.df['date'] = pd.to_datetime(self.df['date'], errors='coerce')
        self.df['rating'] = pd.to_numeric(self.df['rating'], errors='coerce')
        self.df.dropna(subset=['date', 'rating'], inplace=True)
        stats["형식 오류(날짜/별점) 제거"] = pre_count - len(self.df)

        # 4. 기간 이상치 처리 (10년 전 이상의 과거 데이터)
        pre_count = len(self.df)
        cutoff_date = pd.Timestamp.now() - pd.DateOffset(years=10)
        self.df = self.df[self.df['date'] > cutoff_date]
        stats["기간 이상치(10년 전) 제거"] = pre_count - len(self.df)
        
        # 5. 별점 이상치 처리 (1~5점 범위 밖)
        pre_count = len(self.df)
        self.df = self.df[(self.df['rating'] >= 1) & (self.df['rating'] <= 5)]
        stats["별점 이상치(범위 밖) 제거"] = pre_count - len(self.df)

        # 6. 텍스트 정제 및 길이 이상치 처리 (2글자 이하)
        pre_count = len(self.df)
        self.df['cleaned_content'] = self.df['content'].apply(
            lambda x: re.sub(r'\s+', ' ', re.sub(r'[^가-힣a-zA-Z0-9\s]', '', 
                      str(x).replace("\n", " ").replace('"', '').replace("'", ""))).strip()
        )
        self.df = self.df[self.df['cleaned_content'].str.len() > 2]
        stats["텍스트 길이 이상치(2자 이하) 제거"] = pre_count - len(self.df)

        # 7. 중복 리뷰 제거
        pre_count = len(self.df)
        self.df.drop_duplicates(subset=['cleaned_content'], inplace=True)
        stats["중복 리뷰 제거"] = pre_count - len(self.df)

        # 최종 요약 출력
        print("\n" + "="*30)
        print(f" [{self.__class__.__name__} 전처리 요약] ")
        print("-"*30)
        for reason, count in stats.items():
            print(f" - {reason}: {count}개")
        print("-"*30)
        print(f" * 최종 남은 데이터: {len(self.df)}개")
        print("="*30 + "\n")

    def feature_engineering(self) -> None:
        """
        [FE 및 벡터화 준비]
        계절 파생 변수 및 TF-IDF용 토큰을 생성한다.
        """
        self.df['month'] = self.df['date'].dt.month
        self.df['season'] = self.df['month'].apply(self._get_season)
        
        self.df['tokens'] = self.df['cleaned_content'].apply(
            lambda x: ' '.join(re.findall(r'[가-힣a-zA-Z0-9]+', x))
        )
        
        self.df['review_length'] = self.df['cleaned_content'].apply(len)

    def save_to_database(self) -> None:
        """
        전처리 결과를 CSV 파일로 저장한다.
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        save_path = os.path.join(self.output_dir, "preprocessed_reviews_emart.csv")
        self.df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"[Success] 이마트 파일 저장 완료: {save_path}")