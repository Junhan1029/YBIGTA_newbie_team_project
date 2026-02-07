import json
from langchain_core.prompts import PromptTemplate
from st_app.utils.state import GraphState
from st_app.rag.llm import get_llm

def info_node(state: GraphState):
    """
    subjects.json에서 도서 정보를 검색하여 답변을 생성하는 노드이다.
    """
    print("---도서 정보 검색 및 응답 생성 (Subject Info Node)---")

    # 1. subjects.json 데이터 로드
    # 명세서의 경로(st_app/db/subject_information/subjects.json)를 참조한다.
    with open("st_app/db/subject_information/subjects.json", "r", encoding="utf-8") as f:
        subjects_data = json.load(f)

    # 2. 사용자 질문 및 이전 상태 확인
    user_message = state["messages"][-1].content

    # 3. LLM을 사용하여 질문에서 언급된 도서 식별 및 정보 추출
    llm = get_llm()
    
    prompt = PromptTemplate(
        template="""당신은 도서 정보 전문가입니다. 제공된 [도서 데이터]를 바탕으로 사용자의 질문에 친절하게 답하세요.
        답변 시에는 반드시 제공된 데이터에 근거해야 하며, 데이터에 없는 내용은 모른다고 답하세요.
        
        [도서 데이터]: {books_info}
        
        사용자 질문: {question}
        
        답변 형식: 질문에 대한 핵심 정보를 포함하여 "~이다." 말투로 작성하세요.
        """,
        input_variables=["books_info", "question"],
    )
    
    # 4. 체인 실행
    chain = prompt | llm
    response = chain.invoke({
        "books_info": json.dumps(subjects_data, ensure_ascii=False), 
        "question": user_message
    })
    
    # 5. 상태 업데이트
    # 생성된 답변을 메시지 리스트에 추가하여 반환한다.
    return {
        "messages": [response],
        "context": "도서 기초 정보 참조 완료"
    }