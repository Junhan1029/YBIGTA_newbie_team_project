import os
from langchain_upstage import ChatUpstage, UpstageEmbeddings

def get_llm():
    """Upstage의 Solar-1-Mini 모델을 반환한다."""
    return ChatUpstage(model="solar-1-mini-chat")

def get_embeddings():
    """Upstage의 Embedding 모델을 반환한다."""
    return UpstageEmbeddings(model="solar-embedding-1-large")