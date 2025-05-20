#!/usr/bin/env python3
"""
Run the Streamlit app without installing the package.
This script adds the project root to Python path and then runs Streamlit.
"""
import os
import sys
import subprocess

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

print(f"Added {project_root} to Python path")
print("Starting Streamlit app...")

# Run Streamlit
subprocess.run(["streamlit", "run", os.path.join(project_root, "app", "main.py")]) 