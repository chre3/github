"""
MCP GitHub App - GitHub App MCP服务器
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mcp-github-app",
    version="1.0.0",
    author="chre3",
    author_email="chremata3@gmail.com",
    description="GitHub App MCP服务器，提供完整的GitHub操作功能",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chre3/mcp-github-app",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Version Control :: Git",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.18.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.910",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5",
        ],
    },
    entry_points={
        "console_scripts": [
            "mcp-github-app=mcp_github_app.server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "mcp_github_app": ["config/*.json", "docs/*.md"],
    },
    keywords="github app mcp server",
    project_urls={
        "Bug Reports": "https://github.com/chre3/mcp-github-app/issues",
        "Source": "https://github.com/chre3/mcp-github-app",
        "Documentation": "https://github.com/chre3/mcp-github-app/blob/main/README.md",
    },
)
