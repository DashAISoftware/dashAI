import os

from setuptools import find_packages, setup

with open("README.rst") as f:
    long_description = f.read()


def load_requirements(filename):
    """Load requirements from a file, ignoring comments and empty lines."""
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


# Use your existing requirements files
requirements = load_requirements("requirements.txt")
test_requirements = load_requirements("requirements-dev.txt")


setup(
    name="DashAI",
    version="0.1.2",
    license="MIT",
    description=(
        "DashAI: a graphical toolbox for training, evaluating and deploying "
        "state-of-the-art AI models."
    ),
    long_description=long_description,
    url="https://github.com/OpenCENIA/DashAI",
    project_urls={
        "Documentation": "https://dash-ai.com/",
        "Changelog": "https://dash-ai.com/changelog.html",
        "Issue Tracker": "https://github.com/DashAISoftware/DashAI/issues",
    },
    author="DashAI Team",
    author_email="fbravo@dcc.uchile.cl",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=requirements,
    test_require=test_requirements,
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "dashai = DashAI:run",
            "DashAI = DashAI:run",
        ]
    },
)
