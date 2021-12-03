# `creepy` docs using sphinx documentation generator

## Building documentation

To build the documentation:

1. Install `creepy`.

2. Install the prerequisites.

    ```bash
    cd docs
    pip install -r requirements.txt
    ```

3. Generate the documentation HTML files. The generated files will be in `docs/build/html`.

    ```bash
    cd docs
    make html
    ```

4. Run doctests.

    ```bash
    cd docs
    make doctest
    ```
