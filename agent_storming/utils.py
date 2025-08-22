"""
Utility functions
"""

import os
import getpass
import logging


def ensure_env(var: str) -> str:
    """Ensure environment variable is set. Prompt securely if missing."""
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")
    return os.environ[var]

def read_file_contents(filename: str) -> str:
    """Read the entire contents of a text file. Returns empty string if errors occur."""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        logging.error(f"File not found: {filename}")
        raise
    except PermissionError:
        logging.error(f"Permission denied: {filename}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error reading {filename}: {e}")
        raise
