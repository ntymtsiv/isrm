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
from functools import wraps
import logging

import eventlet
from flask import request
from flask.ext import restful
from flask.ext.restful import abort
from novaclient import exceptions
from oslo.config import cfg


CONF = cfg.CONF
LOG = logging.getLogger(__name__)
NOVA_CLI = None


def rebuild(instances):
    for i in instances:
        uuid = i.get('instance', None)
        image = i.get('image', None)
        if uuid is None or image is None:
            LOG.error("Instance or image field is missing.")
        try:
            instance = NOVA_CLI.servers.get(uuid)
        except exceptions.NotFound as e:
            LOG.error("Instance `%s` was not found." % uuid)
            continue
        if instance.image['id'] == image:
            LOG.info("Task for instance %s was skipped."
                     " It is rebuilded." % uuid)
            continue
        try:
            instance.rebuild(image)
            LOG.info("Rebuild for instance %s is started."
                     " Expected image %s." % (uuid, image))
        except exceptions.BadRequest as e:
            LOG.error("Rebuld for instance %s was failed."
                      " %s" % (uuid, e.message))
            continue


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(func, 'authenticated', True):
            return func(*args, **kwargs)

        creds = request.authorization
        if creds is None:
            abort(401)
        user = creds['username']
        password = creds['password']
        acct = user == CONF.auth_login and password == CONF.auth_password
        if acct:
            return func(*args, **kwargs)

        restful.abort(401)
    return wrapper


class Jobs(restful.Resource):

    method_decorators = [authenticate]

    def post(self):
        try:
            data = request.json
        except Exception:
            abort(400, message="Data is missing.")
        if 'instances' not in data:
            abort(400, message="Instances is missing in data.")
        eventlet.spawn_n(rebuild, data['instances'])
        return {"status": "started"}
