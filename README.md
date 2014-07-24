##Project: *Unemployed DevOps* (UDO)

You have an application you want to deploy into AWS, taking advantage of all of the cool features and services generously provided by Amazon. You have an interest in doing things the Right Way, and not Reinventing The Wheel. You have some modest level of clue.

Have a look at the [sample configuration](config.sample.yml) to get an idea of what Udo
will manage.

## Quickstart:  

#### Step 1: Configure boto with your AWS credentials
* See: http://boto.readthedocs.org/en/latest/boto_config_tut.html#details

#### Step 2: Configure boto
```
# describe our application clusters
cp config.sample.yml config.yml
emacs config.yml   # replace 'emacs' with 'vim' if you are a simple-minded cretin
```

#### Step 3: ... That's it! There's no step 3.
```
# view usage:
$ script/udo
Valid commands are:
  * cluster list - view state of clusters
  * cluster status - view state of a cluster
  * cluster activate - create a VPC
  * lc cloudinit - display cloud-init script
  * lc activate - create a launch configuration
  * lc deactivate - delete a launch configuration
  * asg reload - deactivate and activate an autoscaling group to update the config
  * asg activate - create an autoscaling group
  * asg deactivate - delete an autoscaling group
  * asg updatelc - updates launchconfiguration in-place

# create a VPC from our config by name
$ cluster activate dev webapp

# display our application launchconfig cloud-init script for the dev/webapp role
$ script/udo lc cloudinit dev webapp   

# terminates all instances in the qa-webapp group via scaling policy, deletes ASgroup and LC
$ $ script/udo asg deactivate qa webapp
Deleting... this may take a few minutes...
. . . . . . . . . . . .
Deleted ASgroup qa-webapp
Deleting launchconfig...
Deleted LaunchConfig qa-webapp

# delete and recreate ASgroup, super easy brain-dead way to reprovision a cluster
$ script/udo asg reload prod worker
Are you sure you want to tear down the prod-worker ASgroup and recreate it? (y/n) y
Reloading ASgroup prod-worker
Deleting... this may take a few minutes...
. . . . . . . . . . . . 
Deleted ASgroup prod-worker
Deleting launchconfig...
Deleted LaunchConfig prod-worker
Creating LaunchConfig prod-worker
Activated LaunchConfig prod-worker
Using subnets subnet-cf9a87321, subnet-bfac8123
AZs: ['us-west-2a', 'us-west-2b']
Activated ASgroup prod-worker

# bonus slack notifications (if configured)
20:11 < UdoBot> Reloading ASgroup prod-worker
20:12 < UdoBot> Deleted ASgroup prod-worker
20:12 < UdoBot> Deleted LaunchConfig prod-worker
20:12 < UdoBot> Activated LaunchConfig prod-worker
20:13 < UdoBot> Activated ASgroup prod-worker


# update launchconfig for an existing autoscaling group (bonus feature not provided by AWS or boto)
$ script/udo asg updatelc dev webapp
```


## What's all this then, eh?

### What does Udo do?
Udo is a small collection of useful tools for managing clusters in AWS. It uses the python `boto` library to communicate with the AWS APIs to automate creation of clusters and instances, making full use of VPCs and AutoScaling Groups.  
Udo allows you to define your entire operational structure in a straightforward configuration file, and then use the Udo command-line tool to bring up and manage clusters and groups of instances. It takes the tedious work out of creating nearly identical clusters by hand, and automates actions like creating and managing launconfigurations and autoscaling groups, parallelizing SSH commands by ASgroup (orchestration without the need for any running services), and performing graceful upgrades of instances in an autoscale group without downtime.

### What do _you_ do?
Most development projects utilize several distinct sets of environments, such as dev, qa, stage, production. These clusters are generally partitioned into different roles, such as a web application server, asynchronous worker machine, monitoring and so on.  
If you wish to set this up in AWS, you should script creating environments, provisioning instances based on roles and creating different parameters for each type of instance you want ("dev webapp servers should be of type m3.medium", "production workers should use an autoscaling policy with a minimum of 3 instances", etc..).
You *could* do all of this work yourself, or you could just use Udo.

### What _should_ you do?
EC2 is not a datacenter in ~the cloud~. If you're using it like a traditional managed hosting company, you are probably doing things wrong. You should take advantage of the specialized infrastucture and APIs provided by AWS, like AutoScaling Groups and `boto`.  
If you're making an AMI per role, you may be doing things wrong. You should be able to automatically deploy your entire application onto a virgin Amazon Linux AMI, though making one with some of your app already installed to save time isn't a bad idea.
If you're using Puppet, Chef, or care about hostnames/IPs, you're almost definitely doing things wrong. You aren't maintaining machines that are going to necessairly exist for any length of time, and you should be able to kill off instances at will as well as spawn and fully provision a new instance from scratch without even thinking about it. There's no real reason you should ever need to keep track of an individual instance. 

### Does this work?
I've been using this in production for a decent length of time with minimal trouble. It's been very handy for managing groups of instances without the need for any special services running on them. We mostly use it for turning QA clusters off when not in use, cleanly reprovisioning instances, and updating launchconfigurations in place on production (something you cannot currently do with the AWS GUI or CLI). 
Several Amazon engineers have reviewed Udo and given it their seal of approval. They said many companies have similar internal tools, but they don't open-source them. Hopefully this code will save someone some effort. 


### Summary of a proper AWS setup:

#### Your job:
- Describe your architecture in `config.yml`.
- Have some very simple way of setting up your app. One recommendation is to install your application and configs via RPMs, though this is not required.
- If you use RPMs, stick your RPMs in a private S3 repo and authenticate access via [yum-s3-iam](https://github.com/seporaitis/yum-s3-iam).

#### Udo takes care of:
- LaunchConfigs per role, in a VPC and AutoScaleGroup per cluster.
- Apply tags to instances to identify their roles.
- Bringing clusters up and down and reprovisioning them, using ASgroups to track membership and SSH for orchestration.
- Installing a cloud-init script to provision instances. You can add your own commands to it via config.
- Using RPMs to provision instances (optional)


### TODO:
* Parallel-SSH integration (needs to be merged from another repo)
* Graceful "deploy" command with canary and rolling options


