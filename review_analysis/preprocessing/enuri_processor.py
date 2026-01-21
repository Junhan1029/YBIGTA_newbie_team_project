import pandas as pd
import re
import os
from datetime import datetime

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

from review_analysis.preprocessing.base_processor import BaseDataProcessor

class EnuriProcessor(BaseDataProcessor):
    """
    에누리 리뷰 데이터를 전처리 및 FE하는 클래스이다.
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
        형식 오류 발생 시 해당 데이터를 터미널에 출력한다.
        """
        # 1. 데이터 로드
        try:
            self.df = pd.read_csv(self.input_path)
        except Exception as e:
            print(f"파일 로드 실패: {e}")
            return

        stats = {"초기 데이터 개수": len(self.df)}
        
        # 2. 결측치 제거
        pre_count = len(self.df)
        self.df.dropna(subset=['content', 'date', 'rating'], inplace=True)
        stats["결측치(Null) 제거"] = pre_count - len(self.df)
        
        # 3. 자료형 변환 및 형식 오류 데이터 출력
        pre_count = len(self.df)
        
        # 변환 시도 (오류는 NaT/NaN으로 처리)
        temp_date = pd.to_datetime(self.df['date'], format='%Y.%m.%d', errors='coerce')
        temp_rating = pd.to_numeric(self.df['rating'], errors='coerce')
        
        # 형식 오류가 발생한 행들(원래 null이 아니었으나 변환 후 null이 된 경우) 추출
        date_errors = self.df[temp_date.isna() & self.df['date'].notna()]
        rating_errors = self.df[temp_rating.isna() & self.df['rating'].notna()]
        
        # 터미널에 오류 데이터 출력
        if not date_errors.empty:
            print("\n" + "!"*10 + " [날짜 형식 오류 데이터] " + "!"*10)
            print(date_errors[['date', 'content']].head()) # 너무 많을 수 있으므로 상위 일부만 출력
            print(f"총 {len(date_errors)}건의 날짜 오류 발견")
            
        if not rating_errors.empty:
            print("\n" + "!"*10 + " [별점 형식 오류 데이터] " + "!"*10)
            print(rating_errors[['rating', 'content']].head())
            print(f"총 {len(rating_errors)}건의 별점 오류 발견")

        # 실제 변환 결과 반영 및 결측치 제거
        self.df['date'] = temp_date
        self.df['rating'] = temp_rating
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
                      str(x).replace("\n", " "))).strip()
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
        [Feature Engineering 단계]
        시계열 파생변수 생성, 텍스트 토큰화, 리뷰 길이(review_length) 계산, 그리고 LDA 토픽 모델링을 수행한다.

        이때 토픽 모델링은 CountVectorizer로 벡터화(BOW) 수행하여 LDA 모델을 통해 잠재된 3가지 토픽을 추출한다.
        데이터 저장 시 단순 숫자가 아닌 '토픽번호(핵심키워드)' 형태로 'topic_id' 컬럼을 생성한다.
        (예: 0(배송_빠름_기사님))
        """
        if self.df.empty: return
        print(" -> Feature Engineering 수행 중...")

        # 1. 시계열 파생변수 
        self.df['month'] = self.df['date'].dt.month
        self.df['season'] = self.df['month'].apply(self._get_season)

        # 2. 토큰화
        self.df['tokens'] = self.df['cleaned_content'].apply(lambda x: ' '.join(re.findall(r'[가-힣a-zA-Z0-9]+', x)))
        self.df['review_length'] = self.df['cleaned_content'].apply(len)

        # ---------------------------------------------------------
        # LDA 토픽 모델링
        # ---------------------------------------------------------
        print(" -> 벡터화(BOW) 및 토픽 모델링(LDA) 수행 중...")
        
        # (1) 벡터화
        vectorizer = CountVectorizer(max_features=1000, min_df=2)
        vectorized_data = vectorizer.fit_transform(self.df['tokens'])
        
        # (2) LDA 모델링
        lda_model = LatentDirichletAllocation(n_components=3, random_state=42)
        topic_output = lda_model.fit_transform(vectorized_data)
        
        # (3) 토픽 ID 및 라벨 생성
        topic_indices = topic_output.argmax(axis=1)
        feature_names = vectorizer.get_feature_names_out()
        topic_label_dict = {}
        
        print(" -> 토픽 라벨 생성 중...")
        for topic_idx, topic in enumerate(lda_model.components_):
            top_features_ind = topic.argsort()[:-4:-1]
            top_words = [feature_names[i] for i in top_features_ind]
            
            # 라벨 포맷: ex) 0(배송_빠름_기사님)
            keywords_str = "_".join(top_words)
            label = f"{topic_idx}({keywords_str})"
            topic_label_dict[topic_idx] = label
            print(f"    Topic {topic_idx} -> {label}")
        
        self.df['topic_id'] = [topic_label_dict[idx] for idx in topic_indices]
        print(" -> 'topic_id' 컬럼 생성 완료")


    def save_to_database(self) -> None:
        """전처리 결과를 CSV 파일로 저장한다."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        save_path = os.path.join(self.output_dir, "preprocessed_reviews_Enuri.csv")
        self.df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"[Success] 에누리 파일 저장 완료: {save_path}")