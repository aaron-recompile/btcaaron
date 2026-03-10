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
    keywords=[
        "bitcoin",
        "taproot",
        "tapscript",
        "bip341",
        "bip342",
        "schnorr",
        "p2tr",
        "taptree",
        "script-path",
        "miniscript",
        "psbt",
        "regtest",
        "testnet",
    ],
    packages=find_packages(),
    install_requires=[
         "requests>=2.25.0,<3.0.0",
         "bitcoin-utils>=0.7.3,<0.8.0"
    ],
    entry_points={
        "console_scripts": [
            "btcaaron-doctor=btcaaron_doctor:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: Security :: Cryptography",
    ],
    python_requires=">=3.10,<3.13",
)