import os
import pandas as pd
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
import re

def get_llm(provider="gemini"):
    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("groq_api_key")
        if not api_key: raise ValueError("GROQ_API_KEY not set")
        return ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=api_key)
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("openai_api_key")
        if not api_key: raise ValueError("OPENAI_API_KEY not set")
        return ChatOpenAI(model="gpt-4o", temperature=0, api_key=api_key)
    elif provider == "ollama":
        # Ensure Ollama is running locally on the default port
        return ChatOllama(model="llama3", temperature=0)
    elif provider == "modal":
        base_url = os.environ.get("MODAL_LLM_URL") or os.environ.get("modal_llm_url")
        api_key = os.environ.get("MODAL_LLM_TOKEN") or os.environ.get("modal_llm_token") or "EMPTY" # Modal vLLM doesn't strictly need a key unless user wraps it
        if not base_url: raise ValueError("MODAL_LLM_URL not set in environment. It must point to your modal vLLM deployment (e.g. 'https://...modal.run/v1')")
        return ChatOpenAI(model="modal-model", temperature=0, base_url=base_url, api_key=api_key, max_retries=2, timeout=600)
    else:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key: raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set")
        return ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0, google_api_key=api_key)

class AnalyzerAgent:
    def __init__(self, llm=None, provider="gemini"):
        self.llm = llm or get_llm(provider)
        self.prompt = PromptTemplate.from_template(
            """You are an expert data analyst.
You are given a sample of an input dataset and the corresponding sample of the output dataset.
Your job is to deduce the exact business logic and transformation rules required to convert the input into the output.

CRITICAL INSTRUCTIONS:
1. You must explicitly list every single column present in the Output Data.
2. For each output column, explain EXACTLY how it is derived from the Input Data (e.g. copied exactly, renamed from 'X', calculated as A*B, hardcoded, or mapped). Provide specific value mappings if applicable.
3. Explain which rows are dropped or filtered out. Handle potential nulls or `NaN`s clearly.
4. If there are aggregations or groupbys, identify the exact group keys and the aggregation functions used. Beware of data type mismatches (e.g. string vs numeric).

Input Columns:
{input_columns}

Output Columns:
{output_columns}

Input Data Sample (Markdown):
{input_data}

Output Data Sample (Markdown):
{output_data}

Detailed Transformation Rules:"""
        )

    def analyze(self, input_df: pd.DataFrame, output_df: pd.DataFrame) -> str:
        # Convert to markdown internally for the prompt
        from utils import dataframe_to_markdown
        in_md = dataframe_to_markdown(input_df)
        out_md = dataframe_to_markdown(output_df)
        
        in_cols = list(input_df.columns)
        out_cols = list(output_df.columns)
        
        chain = self.prompt | self.llm
        response = chain.invoke({
            "input_columns": str(in_cols),
            "output_columns": str(out_cols),
            "input_data": in_md, 
            "output_data": out_md
        })
        return response.content

class CoderAgent:
    def __init__(self, llm=None, provider="gemini"):
        self.llm = llm or get_llm(provider)
        self.prompt = PromptTemplate.from_template(
            """You are an expert Python data engineer.
Write a python function `def transform_data(df):` that takes a pandas DataFrame `df` and returns the transformed DataFrame.
Do NOT read or write any files inside this function. Only manipulate the DataFrame `df` and return it.
Ensure you import pandas as pd if needed inside or outside the function.

CRITICAL INSTRUCTIONS: 
Ensure the FINAL returned DataFrame has EXACTLY the same columns, in the exact same order, as the expected output described in the rules. Handle potential missing values (NaN/None) gracefully, especially when doing string operations or numerical calculations.
Drop any intermediate calculation columns before returning.
DO NOT hallucinate mapping dictionaries. If the rules do not provide specific key-value pairs for a mapping, write code that works universally or leave the mapping empty. DO NOT hardcode 'MAT_A', 'SUP1' etc unless explicitly instructed.
DO NOT drop any rows or perform `groupby` aggregations unless the rules EXPLICITLY state that the output has fewer rows than the input and requires aggregation. By default, assume a 1-to-1 row mapping.

Here are the transformation rules you must implement:
{rules}

{error_feedback}

Output ONLY valid, executable Python code. Do not include markdown formatting or explanations, just the Python code.
"""
        )

    def write_code(self, rules: str, previous_code: str = None, error_msg: str = None) -> str:
        error_feedback = ""
        if previous_code and error_msg:
            error_feedback = f"Your previous code:\n```python\n{previous_code}\n```\n\nFailed with this error:\n{error_msg}\n\nPlease fix the code so it executes successfully."
            
        chain = self.prompt | self.llm
        response = chain.invoke({"rules": rules, "error_feedback": error_feedback})
        code = response.content
        
        # Aggressive extraction of code block to handle conversational models like Llama3
        match = re.search(r"```python\n(.*?)\n```", code, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Fallback if just generic code blocks are used
        match = re.search(r"```(.*?)```", code, re.DOTALL)
        if match:
            return match.group(1).strip()

        return code.strip()

class EvaluatorAgent:
    def __init__(self):
        pass

    def evaluate(self, code: str, input_df: pd.DataFrame, expected_df: pd.DataFrame):
        """
        Executes the generated code safely and compares the result to expected_df.
        Returns (success_bool, result_df, error_message)
        """
        local_env = {"pd": pd}
        try:
            exec(code, local_env)
            if "transform_data" not in local_env:
                return False, None, "Function `transform_data` not found in generated code."
            
            # Run the function
            result_df = local_env["transform_data"](input_df.copy())
            
            # Compare output shape or values
            pd.testing.assert_frame_equal(result_df.reset_index(drop=True), expected_df.reset_index(drop=True))
            return True, result_df, None
        except AssertionError as e:
            return False, result_df if 'result_df' in locals() else None, f"Data mismatch:\\n{str(e)}"
        except Exception as e:
            return False, None, f"Execution Error:\\n{str(e)}"
