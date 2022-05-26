import subprocess
import sys


def main():
    subprocess.run(
        ["poetry", "run", "python", "src/waxtax"], stderr=sys.stderr, stdout=sys.stdout
    )
