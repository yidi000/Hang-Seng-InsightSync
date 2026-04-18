import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# 1. 加载本地 .env
load_dotenv()

# 2. 读取环境变量
api_key = os.getenv("AZURE_OPENAI_API_KEY")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

# 3. 基本校验
if not all([api_key, endpoint, deployment, api_version]):
    raise ValueError("Missing one or more Azure environment variables in .env")

# 4. 初始化 Azure OpenAI client
client = AzureOpenAI(
    api_key=api_key,
    azure_endpoint=endpoint,
    api_version=api_version
)

# 5. 读取输入文件
with open("data/sample_report.txt", "r", encoding="utf-8") as f:
    report = f.read()

with open("prompt/insight_prompt_v1.txt", "r", encoding="utf-8") as f:
    prompt = f.read()

# 6. 组装输入
full_prompt = f"""
[REPORT]
{report}

{prompt}
"""

# 7. 调用模型
response = client.chat.completions.create(
    model=deployment,
    messages=[
        {"role": "system", "content": "You are a banking insight generation assistant."},
        {"role": "user", "content": full_prompt}
    ],
    temperature=0.3
)

# 8. 提取输出
output_text = response.choices[0].message.content

# 9. 保存结果
os.makedirs("output", exist_ok=True)
with open("output/generated_insight.txt", "w", encoding="utf-8") as f:
    f.write(output_text)

print("✅ Demo completed successfully.")
print("📄 Output saved to output/generated_insight.txt")
