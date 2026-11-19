# Automated tests

The test suite uses Python's standard-library `unittest` framework and mocks all GLPI network calls. No GLPI server or credentials are required.

Run the complete suite from the repository root:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

GitHub Actions runs the same command on pushes to `main` and `test/**` branches, and on pull requests targeting `main`, using Python 3.11 and 3.12.
