# Running the Example Scripts

To run the example scripts, first set up the CBAPI with either the `pip install cbapi` or `python setup.py develop`
commands as detailed in the top-level `README.md` file.  You may also set your `PYTHONPATH` environment variable to
point to the `{cbapi}/src` directory, where `{cbapi}` refers to the top-level directory where you have cloned
the CBAPI repository.

You should also have an API key and have set up a `credentials` file as detailed in the "API Token" section of the
top-level `README.md` file.

Once you have done so, you should be able to run any example script with the command:

		python scriptname.py [arguments]

Executing any script with the `--help` argument should give you a detailed message about the arguments that can
be supplied to the script when it is executed.

### Note: Users of Carbon Black Cloud must transition to the Carbon Black Cloud Python SDK.

Please see
<https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/python-sdk>`_
for details.

CBAPI is not maintained for Carbon Black Cloud.