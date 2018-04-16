"""
dqm_client
A front-end client to DQM
"""
import setuptools
import versioneer

DOCLINES = __doc__.split("\n")

setuptools.setup(
    name='dqm_client',
    author='The Molecular Sciences Software Institute',
    description=DOCLINES[0],
    long_description="\n".join(DOCLINES[2:]),
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license='BSD-3-Clause',
    packages=setuptools.find_packages(),
    #packages=['dqm_client', "dqm_client.tests", "dqm_client.data", "dqm_client.schema"],
    # Optional include package data to ship with your package
    #package_data={
    #    'dqm_client': ["dqm_client/data/*.json"]
    #},
    include_package_data=True,
    install_requires=["numpy"],
    # Additional entries you may want simply uncomment the lines you want and fill in the data
    # author_email='me@place.org',      # Author email
    # url='http://www.my_package.com',  # Website
    # platforms=['Linux',
    #            'Mac OS-X',
    #            'Unix',
    #            'Windows'],            # Valid platforms your code works on, adjust to your flavor
    zip_safe=False,                   # Compress final package or not
    # python_requires=">=3.5",          # Python version restrictions
)
