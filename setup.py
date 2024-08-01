from setuptools import setup, find_packages

setup(
    name="regexsolver",
    version="1.0.0",
    description="RegexSolver allows you to manipulate regular expressions as sets, enabling operations such as intersection, union, and subtraction.",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author="RegexSolver",
    author_email="contact@regexsolver.com",
    url="https://github.com/RegexSolver/regexsolver-python",
    license="MIT",
    keywords="regex regexp set intersection union subtraction difference equivalence subset nfa dfa",
    packages=find_packages(exclude=["tests", "tests.*"]),

    install_requires=[
        'requests>=2.20.0',
        'pydantic<=2.5.3, >2.4.0; python_version<"3.8"',
        'pydantic>=2.6.0; python_version>="3.8"'
    ],
    python_requires='>=3.7',
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
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
