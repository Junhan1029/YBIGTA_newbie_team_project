from st_app.rag.retriever import get_relevant_documents
from st_app.rag.prompt import REVIEW_PROMPT
from st_app.rag.llm import get_llm
from st_app.utils.state import GraphState

def review_node(state: GraphState):
    """
    FAISS 기반 리뷰 RAG 응답을 생성하는 노드이다.
    """
    print("---리뷰 RAG 응답 생성 (RAG Review Node)---")

    # 1. 사용자 질문 추출
    user_message = state["messages"][-1].content

    # 2. retriever.py를 호출하여 관련 리뷰 문맥(Context) 가져오기
    context = get_relevant_documents(user_message)

    # 3. LLM 설정
    llm = get_llm()

    # 4. prompt.py에 정의된 RAG 전용 프롬프트 사용
    # 5. 체인 실행 및 응답 생성
    chain = REVIEW_PROMPT | llm
    response = chain.invoke({
        "context": context, 
        "question": user_message
    })
    
    # 6. 상태 업데이트 및 반환
    # 검색된 컨텍스트를 state의 context 필드에 저장하여 투명성을 확보한다.
    return {
        "messages": [response],
        "context": context
    }