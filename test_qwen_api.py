import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://ws-4huke4bou69ngcli.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
)

response = client.chat.completions.create(
    model="qwen-plus",
    messages=[{"role": "user", "content": "Hello, tell me about ESG reporting."}]
)
print(response.choices[0].message.content)
