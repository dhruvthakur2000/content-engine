from langchain_community.llms import HuggingFaceEndpoint

import os


def get_llm():
    llm = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen2.5-7B-Instruct",  # Or Qwen2.5-72B
        task="text-generation",
        temperature=0.7,
        max_new_tokens=512,
        model_kwargs={
            "top_p": 0.9,
            "do_sample": True,
        },
        huggingfacehub_api_token=os.getenv("HF_TOKEN")  # Free tier works
    )
    return llm
