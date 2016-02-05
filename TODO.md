### TODO
* Parallel-SSH integration (needs to be merged from another repo)
* CodeDeploy support from S3
* For all ASG in a CodeDeploy group, suspend all autoscaling processes before a CodeDeploy deploy (if there are autoscaling rules in the ASG).  After deploy is done, resume autoscaling processes in the ASG.  I added suspend and resume, I wasn't able to successfully suspend before a CodeDeploy deploy.  Working on it.
