### TODO
* Parallel-SSH integration (needs to be merged from another repo)

* CodeDeploy support from S3

* getting role and cluster name in create deploy in deploy.py, to pass to asgroup.py , is pretty dumb, uses regexp.  there
must be a better way.

* for each ASG in a CodeDeploy group, we suspend autoscaling processes before a CodeDeploy deploy.  After a successful or failed CodeDeploy deploy, we resume autoscaling processes in each ASG.  I should make suspend/resume autoscaling processes before a deploy be an option you can turn on/off.  I should make the 'resume' be a lifecycle hook that will eventually occur after a deploy, instead of doing it manually in udo.

* sometimes CodeDeploy gets stuck because there is an old deploy still going on. We should provide a way to list the stuck deployment and kill it

* README.md is out of date
