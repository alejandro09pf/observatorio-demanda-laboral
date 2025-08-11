from setuptools import setup, find_packages

setup(
    name="labor-observatory",
    version="1.0.0",
    author="Nicolas Francisco Camacho Alarcon",
    description="Automated Labor Market Observatory for Latin America",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
    entry_points={
        "console_scripts": [
            "labor-observatory=orchestrator:app",
        ],
    },
)
