# `creepy` docs using sphinx documentation generator

## Building documentation

To build the documentation:

1. Go to the repository root.

2. Install `creepy` with its documentation dependencies.

    ```bash
    pip install '.[docs]'
    ```

3. Generate the documentation HTML files. The generated files will be in `docs/build/html`.

    ```bash
    make -C docs html
    ```

4. Run doctests.

    ```bash
    make -C docs doctest
    ```
