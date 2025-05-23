from setuptools import setup, find_packages

setup(
    name="buffett_screener",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "matplotlib==3.5.3",
        "pandas==1.5.3",
        "numpy==1.24.3",
        "streamlit==1.29.0",
        "yfinance==0.2.35",
    ],
    python_requires=">=3.9,<3.10",
) 