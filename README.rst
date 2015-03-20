=============
ISRM
=============

Overview
--------

REST API service that make possible rebuild of instance with new image.
All volumes, ports and other specific information about VM will be saved.

List of supported URL's:
 - POST /

Example of data:

.. code-block:: bash

  {"instances": [
    {"instance" : "instance_uuid1", "image": "image_uuid"},
    {"instance" : "instance_uuid2", "image": "image_uuid"}]
  }

Example of response:

.. code-block:: bash

  {
    "status": "started"
  }


Example of config
-----------------

.. code-block:: bash

  [DEFAULT]
  host=localhost
  port=8080
  debug=False
  auth_login=user
  auth_password=password
  log_file=/var/log/isrm.log

  [openstack]
  auth_url=http://localhost:5000/v2.0
  user=user
  password=password
  tenant=admin

Usage
-----
.. code-block:: bash

  $ isrm --config-file=../isrm.conf
   * Running on http://127.0.0.1:8080/ (Press CTRL+C to quit)
   * Restarting with stat
