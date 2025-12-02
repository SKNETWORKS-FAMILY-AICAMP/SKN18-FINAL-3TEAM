from openai import OpenAI
import os

def create_model():
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"))
    return client
