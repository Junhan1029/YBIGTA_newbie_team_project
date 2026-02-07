from langchain_community.vectorstores import FAISS
from st_app.rag.llm import get_embeddings

def get_relevant_documents(query, k=3):
    """
    사용자의 질문과 가장 유사한 리뷰 문단을 FAISS DB에서 검색하여 반환한다.
    """

    # 1. Upstage 임베딩 모델 설정 (llm.py에서 관리)
    embeddings = get_embeddings()
    
    # 2. 저장된 FAISS 인덱스 경로 설정
    # 명세서에 따라 st_app/db/faiss_index/ 폴더를 참조한다.
    index_path = "st_app/db/faiss_index"
    
    # 3. 로컬에 저장된 FAISS 인덱스 로드
    # allow_dangerous_deserialization=True는 로컬 파일 신뢰 시 사용한다.
    vector_store = FAISS.load_local(
        index_path, 
        embeddings, 
        allow_dangerous_deserialization=True
    )
    
    # 4. 유사도 검색 수행 (Top-k)
    # k=3~5 권장 사항에 따라 관련성이 높은 문서를 가져온다.
    docs = vector_store.similarity_search(query, k=k)
    
    # 5. 검색된 문서들의 내용을 하나의 텍스트로 합쳐서 반환한다.
    context = "\n\n".join([doc.page_content for doc in docs])
    
    return context