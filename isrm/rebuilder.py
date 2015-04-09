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
import json
import logging
import multiprocessing
import os
import sys
import time

from oslo.config import cfg

from isrm import cfg as config
from isrm import constants
from isrm import logger
from keystoneclient.v2_0 import client
from keystoneclient.auth.identity import v2
from keystoneclient import session
from novaclient import exceptions
from novaclient import client as nova_cli


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class Reader(object):

    def _get_cli(self):
        auth = v2.Password(auth_url=CONF.openstack.auth_url,
                           username=CONF.openstack.user,
                           password=CONF.openstack.password,
                           tenant_name=CONF.openstack.tenant)
        sess = session.Session(auth=auth)
        keystone = client.Client(auth_url=CONF.openstack.auth_url,
                                 username=CONF.openstack.user,
                                 password=CONF.openstack.password,
                                 tenant_name=CONF.openstack.tenant)
        keystone = client.Client(endpoint=CONF.openstack.auth_url,
                                 token=keystone.auth_token)
        self.tenants = dict([(t.name, t.id) for t in keystone.tenants.list()])
        return nova_cli.Client(2, session=sess)

    def _rebuild_instances(self, instances, image, nova_cli):
        for i in instances:
            uuid = i.id
            try:
                i.rebuild(image)
                LOG.info("Rebuild for instance %s is started."
                         " Expected image %s." % (uuid, image))
            except exceptions.BadRequest as e:
                LOG.error("Rebuld for instance %s was failed."
                          " %s" % (uuid, e.message))
            except exceptions.Conflict as e:
                LOG.error("Instance %s in rebuilding state." % uuid)
            except Exception as e:
                LOG.error("Unexpected error %s." % e.message)
            time.sleep(CONF.instance_rebuild_timeout)

    def _has_floating(self, instance):
        for k, v in instance.to_dict()['addresses'].iteritems():
            for ip in v:
                if 'floating' in ip.values():
                    return True
        return False

    def _rebuild(self, data, f_name):
        image_old = data[constants.DEPRECEATED_IMAGE]
        image_new = data[constants.NEW_IMAGE]
        tenant_name = data.get(constants.TENANT_NAME, None)
        nova_cli = self._get_cli()
        search_opts = {'all_tenants': 1, 'image': image_old}
        if tenant_name is not None:
            tenant_id = self.tenants.get(tenant_name, None)
            if tenant_id is None:
                LOG.error("Tenant %s was not found." % tenant_name)
                return
            search_opts['tenant_id'] = tenant_id
        instances = nova_cli.servers.list(search_opts=search_opts)
        filtered = []
        for i in instances:
            public = set(i.networks.keys()) & set(CONF.public_network)
            has_floating = self._has_floating(i)
            if not public and not has_floating:
                filtered.append(i)
        self._rebuild_instances(filtered, image_new, nova_cli)
        os.remove(f_name)

    def find_files(self):
        now = datetime.datetime.now()
        isrm_d = CONF.isrm_dir
        all_files = [f for (dp, dn, f) in os.walk(isrm_d)][0]
        active_jobs = [f for f in all_files if 'lock' in f]
        if len(active_jobs) >= CONF.max_parallel_jobs:
            LOG.info("Maximum count of jobs is running. Wait.")
            return
        new_jobs = [f for f in all_files if 'lock' not in f]

        actual_jobs = []
        for f in new_jobs[:CONF.max_parallel_jobs]:
            dt = f.split('J')[0]
            date_format = '%Y_%m_%d_%H_%M'
            planned = datetime.datetime.strptime(dt, date_format)
            if planned <= now:
                actual_jobs.append(f)

        for f in actual_jobs:
            f_name_old = '/'.join((isrm_d, f))
            f_name = f_name_old + '.lock'
            os.rename(f_name_old, f_name)
            with open(f_name, 'r') as f:
                try:
                    data = json.loads(f.read())
                except ValueError:
                    LOG.error("%s was skipped due to broken "
                              "JSON format." % f_name)
                    data = None

                if data is not None:
                    LOG.info("Starts with %s." % f_name)
                    p = multiprocessing.Process(target=self._rebuild,
                                                args=(data, f_name,))
                    p.start()

    def unlock_files(self):
        isrm_d = CONF.isrm_dir
        files = [f for (dp, dn, f) in os.walk(isrm_d)][0]
        for f in files:
            if 'lock' not in f:
                continue
            f_name_old = '/'.join((isrm_d, f))
            f_name = f_name_old[:-5]
            os.rename(f_name_old, f_name)


def main():
    config.parse_args(sys.argv)
    logger.setup(log_file=CONF.log_file, rebuilder=True)

    reader = Reader()
    LOG.info("Start json handler in %s dir" % CONF.isrm_dir)
    reader.unlock_files()
    while True:
        try:
            reader.find_files()
        except Exception as e:
            LOG.error(e.message)
            break
        time.sleep(10)
