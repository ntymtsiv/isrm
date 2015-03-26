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

import datetime
from functools import wraps
import json
import logging
import os
import sys
import uuid

import flask
from flask import abort
from flask import jsonify
from flask import request
from oslo.config import cfg

from isrm import cfg as config
from isrm import logger


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


app = flask.Flask('isrm')


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

        abort(401)
    return wrapper


@app.route('/', methods=['POST'])
@authenticate
def rebuild():
    try:
        data = request.json
    except Exception:
        LOG.error("Data is missing.")
        abort(400)
    mandatory = set(['deprecated_image', 'new_image'])
    if mandatory & set(data.keys()) != mandatory:
        missing = mandatory - set(data.keys())
        abort(400)
        LOG.error("Fields %s are missing." % str(missing))
    date_format = '%Y-%m-%dT%H:%M'
    if 'date' in data:
        try:
            date = datetime.datetime.strptime(data['date'], date_format)
        except ValueError:
            abort(400)
            LOG.error("Wrong format of date. Use Y-m-dTH:M")
    else:
        date = datetime.datetime.now()
    str_date = date.strftime('%Y_%m_%d_%H_%M')
    tenant = data.get('tenant_name', None)
    if not isinstance(tenant, list):
        tenant = [tenant]
    jobs = []
    for t in tenant:
        _data = data.copy()
        _data['tenant_name'] = t
        _uuid = str(uuid.uuid1())
        name = 'J'.join((str_date, _uuid))
        full_path = '/'.join((CONF.isrm_dir, name + '.json'))
        with open(full_path, 'w') as f:
            json.dump(_data, f, sort_keys=True, indent=4,
                      ensure_ascii=False)
            jobs.append({"id": _uuid,
                         "job_name": name,
                         "date": date.strftime('%Y-%m-%dT%H:%M')})
    return jsonify({"jobs": jobs})


def main():
    config.parse_args(sys.argv)
    logger.setup(log_file=CONF.log_file)
    isrm_dir = CONF.isrm_dir
    if not os.path.exists(isrm_dir):
        os.mkdir(isrm_dir)

    host, port = CONF.host, CONF.port
    try:
        app.run(host=host, port=port, debug=CONF.debug)
    except KeyboardInterrupt:
        pass
