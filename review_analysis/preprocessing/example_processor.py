from review_analysis.preprocessing.base_processor import BaseDataProcessor

class ExampleProcessor(BaseDataProcessor):
    def __init__(self, input_path: str, output_path: str):
        super().__init__(input_path, output_path)

    # content(리뷰 내용)를 인자로 받을 수 있게 수정
    def preprocess(self, content: str):
        # 일단은 받은 내용을 그대로 돌려주도록(pass 대신 return) 만듦
        return content
    
    # data(전체 데이터 dictionary)를 인자로 받을 수 있게 수정
    def feature_engineering(self, data: dict):
        return data

    def save_to_database(self):
        pass