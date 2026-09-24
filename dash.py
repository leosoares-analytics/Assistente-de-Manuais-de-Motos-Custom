import os
import streamlit as st

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# ============================================================
# 1. CARREGAR VARIÁVEIS DO .ENV
# ============================================================

load_dotenv()

VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")
IMAGE_DB_PATH = os.getenv("IMAGE_DB_PATH")

VECTOR_COLLECTION_NAME = os.getenv(
    "VECTOR_COLLECTION_NAME",
    "manuais_docs"
)

IMAGE_COLLECTION_NAME = os.getenv(
    "IMAGE_COLLECTION_NAME",
    "manuais_imagens"
)

EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBEDDING_MODEL",
    "nomic-embed-text"
)

LLM_MODEL = os.getenv(
    "OLLAMA_LLM_MODEL",
    "llama3"
)


# ============================================================
# 2. VALIDAÇÃO DAS VARIÁVEIS
# ============================================================

if not VECTOR_DB_PATH:
    st.error("VECTOR_DB_PATH não foi definido no arquivo .env")
    st.stop()

if not IMAGE_DB_PATH:
    st.error("IMAGE_DB_PATH não foi definido no arquivo .env")
    st.stop()


# ============================================================
# 3. CONFIGURAÇÃO DO STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Assistente de Manuais",
    page_icon="🏍️",
    layout="wide"
)

st.title("🏍️ Assistente de Manuais Técnicos")


# ============================================================
# 4. CARREGAMENTO DO RAG
# ============================================================

@st.cache_resource
def carregar_rag():

    # --------------------------------------------------------
    # Embeddings
    # --------------------------------------------------------

    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL
    )


    # --------------------------------------------------------
    # BANCO VETORIAL DE TEXTO
    # --------------------------------------------------------

    vectorstore = Chroma(
        collection_name=VECTOR_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=VECTOR_DB_PATH
    )

    retriever_texto = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 6
        }
    )


    # --------------------------------------------------------
    # BANCO VETORIAL DE IMAGENS
    # --------------------------------------------------------

    image_store = Chroma(
        collection_name=IMAGE_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=IMAGE_DB_PATH
    )

    retriever_imagens = image_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 4
        }
    )


    # --------------------------------------------------------
    # LLM
    # --------------------------------------------------------

    llm = OllamaLLM(
        model=LLM_MODEL
    )


    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    prompt = ChatPromptTemplate.from_template(
        """
Você é um assistente especializado em manuais técnicos
de motocicletas.

Sua função é responder perguntas utilizando SOMENTE
as informações presentes no contexto.

REGRAS IMPORTANTES:

1. Não invente informações.

2. Não utilize conhecimento externo ao contexto.

3. Se a informação não estiver presente no contexto,
   responda exatamente:

   "Não encontrei essa informação nos manuais disponíveis."

4. Preserve as relações entre títulos, categorias,
   listas, tabelas e seus respectivos valores.

5. Quando uma pergunta pedir uma lista de modelos,
   apresente todos os modelos encontrados no contexto.

6. Não confunda modelos diferentes.

   Por exemplo:

   Meteor 350
   Super Meteor 650
   Shotgun 650

   são modelos diferentes.

7. Se houver informações de modelos diferentes
   no contexto, utilize somente as informações
   correspondentes ao modelo perguntado.

8. Se existirem informações conflitantes,
   informe que existe uma divergência.

9. Sempre que possível, mencione o documento
   e a página onde a informação foi encontrada.

--------------------------------------------------

CONTEXTO:

{context}

--------------------------------------------------

PERGUNTA:

{question}

--------------------------------------------------

RESPOSTA:
"""
    )


    # --------------------------------------------------------
    # FORMATAÇÃO DOS DOCUMENTOS
    # --------------------------------------------------------

    def format_docs(docs):

        formatted_docs = []

        for i, doc in enumerate(docs):

            arquivo = doc.metadata.get(
                "arquivo",
                doc.metadata.get(
                    "source",
                    "Desconhecido"
                )
            )

            pagina = doc.metadata.get(
                "pagina",
                doc.metadata.get(
                    "page",
                    "Desconhecida"
                )
            )

            formatted_docs.append(
                f"""
[FONTE {i + 1}]

Arquivo: {arquivo}

Página: {pagina}

{doc.page_content}
""".strip()
            )

        return "\n\n".join(formatted_docs)


    # --------------------------------------------------------
    # RAG CHAIN
    # --------------------------------------------------------

    chain = (
        {
            "context": retriever_texto | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )


    return (
        chain,
        retriever_texto,
        retriever_imagens
    )


# ============================================================
# 5. CARREGAR COMPONENTES
# ============================================================

rag_chain, retriever_texto, retriever_imagens = carregar_rag()


# ============================================================
# 6. HISTÓRICO DO CHAT
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])

        # Exibir imagens associadas à resposta
        if msg["role"] == "assistant":

            imagens = msg.get("images", [])

            for imagem in imagens:

                if os.path.exists(imagem):

                    st.image(
                        imagem,
                        use_container_width=True
                    )


# ============================================================
# 7. CHAT
# ============================================================

if pergunta := st.chat_input(
    "Pergunte algo sobre os manuais..."
):

    # --------------------------------------------------------
    # Mostrar pergunta
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": pergunta
        }
    )

    with st.chat_message("user"):
        st.markdown(pergunta)


    # --------------------------------------------------------
    # Gerar resposta
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "Buscando nos manuais..."
        ):

            # ================================================
            # 1. Recuperar textos
            # ================================================

            docs_texto = retriever_texto.invoke(
                pergunta
            )


            # ================================================
            # 2. Gerar resposta
            # ================================================

            resposta = rag_chain.invoke(
                pergunta
            )


            # ================================================
            # 3. Recuperar imagens
            # ================================================

            docs_imagens = retriever_imagens.invoke(
                pergunta
            )


            # ================================================
            # 4. Identificar caminhos das imagens
            # ================================================

            imagens = []

            for doc in docs_imagens:

                metadata = doc.metadata

                caminho = (
                    metadata.get("image_path")
                    or metadata.get("imagem")
                    or metadata.get("path")
                    or metadata.get("source")
                )

                if caminho:

                    # Converter para caminho absoluto
                    if not os.path.isabs(caminho):

                        caminho = os.path.join(
                            IMAGE_DB_PATH,
                            caminho
                        )

                    caminho = os.path.normpath(
                        caminho
                    )

                    if os.path.exists(caminho):

                        if caminho not in imagens:

                            imagens.append(caminho)


            # ================================================
            # 5. Mostrar resposta
            # ================================================

            st.markdown(resposta)


            # ================================================
            # 6. Mostrar imagens
            # ================================================

            if imagens:

                st.markdown(
                    "### 🖼️ Imagens relacionadas"
                )

                for imagem in imagens:

                    st.image(
                        imagem,
                        use_container_width=True
                    )


    # ========================================================
    # 7. SALVAR NO HISTÓRICO
    # ========================================================

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": resposta,
            "images": imagens
        }
    )
