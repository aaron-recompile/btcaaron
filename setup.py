from setuptools import setup, find_packages

setup(
    name="btcaaron",
    version="0.2.1",
    description="A Bitcoin Testnet transaction toolkit supporting Legacy, SegWit, and Taproot",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Aaron Zhang",
    author_email="aaron.recompile@gmail.com",   
    url="https://x.com/aaron_recompile",
    packages=find_packages(),
    install_requires=[
         "requests>=2.25.0",
         "bitcoin-utils>=0.7.1"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.7",
)