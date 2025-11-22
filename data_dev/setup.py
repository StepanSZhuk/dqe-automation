"""
Setup configuration for data_dev package.
"""
from setuptools import setup, find_packages

setup(
    name="data_dev",
    version="0.1.0",
    description="Data generation and transformation pipeline for DQE automation",
    author="Stepan Zhuk",
    packages=find_packages(where="."),
    package_dir={"": "."},
    python_requires=">=3.9",
    install_requires=[
        "faker~=37.1.0",
        "psycopg2~=2.9.10",
        "pandas~=2.2.3",
        "pyarrow~=19.0.1",
        "plotly~=6.1.2",
    ],
)
