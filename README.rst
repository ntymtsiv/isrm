=============
ISRM
=============

Overview
--------

REST API service that make possible rebuild of instance with new image.
All volumes, ports and other specific information about VM will be saved.

List of supported URL's:
 - POST /
 - GET /jobs
     list of filtered params:
         - status (active),
         - date (format "2015-03-25T15:55"),
         - new_image,
         - deprecated_image,
         - tenant_name.
 - GET /job/<job_id>
 - DELETE /job/<job_id>

Example of data:

.. code-block:: bash

  {
    "new_image": "039f1b78-e114-47bc-87b5-22c67c35e49d",
    "deprecated_image": "c7360e10-c352-418c-99f2-065e1318aa2d",
    "tenant_name": ["demo", "admin"],
    "date": "2015-03-25T15:55"
  }

Example of response:

.. code-block:: bash

  {   
    "jobs": [
      {   
        "date": "2015-03-26T10:27",
        "id": "8c4c9ddc-d389-11e4-b9f7-14dae9dfafc6",
        "job_name": "2015_03_26_10_27J8c4c9ddc-d389-11e4-b9f7-14dae9dfafc6"
      }
    ]
  }


Example of config
-----------------

.. code-block:: bash

  [DEFAULT]
  host=localhost
  port=8080
  auth_login=user
  auth_password=password
  log_file=/var/log/isrm.log
  isrm_dir=/var/log/isrm
  public_network=net1,net2
  max_parallel_jobs=2
  instance_rebuild_timeout=2

  [openstack]
  auth_url=http://localhost:5000/v2.0
  user=user
  password=password
  tenant=admin

Usage
-----
Run REST API server that will store json in isrm_dir.

.. code-block:: bash

  $ isrm --config-file=../isrm.conf
   * Running on http://127.0.0.1:8080/ (Press CTRL+C to quit)
   * Restarting with stat

Run json handler by command:

.. code-block:: bash

  isrm_rebuilder --config-file=/home/sshturm/Documents/isrm.conf 
  2015-03-24 15:16:54 INFO (rebuilder) Start json handler in /var/log/isrm dir
