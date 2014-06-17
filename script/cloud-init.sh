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

# install updates

yum update -y

# your stuff from cloud_init config
@cloud_init_extra

## install packages
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
