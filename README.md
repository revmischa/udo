Project: *Unemployed DevOps*
===

You have an application you want to deploy into AWS, taking advantage of all of the cool features and services generously provided by Amazon. You have an interest in doing things the Right Way, and not Reinventing The Wheel. You have some modest level of clue.


## Quickstart:  

#### Configure boto with your AWS credentials
See: http://boto.readthedocs.org/en/latest/boto_config_tut.html#details

```
# describe our application clusters
cp config.sample.yml config.yml
emacs config.yml   # replace 'emacs' with 'vim' if you are a simple-minded cretin

# view cluster status
script/udo cluster list

# display our application launchconfig cloud-init script for the dev/webapp role
script/udo lc cloudinit dev webapp   

# ... more coming
```


## What's all this then, eh?

### What does Udo do?
Udo is a small collection of useful tools for managing clusters in AWS. It uses the python `boto` library to communicate with the AWS APIs to automate creation of clusters and instances, making full use of VPCs and AutoScaling Groups.  
Udo allows you to define your entire operational structure in a straightforward configuration file, and then use command-line tools to bring up clusters and groups of instances.

### What do _you_ do?
Most development projects utilize several distinct sets of environments, such as dev, qa, stage, production. These clusters are generally partitioned into different roles, such as a web application server, asynchronous worker machine, monitoring.  
If you wish to set this up in AWS, you should script creating environments, provisioning instances based on roles and creating different parameters for each type of instance you want ("dev webapp servers should be of type m3.medium", "production workers should use an autoscaling policy with a minimum of 3 instances", etc..).
You *could* do all of this work yourself, or you could just use Udo.

### What _should_ you do?
EC2 is not a datacenter in the cloud. If you're using it like a traditional managed hosting company, you are probably doing things wrong. You should take advantage of the specialized infrastucture and APIs provided by AWS, like AutoScaling Groups and `boto`.  
If you're making an AMI per role, you may be doing things wrong. You should be able to automatically deploy your entire application onto a virgin Amazon Linux AMI, though making one with some of your app already installed to save time isn't a bad idea.
If you're using Puppet, Chef, or care about hostnames/IPs, you're almost definitely doing things wrong. You aren't maintaining machines that are going to necessairly exist for any length of time, and you should be able to kill off instances at will as well as spawn and fully provision a new instance from scratch without even thinking about it. There's no real reason you should ever need to keep track of an individual instance.

### Summary of a proper AWS setup:
#### Your job:
- Describe your architecture in `config.yml`
- Install your application and configs via RPMs
- Stick your RPMs in a private S3 repo, authenticate access via [yum-s3-iam](https://github.com/seporaitis/yum-s3-iam)
#### Udo takes care of:
- LaunchConfigs per role, in a VPC and AutoScaleGroup per cluster
- Apply tags to instances per role, so they can know what RPMs to install
- Use a cloud-init script to provision instances via RPMs
