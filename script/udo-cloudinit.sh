#!/bin/bash

# Initialize a base system, provision via RPM installation
# Read by LaunchConfig

# Our stuff goes in here
BOOTSTRAP_DIR=/root/.udo
mkdir -p $BOOTSTRAP_DIR

# set up Yum S3 IAM plugin
curl @yum_plugin_url \
    > $BOOTSTRAP_DIR/yum-plugin-s3-iam.noarch.rpm
rpm -i $BOOTSTRAP_DIR/yum-plugin-s3-iam.noarch.rpm

# add our app yum repo
curl @repo_url > /etc/yum.repos.d/@{app_name}.repo

# load up repo metadata
yum makecache

# install updates
yum update -y

# base system
if [[ -n "@base_packages" ]]; then
	yum install -y @base_packages
fi

# role packages
if [[ -n "@role_packages" ]]; then
	yum install -y @role_packages
fi

# might not be a bad idea to reboot after updating everything?
#/sbin/reboot now
