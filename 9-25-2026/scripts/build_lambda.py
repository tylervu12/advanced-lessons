"""Read third: prepare the files that CDK will upload to Lambda.

Run from the repo root: python scripts/build_lambda.py

Lambda needs our code AND the libraries it imports. This script collects both
in .build/lambda/. It prepares local files; it does not deploy anything to AWS.
"""

# shutil handles copying/removing files; subprocess runs another command.
# sys identifies the Python interpreter; Path helps build filesystem paths.
import shutil
import subprocess
import sys
from pathlib import Path

# __file__ is this script's path. Going up from scripts/ gives us the repo root.
# Using the script's location avoids depending on the terminal's current folder.
root = Path(__file__).resolve().parents[1]
output = root / ".build" / "lambda"

# Start with an empty package so old dependency files cannot survive a rebuild.
# Only .build/lambda/ is replaced; api/ and .venv/ are not touched.
if output.exists():
    shutil.rmtree(output)
output.mkdir(parents=True)

# Run pip using the same Python interpreter that is running this script.
# We pass arguments as a list; no shell command string is needed.
subprocess.run(
    [
        sys.executable, "-m", "pip", "install",

        # Install only runtime dependencies, not CDK or local development tools.
        "-r", str(root / "api" / "requirements.txt"),

        # Put the packages beside our Lambda code, instead of in .venv/.
        "--target", str(output),

        # Lambda runs Linux on x86_64 in this stack. Your laptop may run macOS
        # or Windows, so we explicitly download packages for Lambda's platform.
        "--platform", "manylinux2014_x86_64",

        # "cp" means CPython. Match the Python 3.11 runtime chosen in the stack.
        "--implementation", "cp",
        "--python-version", "3.11",

        # Use prebuilt wheels. Do not compile native extensions on this laptop.
        "--only-binary=:all:",

        # Skip optional bytecode generation while preparing the package.
        "--no-compile",
    ],
    # Stop with an error if pip fails, instead of reporting an incomplete build.
    check=True,
)

# Put main.py at the top of the package, beside fastapi/, mangum/, etc.
# That layout is why Lambda's configured handler is "main.handler".
shutil.copy2(root / "api" / "main.py", output / "main.py")
print("Lambda package ready in .build/lambda")
