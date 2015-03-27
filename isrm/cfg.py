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


from oslo_config import cfg


from isrm import version


common_opts = [
    cfg.StrOpt('host',
               default='127.0.0.1',
               help="Server host"),
    cfg.IntOpt('port',
               default=8080,
               help="Port number"),
    cfg.StrOpt('log_file',
               default='/var/log/isrm.log',
               help="ISRM log file"),
    cfg.StrOpt('auth_login',
               default='user',
               help="REST API login"),
    cfg.StrOpt('auth_password',
               default="password",
               help="REST API passord."),
    cfg.StrOpt('isrm_dir',
               default='/var/log/isrm',
               help="ISRM dir with json files for rebuilding"),
    cfg.ListOpt('public_network',
                default=[],
                help="List of public networks"),
    cfg.IntOpt('max_parallel_jobs',
               default=2,
               help="Max count of pararllel executed jobs."),
    cfg.IntOpt('instance_rebuild_timeout',
               default=2,
               help="Timeout between of rebuilding instances."),
]


openstack_group = cfg.OptGroup("openstack", "Openstack configuration group.")


openstack_opts = [
    cfg.StrOpt('auth_url',
               default='http://localhost:5000/v2.0',
               help="Auth url"),
    cfg.StrOpt('user',
               default='user',
               help="Openstack user"),
    cfg.StrOpt('password',
               default='password',
               help="Openstack password"),
    cfg.StrOpt('tenant',
               default='admin',
               help="Openstack tenant"),
]


CONF = cfg.CONF
CONF.register_opts(common_opts)
CONF.register_group(openstack_group)

CONF.register_opts(openstack_opts, openstack_group)


def parse_args(argv, default_config_files=None):
    cfg.CONF(args=argv[1:],
             project='cloudv_ostf_adapter',
             version=version.version,
             default_config_files=default_config_files)
