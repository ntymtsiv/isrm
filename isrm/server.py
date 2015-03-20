#    Copyright 2015 Mirantis, Inc
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging
import sys

import eventlet
import flask
from flask.ext import restful
from oslo.config import cfg

from isrm import cfg as config
from isrm import logger
from isrm import controller
from keystoneclient.auth.identity import v2
from keystoneclient import session
from novaclient import client as nova_cli


eventlet.monkey_patch()
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


app = flask.Flask('isrm')
api = restful.Api(app)

api.add_resource(controller.Jobs, '/')


def main():
    config.parse_args(sys.argv)
    logger.setup(log_file=CONF.log_file)
    auth = v2.Password(auth_url=CONF.openstack.auth_url,
                       username=CONF.openstack.user,
                       password=CONF.openstack.password,
                       tenant_name=CONF.openstack.tenant)
    sess = session.Session(auth=auth)
    controller.NOVA_CLI = nova_cli.Client(2, session=sess)

    host, port = CONF.host, CONF.port
    try:
        app.run(host=host, port=port, debug=CONF.debug)
    except KeyboardInterrupt:
        pass
