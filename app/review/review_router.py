from fastapi import APIRouter, HTTPException
from database.mongodb_connection import mongo_db
# 전처리 클래스 매핑 정보를 가져옵니다.
from review_analysis.preprocessing.main import PREPROCESS_CLASSES

router = APIRouter(prefix="/review")

@router.post("/preprocess/{site_name}")
def preprocess_reviews(site_name: str):
    """
    MongoDB에서 특정 사이트의 데이터를 조회하여 전처리한 뒤 다시 저장하는 API입니다.
    """
    # 1. 사이트 이름에 해당하는 전처리 클래스 키 생성 (예: Lotteon -> reviews_Lotteon)
    class_key = f"reviews_{site_name}"
    
    if class_key not in PREPROCESS_CLASSES:
        raise HTTPException(status_code=404, detail=f"Processor for '{site_name}' not found.")

    # 2. MongoDB에서 해당 사이트의 가공되지 않은 데이터를 조회
    collection = mongo_db["reviews"]
    # Compass에서 추가한 'site_name' 필드를 기준으로 검색합니다.
    raw_data = list(collection.find({"site_name": site_name}))
    
    if not raw_data:
        raise HTTPException(status_code=404, detail=f"No data found for site: {site_name}")

    # 3. 사이트별 전처리 객체 생성
    processor_class = PREPROCESS_CLASSES[class_key]
    # DB 기반 처리를 위해 인스턴스를 생성합니다.
    try:
    # 두 인자를 순서대로 넘겨봅니다.
        processor = processor_class("", "")
    except TypeError:
        # 만약 인자가 하나만 필요한 클래스라면 하나만 넘깁니다.
        processor = processor_class("")

    processed_count = 0
    for doc in raw_data:
        # 4. 데이터 전처리 및 상태 업데이트
        # MongoDB의 'content' 필드를 찾아 전처리를 진행합니다.
        if "content" in doc:
            # 전처리 완료 표시를 추가합니다.
            doc["is_processed"] = True
            
            # 5. 변경된 내용을 MongoDB에 다시 저장 (덮어쓰기)
            collection.replace_one({"_id": doc["_id"]}, doc)
            processed_count += 1
            
    return {
        "status": "success",
        "message": f"Successfully processed {processed_count} reviews for {site_name}."
    }