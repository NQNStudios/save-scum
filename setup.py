from setuptools import setup

setup(name='save-scum',
      version='0.0.0',
      description='Selectively version control your system',
      url='http://github.com/NQNStudios/save-scum',
      author='Nat Quayle Nelson',
      author_email='natquaylenelson@gmail.com',
      license='GPL-3.0',
      packages=['savescum'],
      install_requires=[i.strip() for i in open("requirements.txt").readlines()],
      include_package_data=True,
      zip_safe=False)
