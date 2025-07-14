from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="async-easy-model",
    version="0.3.8",
    author="Pablo Schaffner",
    author_email="pablo@puntorigen.com",
    description="A simplified SQLModel-based ORM for async database operations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/puntorigen/easy-model",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        "sqlmodel>=0.0.8",
        "sqlalchemy>=2.0.0",
        "asyncpg>=0.25.0",
        "aiosqlite>=0.19.0",
        "greenlet>=3.1.1",
        "inflection>=0.5.1",  # Added dependency for handling pluralization
    ],
    keywords=["orm", "sqlmodel", "database", "async", "postgresql", "sqlite"],
)
