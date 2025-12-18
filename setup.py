from setuptools import setup, find_packages

setup(
    name='steam-audio-isolator',
    version='0.1.6',
    description='Isolate game audio for clean Steam game recording on Linux',
    long_description=open('README.md').read() if __import__('os').path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='Steam Audio Isolator Contributors',
    url='https://github.com/yourusername/steam-audio-isolator',
    packages=find_packages(),
    install_requires=[
        'PyQt5>=5.15.0',
        'pydbus>=0.6.0',
    ],
    entry_points={
        'console_scripts': [
            'steam-audio-isolator=steam_pipewire.main:main',
        ],
        'gui_scripts': [
            'steam-audio-isolator-gui=steam_pipewire.main:main',
        ],
    },
    data_files=[
        ('share/applications', ['steam-audio-isolator.desktop']),
    ],
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Sound/Audio',
    ],
)
