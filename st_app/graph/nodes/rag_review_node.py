from langchain_upstage import ChatUpstage
from langchain_core.prompts import PromptTemplate
from st_app.rag.retriever import get_relevant_documents
from st_app.utils.state import GraphState

def review_node(state: GraphState):
    """
    FAISS 기반 리뷰 RAG 응답을 생성하는 노드이다.
    """
    print("---리뷰 RAG 응답 생성 (RAG Review Node)---")
    
    # 1. 사용자 질문 추출
    user_message = state["messages"][-1].content
    
    # 2. retriever.py를 호출하여 관련 리뷰 문맥(Context) 가져오기
    # k값은 명세서 권장 사항인 3으로 설정되어 있다.
    context = get_relevant_documents(user_message)
    
    # 3. LLM 설정 (Upstage Solar-1-Mini)
    llm = ChatUpstage(model="solar-1-mini-chat")
    
    # 4. RAG 전용 프롬프트 구성
    prompt = PromptTemplate(
        template="""당신은 독자들의 감상을 분석하여 전달하는 도서 리뷰 전문가입니다. 
        제공된 [리뷰 데이터]를 바탕으로 사용자의 질문에 답변하세요.
        
        [리뷰 데이터]: {context}
        
        사용자 질문: {question}
        
        답변 가이드라인:
        - 반드시 제공된 리뷰 데이터에 있는 내용만을 바탕으로 답변해야 한다.
        - 사람들의 전반적인 반응이나 감상을 요약해서 전달한다.
        - "~이다." 말투를 사용하여 정중하고 객관적으로 작성한다.
        - 만약 관련 리뷰 내용이 없다면, "해당 도서에 대한 관련 리뷰를 찾을 수 없다."라고 답변한다.
        """,
        input_variables=["context", "question"],
    )
    
    # 5. 체인 실행 및 응답 생성
    chain = prompt | llm
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