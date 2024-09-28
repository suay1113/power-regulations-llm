from openai import OpenAI

# 初始化OpenAI客户端
openai_api_key = "sk-2024mingjing"
openai_api_base = "http://mingjing.mininglamp.com/api/llm/v1"
client = OpenAI(api_key=openai_api_key, base_url=openai_api_base)



def model_answer(message, system_prompt, tmp=0.01):
    prompt = message
    chat_response = client.chat.completions.create(
        model="Qwen",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.01,
        top_p=0.01,
        max_tokens=2048,
        extra_body={
            "repetition_penalty": 1.05,
        },
    )    
    ans_str = chat_response.choices[0].message.content
    # logger.info(f"【API使用情况】 {chat_response.usage}")
    
    return ans_str
