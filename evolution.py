import os
import re
import pandas as pd
from langchain_core.prompts import PromptTemplate
from agents import get_llm, EvaluatorAgent

class AlgorithmRegistry:
    """Manages the registered test cases and the current best algorithm script."""
    def __init__(self, registry_dir="registry"):
        self.registry_dir = registry_dir
        os.makedirs(self.registry_dir, exist_ok=True)
        self.test_cases = []  # List of dicts: {'input': df, 'expected': df, 'id': int}
        self.current_code = None

    def add_test_case(self, input_df: pd.DataFrame, expected_df: pd.DataFrame):
        case_id = len(self.test_cases)
        self.test_cases.append({
            'id': case_id,
            'input': input_df,
            'expected': expected_df
        })
        return case_id

    def set_current_code(self, code: str):
        self.current_code = code
        with open(os.path.join(self.registry_dir, "algorithm.py"), "w") as f:
            f.write(code)

    def load_current_code(self):
        code_path = os.path.join(self.registry_dir, "algorithm.py")
        if os.path.exists(code_path):
            with open(code_path, "r") as f:
                self.current_code = f.read()
        return self.current_code

class EvolutionAgent:
    def __init__(self, llm=None, provider="gemini"):
        self.llm = llm or get_llm(provider)
        self.prompt = PromptTemplate.from_template(
            """You are an expert Python software engineer and data engineer.
You wrote a data transformation script that worked for previous data, but it fails on new data.
Your job is to REWRITE the function `def transform_data(df):` so that it handles BOTH the old robustness AND the new edge case successfully.

Here is the current code that failed:
```python
{current_code}
```

Here is the error message or diff from the failed test:
{error_message}

Here is a sample of the input data that failed (Markdown):
{failed_input}

Here is the expected output for that input (Markdown):
{failed_expected}

Rewrite the python function `def transform_data(df):`. 
Ensure you import pandas as pd if needed inside or outside the function.
Output ONLY valid, executable Python code. Do not include markdown formatting or explanations, just the Python code.
"""
        )

    def evolve_code(self, current_code: str, error_message: str, failed_input_md: str, failed_expected_md: str) -> str:
        chain = self.prompt | self.llm
        response = chain.invoke({
            "current_code": current_code,
            "error_message": error_message,
            "failed_input": failed_input_md,
            "failed_expected": failed_expected_md
        })
        code = response.content
        
        match = re.search(r"```python\n(.*?)\n```", code, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        return code.strip()
