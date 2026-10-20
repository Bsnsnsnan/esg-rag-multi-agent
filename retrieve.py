import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()
client = OpenAI(api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
collection = chromadb.PersistentClient(path="./chroma_db").get_collection("esg_reports")

def retrieve(query, company=None, k=5):
    emb = client.embeddings.create(model="text-embedding-v3", input=[query]).data[0].embedding
    res = collection.query(query_embeddings=[emb], n_results=k,
                           where={"company": company} if company else None)
    return [{"id": i, "text": t, "metadata": m, "distance": d}
            for i, t, m, d in zip(res["ids"][0], res["documents"][0],
                                  res["metadatas"][0], res["distances"][0])]

if __name__ == "__main__":
    for r in retrieve("Scope 1 and 2 greenhouse gas emissions", company="Apple"):
        print(round(r["distance"], 3), r["id"])
        print(r["text"][:200].replace("\n", " "), "\n")
        