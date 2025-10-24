import altair as alt # New import for Altair
import pandas as pd # Explicitly imported for the example
import re
from backend.azure_client import chat_with_azure
import matplotlib.pyplot as plt 


temperature = 0
max_tokens = 1000

def extract_python_code(full_text: str) -> str:
    """
    Extracts the first Python code block (inside ```python ... ```) from the given text.
    Returns the code as a string without the triple backticks.
    If no Python code block found, returns an empty string.
    """
    pattern = r"```python\s*(.*?)```"
    match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

def run_python_code_return_fig(code_str: str):
    """
    Executes the Python code and returns the visualization object.
    It prioritizes an Altair chart object ('chart') but falls back to a 
    matplotlib Figure object ('fig') if necessary.
    
    Returns the visualization object (Altair Chart or Matplotlib Figure) or None.
    """
    try:
        local_vars = {'pd': pd, 'alt': alt} # Inject necessary modules
        exec(code_str, {'pd': pd, 'alt': alt, 'plt': plt}, local_vars) # Pass modules to exec context

        # 1. Try to get 'chart' (Altair object)
        chart = local_vars.get('chart', None)
        if chart is not None:
            return chart

        # 2. Try to get 'fig' (Matplotlib object)
        fig = local_vars.get('fig', None)

        # 3. Fallback: If no explicit fig, try to get current figure from pyplot
        if fig is None:
            # We explicitly create a figure to control size if no figure was created by the code
            # Note: This fallback is less relevant if the LLM generates Altair, 
            # but is kept for robust Matplotlib handling.
            if plt.get_fignums():
                fig = plt.gcf()
            else:
                # If no figure exists, we can't get one. Return None.
                return None 

        # Always ensure a size is set for Matplotlib figures 
        # (though Altair is preferred for interactivity)
        if fig is not None:
            fig.set_size_inches(8, 5)

        return fig

    except Exception as e:
        print(f"Error executing visualization code: {e}")
        # IMPORTANT: Close any potentially open Matplotlib figures in case of error
        plt.close('all') 
        return None


def generate_visualization_code(user_input: str) -> str:
    system_prompt = f"""
    Generate an executable Python script for the given query: {user_input} that:

    - Imports pandas as pd and altair as alt.
    - Loads the data into a pandas DataFrame (df).
    - Creates an suitable, INTERACTIVE chart (like bar, line, scatter) visualizing the data using Altair.
    - The chart MUST include a 'tooltip' encoding to display data values on hover (interaction).
    - The final chart object MUST be assigned to a variable named 'chart'.
    - Returns only the code block, no explanations. Do NOT include plt.show().

    Example:
    import pandas as pd
    import altair as alt

    data = [
        {{"category": "Electronics", "total_sales": 120000}},
        {{"category": "Clothing", "total_sales": 90000}},
        {{"category": "Books", "total_sales": 45000}}
    ]

    df = pd.DataFrame(data)

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('category', title='Category'),
        y=alt.Y('total_sales', title='Total Sales'),
        tooltip=['category', 'total_sales']
    ).properties(
        title='Total Sales by Category'
    )
    """
    messages = [{"role": "system", "content": system_prompt}]
    response = chat_with_azure(messages, temperature=0, max_tokens=1000)
    return response

def generate_visualization(user_input: str):
    code_response = generate_visualization_code(user_input)
    extracted_code = extract_python_code(code_response)
    if not extracted_code:
        print("No code extracted from model response")
        return None

    # This function now returns an Altair Chart object or Matplotlib Figure
    viz_object = run_python_code_return_fig(extracted_code)
    
    # Critical: Close any figures that were created by the code
    # This prevents figures from bleeding into other Streamlit runs
    plt.close('all') 
    
    return viz_object