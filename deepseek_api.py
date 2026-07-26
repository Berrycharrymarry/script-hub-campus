import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError("没有读取到 DeepSeek API Key，请检查 .env 文件。")


client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)


def ask_deepseek(
    user_message,
    system_message="你是一名聪明友好、诙谐幽默的助手，请帮助用户完成任务。"
):
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        stream=False
    )

    answer = response.choices[0].message.content

    return answer



def handle_question(question,system_message="你是一名聪明友好、诙谐幽默的助手，请帮助用户完成任务。"):
    question = question.strip()
    if not question:
        return "请输入问题。"
    return ask_deepseek(question,system_message=system_message)
