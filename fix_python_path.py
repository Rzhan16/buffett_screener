#!/usr/bin/env python
"""
Fix Python Path for Buffett Screener

This script adds the project root to PYTHONPATH, installs the project in development mode,
and creates a .pth file in site-packages to ensure the src module is always importable.
"""
import os
import sys
import subprocess
import site
from pathlib import Path

def main():
    """Fix Python path for the project"""
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    print(f"Project root: {project_root}")
    
    # Add project root to PYTHONPATH
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added {project_root} to sys.path")
    
    # Install the package in development mode
    print("Installing package in development mode...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
    
    # Create a .pth file in site-packages
    site_packages_dir = site.getsitepackages()[0]
    pth_file = os.path.join(site_packages_dir, "buffett_screener.pth")
    
    with open(pth_file, "w") as f:
        f.write(project_root)
    
    print(f"Created .pth file at {pth_file}")
    
    # Test importing the module
    try:
        print("Testing imports...")
        import src.scoring.buffett
        print("✅ Successfully imported src.scoring.buffett")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        
    # Print environment info for debugging
    print("\nEnvironment Information:")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    print(f"sys.path: {sys.path}")
    
    print("\n✅ Python path fix completed. The project should now be importable.")
    print("To use in your terminal, run:")
    print(f"export PYTHONPATH={project_root}:$PYTHONPATH")

if __name__ == "__main__":
    main() 