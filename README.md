# Agentic AI Pattern Recognition System

This system uses AI Agents to dynamically learn business logic from Input/Output data pairs (Excel or CSV), generate a Python algorithm, and evolve that algorithm when given new pairs without breaking backwards compatibility (originality).

## Setup
1. Make sure you are in the project folder: `cd /Users/krishchoudhary/Downloads/excel-op`
2. Activate the virtual environment: `source venv/bin/activate`
3. Rename the provided `.env.example` file to `.env` and insert your `OPENAI_API_KEY`.

## Usage
Provide an input file and expected corresponding output file to the app:
```bash
python main.py input.xlsx expected_output.xlsx
```

- When run for the **first time**, the `AnalyzerAgent` and `CoderAgent` will deduce the rules between the two files and generate an algorithm saved to `registry/algorithm.py`. The `EvaluatorAgent` runs it instantly to confirm it produces the expected output.
- When run the **second time with new files**, the `EvaluatorAgent` runs the **current code**. If it fails, the `EvolutionAgent` enters a loop to rewrite the python code to handle the *new* case, while asserting it *still passes* the previous cases stored in `registry/`.
