"""
Setup script for usim800 package.

Fork of: https://github.com/Bhagyarsh/usim800
"""
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="usim800",
    version="1.0.0",
    author="Ante Eres (original: Bhagyarsh Dhumal)",
    description="Robust Python driver for SIM800 GSM/GPRS module",
    url="https://github.com/anteeres/usim800",
    project_urls={
        "Bug Tracker": "https://github.com/anteeres/usim800/issues",
        "Original Library": "https://github.com/Bhagyarsh/usim800",
        "Documentation": "https://github.com/anteeres/usim800#readme",
    },
    packages=setuptools.find_packages(exclude=("tests", "examples")),
    python_requires=">=3.7",
    install_requires=[
        "pyserial>=3.5",
    ],
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Telephony",
        "Topic :: System :: Hardware",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
    ],
    keywords=[
        "SIM800", "SIM800L", "GSM", "GPRS", "2G",
        "HTTP", "SMS", "IoT", "serial", "AT commands",
        "raspberry pi", "embedded", "cellular"
    ],
)
