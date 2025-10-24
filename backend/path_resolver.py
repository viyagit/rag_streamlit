import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder
    except AttributeError:
        base_path = os.path.abspath(".")  # Current directory if not bundled

    abs_path = os.path.join(base_path, relative_path)

    if os.path.exists(abs_path):
        return abs_path
    else:
        # If path doesn't exist in PyInstaller temp, try current working directory
        abs_path_fallback = os.path.join(os.path.abspath("."), relative_path)
        if os.path.exists(abs_path_fallback):
            return abs_path_fallback
        else:
            # Neither exists, raise error
            raise FileNotFoundError(f"Resource not found in either location: {abs_path} or {abs_path_fallback}")
