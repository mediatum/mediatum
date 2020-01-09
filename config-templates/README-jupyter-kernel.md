Jupyter Notebook Kernel
=======================

*(tested with Jupyter Notebook 4.1.0)*

`kernel.json.example ` is a mediaTUM development kernel definition file for Jupyter Notebook that runs a Python 2 interpreter in a nix shell with all mediaTUM dependencies.
mediaTUM packages can be imported in the notebook, for example: `import web.frontend`

-   create `~/.local/share/jupyter/kernels` if it doesn't exist
-   copy `kernel.json.example` to a new subdir: `~/.local/share/jupyter/kernels/nixenv-mediatum/kernel.json`
-   change the path in `kernel.json` to your location of the mediaTUM repository after `"argv"`
-   restart Jupyter Notebook and use the new Python 2 kernel called `nixenv mediatum`


