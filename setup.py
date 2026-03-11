from setuptools import find_packages, setup

setup(
    name="regexsolver",
    version="1.1.0",
    description="RegexSolver is a powerful toolkit for building, combining, and analyzing regular expressions.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="RegexSolver",
    author_email="contact@regexsolver.com",
    url="https://github.com/RegexSolver/regexsolver-python",
    license="MIT",
    keywords="regex regexp pattern intersection union difference concat equivalence subset nfa dfa",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "aiohttp>=3.8.4",
        "aiohttp-retry>=2.8.3",
        "python-dateutil>=2.8.2",
        "pydantic>=2.0.0",
        "typing-extensions>=4.7.1",
    ],
    extras_require={
        "test": [
            "pytest>=7.2.1",
            "pytest-cov>=2.8.1",
            "pytest-asyncio>=1.3.0",
            "tox>=3.9.0",
            "flake8>=4.0.0",
            "mypy>=1.5",
            "types-python-dateutil>=2.8.19.14",
        ]
    },
    python_requires=">=3.9",
    project_urls={
        "Homepage": "https://regexsolver.com/",
        "Issues": "https://github.com/RegexSolver/regexsolver-python/issues",
        "Documentation": "https://docs.regexsolver.com/",
        "Source Code": "https://github.com/RegexSolver/regexsolver-python",
    },
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
