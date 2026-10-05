import sys
import os

# Insert the parent directory of this conftest file (the backend folder itself) to sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
