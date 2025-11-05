import os
import sys

# Ensure the package root (apps/api) is on sys.path for `import app`
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

