from setuptools import setup, find_packages

setup(
    name='comfyenv',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='ComfyUI Environment Manager CLI Tool',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/comfyenv',
    packages=find_packages(),
    install_requires=[
        'click',
        'PyYAML',
        'docker'
    ],
    entry_points={
        'console_scripts': [
            'comfyenv=comfyenv.cli:cli',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)
