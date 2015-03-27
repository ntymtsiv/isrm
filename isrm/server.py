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
import signal
import sys
import uuid

import flask
from flask import abort
from flask import jsonify
from flask import request
from keystoneclient.v2_0 import client
from keystoneclient import exceptions
from oslo.config import cfg

from isrm import cfg as config
from isrm import constants
from isrm import logger


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


app = flask.Flask('isrm')


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(func, 'authenticated', True):
            return func(*args, **kwargs)

        try:
            data = request.json
        except Exception:
            data = {}
        tenant_json = data.get(constants.TENANT_NAME, None)

        filters = dict(request.args)
        tenants_data = filters.get(constants.TENANT_NAME, [None])
        tenant = tenant_json or tenants_data

        if not isinstance(tenant, list):
            tenant = [tenant]

        creds = request.authorization
        if creds is None:
            abort(401)
        tenant_name = tenant[0] or CONF.openstack.tenant
        try:
            keystone = client.Client(auth_url=CONF.openstack.auth_url,
                                     username=creds['username'],
                                     password=creds['password'],
                                     tenant_name=tenant_name)
            roles = keystone.auth_ref['user']['roles']
            roles_name = [t['name'] for t in roles]
        except exceptions.Unauthorized:
            abort(401)

        is_admin = 'admin' in roles_name
        if is_admin:
            allowed_tenants = [t.name for t in keystone.tenants.list()]
            filter_tenants = set(tenant)
        else:
            allowed_tenants = [tenant_name]
            filter_tenants = set(tenant) & set(allowed_tenants)
        _data = data.copy()
        _data[constants.TENANT_NAME] = filter_tenants
        _data['allowed_tenants'] = allowed_tenants
        _data['is_admin'] = is_admin
        post_or_delete = request.method in ['POST', 'DELETE']
        get = request.method == 'GET'

        if is_admin or (filter_tenants and post_or_delete)\
                or (allowed_tenants and get):
            return func(_data, *args, **kwargs)

        abort(401)
    return wrapper


@app.route('/', methods=['POST'])
@authenticate
def rebuild(data):
    mandatory = set([constants.DEPRECEATED_IMAGE,
                     constants.NEW_IMAGE])
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
    tenant = data.get(constants.TENANT_NAME)
    jobs = []
    for t in tenant:
        _data = data.copy()
        _data['tenant_name'] = t
        _data['date'] = date.strftime(date_format)
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


def get_all_jobs():
    jobs = []
    isrm_d = CONF.isrm_dir
    all_files = [f for (dp, dn, f) in os.walk(isrm_d)][0]
    for f in all_files:
        f_name = '/'.join((isrm_d, f))
        with open(f_name, 'r') as f:
            try:
                data = json.loads(f.read())
            except ValueError:
                continue
            data.update({"id": f_name.split("J")[1][:-5],
                         "job_name": f_name})
            jobs.append(data)
    return jobs


def get_name(jobs, name):
    full_name = 'J%s.json' % name
    for f in jobs:
        if full_name in f:
            return f
    abort(404)


@app.route('/jobs', methods=['GET'])
@authenticate
def get_jobs(data):
    filters = dict(request.args)
    tenants = filters.get(constants.TENANT_NAME, [None])
    tenants = set(tenants) or set(data['allowed_tenants'])
    data[constants.TENANT_NAME] = tenants
    allowed_filters_fields = [constants.DEPRECEATED_IMAGE,
                              constants.NEW_IMAGE,
                              constants.TENANT_NAME]
    jobs = get_all_jobs()
    if 'status' in filters:
        if 'active' in filters['status']:
            jobs = [j for j in jobs if '.lock' in j['job_name']]
        else:
            jobs = []
    if 'date' in filters:
        jobs = [j for j in jobs if filters['date'][0] in j['date']]
    filter_fields = set(allowed_filters_fields) & set(filters.keys())
    for field in filter_fields:
        jobs = [j for j in jobs if j[field] in filters[field]]
    return jsonify({"jobs": jobs})


@app.route('/job/<job_id>', methods=['GET'])
@authenticate
def get_job(data, job_id):
    isrm_d = CONF.isrm_dir
    all_files = [f for (dp, dn, f) in os.walk(isrm_d)][0]
    f_name = get_name(all_files, job_id)
    full_name = '/'.join((isrm_d, f_name))
    with open(full_name, 'r') as f:
        try:
            _data = json.loads(f.read())
            job_tenants = [_data[constants.TENANT_NAME]]
            is_admin = data['is_admin']
            if is_admin or (set(job_tenants) & set(data['allowed_tenants'])):
                _data.update({"id": job_id})
            else:
                abort(401)
        except ValueError:
            return jsonify({"error": "failed json format"})
    return jsonify({"job": _data})


@app.route('/job/<job_id>', methods=['DELETE'])
@authenticate
def delete_job(data, job_id):
    isrm_d = CONF.isrm_dir
    all_files = [f for (dp, dn, f) in os.walk(isrm_d)][0]
    f_name = get_name(all_files, job_id)
    full_name = '/'.join((isrm_d, f_name))
    with open(full_name, 'r') as f:
        try:
            _data = json.loads(f.read())
            job_tenants = [_data[constants.TENANT_NAME]]
            is_admin = data['is_admin']
            allowed_tenants = data['allowed_tenants']
            if not (is_admin or (set(job_tenants) & set(allowed_tenants))):
                abort(401)
        except ValueError:
            return jsonify({"error": "failed json format"})
    try:
        os.remove(full_name)
        status = 'deleted'
    except OSError:
        status = "failed (no such file)"
    return jsonify({"status": status})


def main():
    config.parse_args(sys.argv)
    logger.setup(log_file=CONF.log_file)
    isrm_dir = CONF.isrm_dir
    if not os.path.exists(isrm_dir):
        os.mkdir(isrm_dir)

    host, port = CONF.host, CONF.port
    try:
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        app.run(host=host, port=port, debug=CONF.debug)
    except KeyboardInterrupt:
        pass
