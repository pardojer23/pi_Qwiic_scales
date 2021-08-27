from setuptools import setup, find_packages


setup(name='pi_Qwiic_scales',
      version='0.01',
      description='Raspberry pi Qwiic scales',
      author='Jeremy Pardo',
      author_email='mezeg39@gmail.com',
      packages=find_packages(),
      install_requires=[
                'PyNAU7802',
                'smbus2',
                'sparkfun-qwiic',
                'PyDrive',
                'gspread',
                'oauth2client',
                'Cython',
                'pandas'])
