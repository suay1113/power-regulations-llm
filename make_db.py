from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from operator import itemgetter
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import Docx2txtLoader
import asyncio
import os

def get_embedding_model():
    model_name = "./model/bge-large-zh-v1.5"
    model_kwargs = {"device": "cuda"}
    encode_kwargs = {"normalize_embeddings": True}
    embedding_model = HuggingFaceBgeEmbeddings(
        model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
    )
    return embedding_model

async def get_db(file_path="./docs/2.docx"):
    loader = Docx2txtLoader(file_path)
    data = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=0)
    docs = text_splitter.split_documents(data)
    db = await FAISS.afrom_documents(docs, get_embedding_model())
    return db

async def get_merged_db(directory="./docs"):
    file_list = os.listdir(directory)
    all_path = []
    for filename in file_list:
        file_path = os.path.join(directory, filename)
        all_path.append(file_path)

    db = await get_db(all_path[0])
    for path in all_path[1:]:
        db_new = await get_db(path)
        db.merge_from(db_new)
    db.save_local("./vector_db/db")
    return db


async def main():
    db = await get_merged_db(directory="./docs")
    query = "用电安全规范"
    searched_docs = await db.asimilarity_search(query,5)
    print(searched_docs[0].page_content)

if __name__ == "__main__":
    # 运行异步事件循环
    asyncio.run(main())

#os.listdir(directory):
#if filename.endswith(".docx"):


