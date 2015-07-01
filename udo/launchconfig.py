import config
import util
import cluster

import re
import os
import sys
from pprint import pprint
from string import Template

import boto
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale import LaunchConfiguration

_cfg = config.Config()

class LCTemplate(Template):
    delimiter = '@'

# cloud-init shell script template
cloud_init_script = '''
#!/bin/bash

# Initialize a base system, provision via RPM installation
# Read by LaunchConfig

CLUSTER_NAME="@cluster_name"
ROLE_NAME="@role_name"

# Our stuff goes in here
BOOTSTRAP_DIR=/root/.udo
mkdir -p $BOOTSTRAP_DIR

# set up Yum S3 IAM plugin
if [[ -n "@yum_plugin_url" ]]; then
    curl @yum_plugin_url \
        > $BOOTSTRAP_DIR/yum-plugin-s3-iam.noarch.rpm
    rpm -i $BOOTSTRAP_DIR/yum-plugin-s3-iam.noarch.rpm
fi

# add our app yum repo
if [[ -n "@repo_url" ]]; then
    cat > /etc/yum.repos.d/@{app_name}.repo <<YUMREPO
[@app_name]
name=@app_name
baseurl=@repo_url
enabled=1
s3_enabled=1
gpgcheck=0
YUMREPO
fi

# load up repo metadata
yum makecache

# your stuff from cloud_init config
# pre-package-setup
@cloud_init_pre

######

# install updates
yum update -y

## install packages
# base system
if [[ -n "@base_packages" ]]; then
    yum install -y @base_packages
fi
# role packages
if [[ -n "@role_packages" ]]; then
    yum install -y @role_packages
fi

# custom post-init hook
@cloud_init_post


# might not be a bad idea to reboot after updating everything?
#/sbin/reboot now
'''

#####


class LaunchConfig:
    def __init__(self, cluster_name, role_name):
        self.cluster_name = cluster_name
        self.role_name = role_name
        self.role_config = config.get_role_config(cluster_name, role_name)
        self.conn = util.as_conn()
        self._name = "-".join([self.cluster_name, self.role_name])

    # have a default name, but can be overridden
    def name(self):
        return self._name
    def set_name(self, name):
        self._name = name

    # processes the cloud-init template, returns a string
    def cloud_init_script(self):
        # load cloud-init script template
        cloud_init_template = LCTemplate(cloud_init_script)

        cloud_init_config = _cfg.get_root()

        # add extra template vars
        cloud_init_config['base_packages'] = " ".join(_cfg.get('packages')) or ''
        cloud_init_config['yum_plugin_url'] = _cfg.get('repo', 'plugin_url') or ''
        # from role config
        cloud_init_config['role_packages'] = " ".join(self.role_config.get('packages')) or ''
        cloud_init_config['repo_url'] = self.role_config.get('repo_url') or ''

        # append extra commands from config
        cloud_init_config['cloud_init_pre'] = _cfg.get('cloud_init') or _cfg.get('cloud_init_pre') or ''
        cloud_init_config['cloud_init_post'] = _cfg.get('cloud_init_post') or ''

        cloud_init_config['cluster_name'] = _self.cluster_name or ''
        cloud_init_config['role_name'] = self.role_name or ''

        cloud_init = cloud_init_template.substitute(**cloud_init_config)
        return cloud_init

    # does a LC exist with our name?
    def exists(self):
        lc = self.get_lc()
        if lc:
            return True
        return False

    # we can't modify a launchconfig in place, we have to create
    # a new one. returns new udo.lc
    def update(self):
        if not self.exists():
            # easy, just create it
            print "not exists"
            self.activate()
            return self
        # generate a name for the new lc version
        name = self.name()
        vermatch = re.search(r'-v(\d+)$', name)
        if vermatch:
            # increment version #
            ver = int(vermatch.group(1))
            ver = ver+1
            name = re.sub(r'-v(\d+)$', '-v'+str(ver), name)
        else:
            name = name + '-v2'
        # create the new lc and return it
        newlc = LaunchConfig(self.cluster_name, self.role_name)
        newlc.set_name(name)
        newlc.activate()
        return newlc

    def get_lc(self):
        conn = util.as_conn()
        lcs = conn.get_all_launch_configurations(names = [self.name()])
        if not len(lcs):
            return None
        return lcs[0]

    def deactivate(self):
        if not self.exists():
            return
        print "Deleting launchconfig..."
        lc = self.get_lc()
        if util.retry(lambda: lc.delete(), 500):
            util.message_integrations("Deleted LaunchConfig {}".format(self.name()))
        else:
            util.message_integrations("Failed to delete LaunchConfig {}".format(self.name()))

    # creates the LaunchConfig
    # returns True if LC exists
    def activate(self):
        conn = util.as_conn()
        conn = boto.ec2.autoscale.connect_to_region('us-west-2')

        name = self.name()

        # check if this LC already exists
        if self.exists():
            if not util.confirm("LaunchConfig {} already exists, overwrite?".format(name)):
                return True
            # delete existing
            conn.delete_launch_configuration(name)

        # get configuration for this LC
        cfg = self.role_config
        lc = LaunchConfiguration(
            name = name,
            image_id = cfg.get('ami'),
            instance_profile_name = cfg.get('iam_profile'),
            instance_type = cfg.get('instance_type'),
            security_groups = cfg.get('security_groups'),
            key_name = cfg.get('keypair_name'),
            user_data = self.cloud_init_script(),
            associate_public_ip_address = True,  # this is required for your shit to actually work
        )
        if not conn.create_launch_configuration(lc):
            print "Error creating LaunchConfig {}".format(name)
            return False

        util.message_integrations("Activated LaunchConfig {}".format(name))

        return lc
