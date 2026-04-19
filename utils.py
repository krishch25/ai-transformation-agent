import pandas as pd
import os

def load_file_to_dataframe(filepath):
    """
    Loads an Excel or CSV file into a pandas DataFrame.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        return pd.read_csv(filepath)
    elif ext in ['.xls', '.xlsx']:
        return pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def save_dataframe_to_file(df, filepath):
    """
    Saves a DataFrame to an Excel or CSV file.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        df.to_csv(filepath, index=False)
    elif ext in ['.xls', '.xlsx']:
        df.to_excel(filepath, index=False)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def dataframe_to_markdown(df, max_rows=50):
    """
    Converts a DataFrame to a markdown table, truncating if necessary.
    This is useful for feeding data into the LLM context.
    """
    if len(df) > max_rows:
        return df.head(max_rows).to_markdown() + f"\n\n... (truncated {len(df) - max_rows} rows)"
    return df.to_markdown()
