Getting Started
===============

First, let's make sure that your API authentication tokens have been imported into cbapi. Once that's done, then read
on for the key concepts that will explain how to interact with Carbon Black APIs via cbapi.

Feel free to follow along with this document or watch the
`Development Environment Setup video <https://developer.carbonblack.com/guide/enterprise-response/development-environment-video/>`_
on the Developer Network website.

API Authentication
------------------

VMware Carbon Black EDR and App Control use a per-user API secret token to authenticate requests via the API. The API
token confers the same permissions and authorization as the user it is associated with, so protect the API token with
the same care as a password.

To learn how to obtain the API token for a user, see the Developer Network website: there you will find instructions
for obtaining an API token for `EDR <https://developer.carbonblack.com/reference/enterprise-response/authentication/>`_
and `App Control <https://developer.carbonblack.com/reference/enterprise-protection/authentication/>`_.

Once you have the API token, cbapi helps keep your credentials secret by enforcing the use of a credential file. To
encourage sharing of scripts across the community while at the same time protecting the security of our customers,
cbapi strongly discourages embedding credentials in individual scripts. Instead, you can place credentials for several
EDR or App Control servers inside the API credential file and select which "profile" you would like to use
at runtime.

To create the initial credential file, a simple-to-use script is provided. Just run the ``cbapi-response``,
``cbapi-protection``, or ``cbapi-psc`` script with the ``configure`` argument. On Mac OS X and Linux::

    $ cbapi-response configure

Alternatively, if you're using Windows (change ``c:\python27`` if Python is installed in a different directory)::

    C:\> python c:\python27\scripts\cbapi-response configure

This configuration script will walk you through entering your API credentials and will save them to your current user's
credential file location, which is located in the ``.carbonblack`` directory in your user's home directory.

If using cbapi-psc, you will also be asked to provide an org key. An org key is required to access the Carbon Black
Cloud, and can be found in the console under Settings -> API Keys.

Your First Query
----------------

Now that you have cbapi installed and configured, let's run a simple query to make sure everything is functional::

    $ python
    Python 2.7.10 (default, Jun 22 2015, 12:25:23)
    [GCC 4.2.1 Compatible Apple LLVM 6.1.0 (clang-602.0.53)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from cbapi.response import *
    >>> c = CbResponseAPI()
    >>> print(c.select(Process).first().cmdline)
    C:\Windows\system32\services.exe

That's it! Now on to the next step, learning the concepts behind cbapi.
