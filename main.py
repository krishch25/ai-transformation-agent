import os
import argparse
from dotenv import load_dotenv
from utils import load_file_to_dataframe, dataframe_to_markdown
from agents import AnalyzerAgent, CoderAgent, EvaluatorAgent
from evolution import AlgorithmRegistry, EvolutionAgent

load_dotenv()

def process_initial_pair(input_df, expected_df, registry, provider):
    print("No existing algorithm found. Analyzing initial pair...")
    analyzer = AnalyzerAgent(provider=provider)
    coder = CoderAgent(provider=provider)
    evaluator = EvaluatorAgent()
    
    
    rules = analyzer.analyze(input_df, expected_df)
    print("--- Deduced Rules ---")
    print(rules)
    print("---------------------\n")
    
    code = None
    err_msg = None
    
    for attempt in range(3):
        print(f"Generating initial algorithm (Attempt {attempt+1}/3)...")
        code = coder.write_code(rules, previous_code=code, error_msg=err_msg)
        
        success, _, err_msg = evaluator.evaluate(code, input_df, expected_df)
        if success:
            print("Success! Initial algorithm works and perfectly matches the output.")
            print("--- Generated Code ---")
            print(code)
            print("----------------------\n")
            registry.set_current_code(code)
            return True
            
        print(f"Algorithm failed on attempt {attempt+1}: {err_msg}")
        print("--- Failed Code Attempt ---")
        print(code)
        print("---------------------------\n")
        
    print("Failed to generate a working initial algorithm after 3 attempts.")
    return False

def process_new_pair(input_df, expected_df, registry, provider):
    print("Testing existing algorithm against new pair...")
    evaluator = EvaluatorAgent()
    current_code = registry.load_current_code()
    
    success, _, err = evaluator.evaluate(current_code, input_df, expected_df)
    if success:
        print("Existing algorithm already handles this case! No evolution needed.")
        return True
        
    print("Existing algorithm failed on new data. Evolving...")
    evolver = EvolutionAgent(provider=provider)
    
    in_md = dataframe_to_markdown(input_df)
    out_md = dataframe_to_markdown(expected_df)
    
    # Try a few evolution loops
    for attempt in range(3):
        print(f"Evolution attempt {attempt+1}/3...")
        new_code = evolver.evolve_code(current_code, err, in_md, out_md)
        
        # Must pass NEW case
        succ_new, _, err_new = evaluator.evaluate(new_code, input_df, expected_df)
        if not succ_new:
            print(f"Attempt {attempt+1} failed on new data: {err_new}")
            err = err_new
            current_code = new_code
            continue
            
        # Must pass ALL OLD cases
        all_passed = True
        for case in registry.test_cases:
            succ_old, _, _ = evaluator.evaluate(new_code, case['input'], case['expected'])
            if not succ_old:
                all_passed = False
                err = f"Failed regression test on old test case ID: {case['id']}"
                print(err)
                break
                
        if all_passed:
            print("Evolution successful! Code passes both new and old cases. Originality maintained.")
            print("--- New Evolved Code ---")
            print(new_code)
            print("------------------------\n")
            registry.set_current_code(new_code)
            return True
            
        current_code = new_code
        
    print("Failed to evolve algorithm after 3 attempts.")
    return False

def main():
    parser = argparse.ArgumentParser(description="Agentic Pattern Recognition")
    parser.add_argument("input_file", help="Path to input Excel/CSV file")
    parser.add_argument("output_file", help="Path to expected output Excel/CSV file")
    parser.add_argument("--provider", choices=["gemini", "groq", "openai", "ollama", "modal"], default="ollama", help="LLM Provider to use (gemini, groq, openai, ollama, modal).")
    args = parser.parse_args()

    # Load data
    try:
        input_df = load_file_to_dataframe(args.input_file)
        expected_df = load_file_to_dataframe(args.output_file)
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    if args.provider == "ollama":
        print("Note: Using Open-Source Local Ollama. Please ensure your Ollama instance is running (e.g., 'ollama serve' and 'ollama run llama3').")
    elif args.provider == "modal":
        print("Note: Using Modal Serverless LLM. Ensure MODAL_LLM_URL is set in your .env file pointing to your inference endpoint.")

    registry = AlgorithmRegistry()
    registry.load_current_code()

    success = False
    if not registry.current_code:
        # First time
        process_initial_pair(input_df, expected_df, registry, args.provider)
        if registry.current_code:
            success = True
    else:
        # Subsequent runs
        success = process_new_pair(input_df, expected_df, registry, args.provider)

    # Finally add test case if success so it can be used for regression testing later
    if success:
        case_id = registry.add_test_case(input_df, expected_df)
        print(f"Test pair saved to registry as case ID {case_id}")

if __name__ == "__main__":
    main()
