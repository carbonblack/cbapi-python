"""
cbapi-python
"""

from setuptools import setup
import sys

packages = ['cbapi', 'cbapi.protection', 'cbapi.response', 'cbapi.cache']
if sys.version_info < (3, 0):
    packages.extend(['cbapi.legacy', 'cbapi.legacy.util'])

install_requires=[
    'requests',
    'attrdict',
    'cachetools',
    'six',
    'pyyaml',
    'pika',
    'prompt_toolkit',
    'pygments',
    'python-dateutil'
]
if sys.version_info < (2, 7):
    install_requires.extend(['simplejson', 'total-ordering', 'ordereddict'])
if sys.version_info < (3, 0):
    install_requires.extend(['futures'])

setup(
    name='cbapi',
    version='0.9.8',
    url='https://github.com/carbonblack/cbapi-python',
    license='MIT',
    author='Carbon Black',
    author_email='dev-support@carbonblack.com',
    description='Carbon Black REST API Python Bindings',
    packages=packages,
    include_package_data=True,
    package_dir = {'': 'src'},
    zip_safe=False,
    platforms='any',
    install_requires=install_requires,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    scripts=['bin/cbapi-response', 'bin/cbapi-protection']
)
