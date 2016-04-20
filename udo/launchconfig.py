import boto3
import os
import re
import sys
from pprint import pprint
from string import Template

import cluster
import config
import util

from time import sleep
from util import debug

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

# cloud_init_extra
@cloud_init_extra

# custom post-init hook
@cloud_init_post


# might not be a bad idea to reboot after updating everything?
#/sbin/reboot now
'''

class LaunchConfig:
    def __init__(self, cluster_name, role_name):
        self.cluster_name = cluster_name
        self.role_name = role_name
        self.role_config = config.get_role_config(cluster_name, role_name)
        self.conn = util.as_conn()
        self._name = "-".join([self.cluster_name, self.role_name])

    # have a default name, but can be overridden
    def name(self):
        debug("in launchconfig.py name")
        return self._name

    def set_name(self, name):
        debug("in launchconfig.py set_name")
        self._name = name

    # processes the cloud-init template, returns a string
    def cloud_init_script(self):
        debug("in launchconfig.py cloud_init")
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
        # cluster/role configurable extra cloud-init stuff
        cloud_init_config['cloud_init_extra'] = self.role_config.get('cloud_init_extra') or ''

        cloud_init_config['cluster_name'] = self.cluster_name or ''
        cloud_init_config['role_name'] = self.role_name or ''

        cloud_init = cloud_init_template.substitute(**cloud_init_config)
        return cloud_init

    # does a LC exist with our name?
    def exists(self):
        debug("in launchconfig.py exists")
        lc = self.get_lc()
        if lc:
            return True
        return False

    # we can't modify a launchconfig in place, we have to create
    # a new one. returns new udo.lc
    def update(self):
        debug("in launchconfig.py update")
        if not self.exists():
            # easy, just create it
            print "not exists"
            self.activate()
            return self
        # generate a name for the new lc version
        name = self.get_lc_server_name()
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

    # NOTE: could do more error checking here.  what if for some crazy reason we have similar
    # named launch configs and we return more than 1 answer?
    def get_lc(self):
        debug("in launchconfig.py get_lc")
        conn = util.as_conn()
        _lcs = conn.describe_launch_configurations()['LaunchConfigurations']
        lcs={}
        for lc in _lcs:
            lcs[lc['LaunchConfigurationName']]=lc
        for key, value in lcs.iteritems():
            if key.startswith(self.name()):
                return value
        # if we didnt find a LaunchConfig above by the time we get to here, return None
        return None

    def get_lc_server_name(self):
        return self.get_lc()['LaunchConfigurationName']

    # this could use more error checking to see if the launchconfig delete actually happened
    def deactivate(self):
        debug("in launchconfig.py deactivate")
        if not self.exists():
            return
        lcname = self.get_lc_server_name()
        print "Deleting launchconfig {}...".format(lcname)
        client = util.as_conn()
        response = client.delete_launch_configuration( LaunchConfigurationName = lcname )
        sleep(5) # give aws a chance to delete the launchconfig
        try:
            response = client.describe_launch_configurations( LaunchConfigurationName = lcname )
            util.message_integrations("Failed to delete LaunchConfig {}".format(lcname))
        except:
            util.message_integrations("Deleted LaunchConfig {}".format(lcname))

    # creates the LaunchConfig
    # returns True if LaunchConfig exists
    def activate(self):
        debug("in launchconfig.py activate")
        conn = util.as_conn()
        name = None

        if self.exists():
            debug("in launchconfig.py self.exists()")
            name = self.get_lc_server_name()
            # NOTE: I don't think program logic ever gets here
            if not util.confirm("LaunchConfig {} already exists, overwrite?".format(name)):
                pprint("in launchconfig.py activate: Confirmed overwriting LaunchConfig")
                return True
            # delete existing
            pprint("in launchconfig.py activate: deleting LaunchConfig")
            conn.delete_launch_configuration(LaunchConfigurationName=name)
        else:
            name = self.name()

        # get configuration for this LC
        cfg = self.role_config

        tenancy = cfg.get('tenancy')
        if not tenancy:
            tenancy='default'

        # NOTE: wrap the following in a try block to catch errors
        lc = conn.create_launch_configuration(
            AssociatePublicIpAddress = True, # this is required to make your stuff actually work
            LaunchConfigurationName = name,
            IamInstanceProfile = cfg.get('iam_profile'),
            ImageId = cfg.get('ami'),
            InstanceType = cfg.get('instance_type'),
            KeyName = cfg.get('keypair_name'),
            UserData = self.cloud_init_script(),
            SecurityGroups = cfg.get('security_groups'),
            PlacementTenancy = tenancy,
        )
        #if not conn.create_launch_configuration(lc):
        #    print "Error creating LaunchConfig {}".format(name)
        #    return False
        util.message_integrations("Activated LaunchConfig {}".format(name))
        return lc
