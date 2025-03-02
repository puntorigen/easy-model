#!/bin/bash

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/

# Build the package
echo "Building package..."
python setup.py sdist bdist_wheel

# Check the built package
echo "Package details:"
ls -l dist/

echo "To publish to PyPI, run:"
echo "python -m twine upload dist/*"
