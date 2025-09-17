How to upload my plugin or package to PyPI?
============================================

The first step is to ensure that you have the detailed structure outlined in the following file:

:doc:`plugin_structure`

Then, before uploading the plugin to PyPI, it's necessary to ensure that it works. Some recommendations for testing it and the steps to follow to create a plugin are available on the following page:

:doc:`plugin_develop`

Finally, ensuring that the above documents have been reviewed, you can create the package on PyPI to upload the plugin.

Tutorial for uploading plugin or package to PyPI
--------------------------------------------------

**IMPORTANT:** The following tutorial uses twine to upload the package to PyPI. However, there are many other ways to do it, and you are free to use any.

1. Package the files. To do this, run the following commands:

   .. code-block:: powershell

      python -m pip install --upgrade build
      python -m build

   The following files will be created:

   .. code-block:: text

      +---dist
            |  plugin-name-0.0.1--none-any.whl
            |  plugin-name-0.0.1.tar.gz

2. Request a token from PyPI. This is shown on the following page, in the section "**How do I use API tokens to authenticate with PyPI?**"

   `Help <https://test.pypi.org/help/#apitoken>`_

   Using Twine, this is necessary for PyPI security measures.

3. Upload the package to test PyPI. To do this, run the following commands:

   **IMPORTANT:** PyPI has a testing version for uploading plugins and testing that they work well when downloaded. For this, replace **"pypi"** with **"testpypi"** in the following snippet.

   .. code-block:: powershell

      python -m pip install --upgrade twine
      python -m twine upload --repository pypi dist/*

   If the token is properly configured, there should be no problem.

With this, the plugin will be uploaded.
