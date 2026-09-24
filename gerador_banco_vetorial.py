import os
import json
import glob
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =======================================================
# 1. Carregar .md, integrar metadados do .json e imagens
# =======================================================

manuais = os.getenv("camada_gold")
manuais_dir = Path(manuais)
documentos = []

# Procura todos os arquivos Markdown no diretório informado
md_files = glob.glob(os.path.join(manuais_dir, "**/*.md"), recursive=True)

print("Carregando arquivos e associando metadados dos JSONs...")
for md_path in md_files:
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Procura por um arquivo .json de mesmo nome (ex: manual.md -> manual.json)
    json_path = os.path.splitext(md_path)[0] + ".json"
    images_metadata = {}
    
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as jf:
                images_metadata = json.load(jf)
        except Exception as e:
            print(f"Erro ao ler {json_path}: {e}")

    # Cria o Documento base com os metadados agregados
    doc = Document(
        page_content=content,
        metadata={
            "source": md_path,
            "images_info": json.dumps(images_metadata, ensure_ascii=False)
        }
    )
    documentos.append(doc)


# =======================================================
# 2. Split do Markdown preservando o contexto e cabeçalhos
# =======================================================

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False
)

docs_split = []
for doc in documentos:
    # Quebra por estrutura de tópicos
    header_splits = markdown_splitter.split_text(doc.page_content)
    
    # Garante que os metadados do documento original sejam mantidos
    for split in header_splits:
        split.metadata.update(doc.metadata)
        docs_split.append(split)

# Aplica divisão secundária caso algum capítulo do markdown seja muito longo
text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
chunks = text_splitter.split_documents(docs_split)


# =======================================================
# 3. Embeddings e VectorStore no ChromaDB
# =======================================================

embeddings = OllamaEmbeddings(model="nomic-embed-text")

vectorstore = Chroma(
    collection_name="manuais_docs",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)

batch_size = 50
print(f"Gerando embeddings para {len(chunks)} chunks...")

for i in tqdm(range(0, len(chunks), batch_size)):
    lote = chunks[i:i + batch_size]
    vectorstore.add_documents(lote)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
print("Embeddings gerados e salvos no ChromaDB com sucesso!")


# =======================================================
# 4. LLM e Formatação do Contexto com Imagens
# =======================================================

llm = OllamaLLM(model="llama3")

def format_docs(docs):
    """
    Combina o texto dos chunks com a descrição dos metadados das imagens.
    Isso instrui o modelo sobre quais imagens correspondem a este trecho.
    """
    formatted_chunks = []
    for doc in docs:
        chunk_text = doc.page_content
        images_info = doc.metadata.get("images_info", "{}")
        
        # Anexa os detalhes das imagens logo abaixo do texto recuperado
        if images_info != "{}":
            chunk_text += f"\n\n[Informações e Descrições das Imagens Disponíveis no JSON]:\n{images_info}"
            
        formatted_chunks.append(chunk_text)
        
    return "\n\n---\n\n".join(formatted_chunks)

prompt = ChatPromptTemplate.from_template(
    "Você é um assistente especializado em manuais técnicos de motos custom de baixa e média cilindrada.\n"
    "Responda à pergunta do usuário utilizando APENAS o contexto fornecido abaixo.\n\n"
    "REGRAS PARA EXIBIÇÃO DE IMAGENS:\n"
    "1. Se o contexto contiver referências ou caminhos de imagens (.png) relevantes para explicar a resposta, "
    "inclua obrigatoriamente a imagem na sua resposta no formato Markdown: ![Descrição](caminho_da_imagem.png).\n"
    "2. Não invente caminhos ou nomes de imagens que não existam no contexto.\n\n"
    "Contexto:\n{context}\n\n"
    "Pergunta: {question}"
)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)