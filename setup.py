#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO - DO NOT EDIT
from setuptools import setup, find_packages

setup(
    name="isrm",
    version="0.1",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'isrm=isrm.server:main']},

    # metadata for upload to PyPI
    description="Rebuilding of instances service",
    license="Apache Software License",
)
