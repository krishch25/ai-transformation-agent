import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
print(f"Key loaded: {'Yes' if api_key else 'No'}")

try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0, google_api_key=api_key)
    prompt = PromptTemplate.from_template("Say hello to {name}")
    chain = prompt | llm
    response = chain.invoke({"name": "world"})
    print("Response:", response.content)
except Exception as e:
    import traceback
    traceback.print_exc()
