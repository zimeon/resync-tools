from distutils.core import setup

setup(
    name='resync-tools',
    version='0.1',
    packages=['resync_tools'],
    package_data={'resync_tools': ['testdata/*']},
    classifiers=["Development Status :: 3 - Alpha",
                 "Programming Language :: Python",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 "Environment :: Web Environment"],
    author='Simeon Warner',
    author_email='simeon.warner@cornell.edu',
    long_description=open('README').read(),
    url='http://github.com/resync/tools',
)
