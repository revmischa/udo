"""
create_deployment(application_name, deployment_group_name=None, 
revision=None, deployment_config_name=None, description=None, 
ignore_application_stop_failures=None)
"""

import boto3
import subprocess
import re
import sys

from datetime import datetime
from dateutil.parser import parse
from pprint import pprint

import asgroup
import config
import util

from time import sleep
from util import debug

_suspend_on_deploy = False

_cfg = config.Config()

class Deploy:
    """Handles deployment via AWS CodeDeploy service. Creates/views/stops deployments."""
    # role_name is optional
    # cluster_name is kinda optional
    def __init__(self, cluster_name=None, role_name=None):
        if cluster_name:
            self.cluster_name = cluster_name
            if role_name:
                self.role_name = role_name
                self.cfg = config.get_role_config(cluster_name, role_name)
            else:
                self.cfg = config.get_cluster_config(cluster_name)
        else:
            self.cfg = _cfg.get_root()
        self.conn = util.deploy_conn()

    def config(self):
        debug("in deploy.py config")
        return self.cfg.get('deploy')

    def app_name(self):
        debug("in deploy.py app_name")
        application = self.config().get('application')
        if not application:
            print "Deployment application not specified or configured"
            print "Valid applications are:"
            self.list_applications()
            return
        return application

    def commit_id_display(self, commit_id):
        debug("in deploy.py commit_id")
        return commit_id[:10]

    # create a deployment
    def create(self, group_name, commit_id):
        debug("in deploy.py create")
        cfg = self.config()

        if not 'application' in cfg:
            print "deployment application not specified in deployment configuration"
            self.list_applications()
            return

        # get source info
        # assume github for now
        repo_name = None
        source = None
        rev_type = 'github'
        if not 'github' in cfg:
            print "github info not specified in deployment configuration"
            return
        source = cfg['github']
        if not 'repo' in source:
            print "deployment github repository not specified in deployment configuration"
            return
        repo_name = source['repo']

        application_name = cfg['application']

        msg = "Deploying commit {} to deployment group: {}".format(self.commit_id_display(commit_id), group_name)

        deployment_asg_info = self.conn.get_deployment_group(applicationName=application_name,
                    deploymentGroupName=group_name)['deploymentGroupInfo']['autoScalingGroups']

        # NOTE: There is probably a better way of getting role_name and cluster_name
        # This depends on role_name and cluster_name being seperated with a "."
        # This works but I don't like it
        def asg_autoscaling_control(action):
            # This will suspend or resume every the autoscaling processes in every ASG that is
            # part of the CodeDeploy group
            for asg_info in deployment_asg_info:
                _asg = (asg_info['name'])
                cluster_name = re.search(r'^(.*?)-', _asg).group(1)
                role_name = _asg.split(cluster_name + '-')[1]
                asg = asgroup.AutoscaleGroup(cluster_name, role_name)
                if action == 'suspend':
                    asg.suspend()
                elif action == 'resume':
                    asg.resume()

        if _suspend_on_deploy:
            asg_autoscaling_control('suspend')

        deployment = self.conn.create_deployment(applicationName=application_name,
            deploymentGroupName=group_name,
            revision={ 'revisionType': 'GitHub',
                       'gitHubLocation': {
                           'repository': repo_name,
                           'commitId' : commit_id
                           }
                   },
            # deploymentConfigName = string,
            ignoreApplicationStopFailures = False,
            )
        if not deployment:
            # prob won't reach here, will throw error instead
            print "Deployment failed"
            return
        deployment_id = deployment['deploymentId']
        debug("in deploy.py create: deploymentId: " + deployment_id)
        
        util.message_integrations(msg, icon=':ship:')

        debug("in deploy.py create: deploymentId: " + deployment_id)

        pprint("Waiting for deployment...")
        try:
            sleep(5)
        except KeyboardInterrupt:
            return

        interval = 5
        tries = 60
        # deployment_status[status] will be:
        # 'Created'|'Queued'|'InProgress'|'Succeeded'|'Failed'|'Stopped',
        #
        # what you see in AWS dashboard is usually what the current state actually is.
        # info you grab from the API appears to be slightly delayed
        #
        for x in range(0, tries):
            try:
            # should get status here, then check for it, instead of in the loop
                status = self.deployment_status(deployment_id)['status']
                if status == 'Succeeded':
                    _msg = 'Deployment of commit ' + commit_id + ' to deployment group: ' + group_name + ' successful.'
                    util.message_integrations(_msg, icon=':ship:')
                    if _suspend_on_deploy:
                        asg_autoscaling_control('resume')
                    # define actions in post_deploy_hooks in udo.yml
                    post_deploy_hooks = self.get_post_deploy_hooks(application_name, group_name)
                    if post_deploy_hooks:
                        for post_deploy_hook in post_deploy_hooks:
                            print("running: " + post_deploy_hook)
                            try:
                                command = subprocess.Popen(post_deploy_hook.split())
                            except OSError as e:
                                print e
                                pass
                            except ValueError as e:
                                print e    
                                pass
                            except:
                                pass
                    break
                elif status == 'Failed':
                    if _suspend_on_deploy:
                        asg_autoscaling_control('resume')
                    _msg = "FAILURE to deploy commit ' + commid_id + ' to deployment group: ' + group_name"
                    break
                elif status == 'Created':
                    raise ValueError("deployment has been created... nothing has happened yet")
                elif status == 'Queued':
                    raise ValueError("deployment is Queued")
                elif status == 'InProgress':
                    print("."),
                    sys.stdout.flush()
                elif status == 'Stopped':
                    _msg = 'deployment to deployment group' + group_name + ' is stopped'
                    util.message_integrations(_msg, icon=':ship:')
                else:
                    pprint("An unknown condition has occured")
                    pprint("status: " + str(status))
                    sys.exit(1)
            except KeyboardInterrupt:
                break
            except ValueError as e:
                pprint(e)
                pass

            try:
                sleep(interval)
            except KeyboardInterrupt:
                break

    def list_deployments(self, dep_id=None, group=None):
        debug("in deploy.py list_deployments")
        application_name = self.app_name()
        groups = self.conn.list_deployment_groups(applicationName=application_name)['deploymentGroups']
        _length = len(groups)
        for group in groups:
            pprint("group: " + str(group))
            pprint("application_name: " + application_name)
            if _length > 1:
                print("")
            _length = _length - 1

    def print_last_deployment(self, **kwargs):
        debug("in deploy.py print_last_deployment")
        application_name = self.app_name()
        group_name = None
        if not kwargs:
            print("No deployment group specified.  Listing info for all of them.")
            deployment_groups = self.conn.list_deployment_groups(applicationName=application_name)['deploymentGroups']
            for deployment_group in deployment_groups:
                last_dep = self.get_last_deployment(deployment_group)
                if not last_dep:
                    continue
                self.print_deployment(last_dep)
        elif 'deployment_group_name' in kwargs:
            # list a specific group?
            dep = self.get_last_deployment(kwargs['deployment_group_name'])
            self.print_deployment(dep)
        else:
            raise ValueError("unknown kwargs for print_last_deployment")

    def stop_deployment(self, deployment_group_name=None):
        debug("in deploy.py stop_deployment")
        last_dep_id = self.get_last_deployment(deployment_group_name=deployment_group_name)
        self.conn.stop_deployment(deploymentId=last_dep_id)
        print "Stopped {}".format(last_dep_id)
        self.print_deployment(last_dep_id)

    def get_last_deployment(self, deployment_group_name=None):
        if not deployment_group_name:
            # just get last
            deps = self.conn.list_deployments()['deployments']
            if not len(deps):
                return None
            last_dep_id = deps[0]
            return last_dep_id

        deps = self.conn.list_deployments(applicationName=self.app_name(), deploymentGroupName=deployment_group_name)['deployments']
        if not deps:
            return None
        last_deployment = deps[0]
        return last_deployment

    def print_deployment(self, dep_id):
        debug("in deploy.py print_deployment")
        dep = self.conn.get_deployment(deploymentId=dep_id)
        info = dep['deploymentInfo']
        dep_id = info['deploymentId']
        app_name = info['applicationName']
        group_name = info['deploymentGroupName']
        status = info['status']
        rev_info = info['revision']
        createTime = info['createTime']
        create_time_display = createTime.strftime("%A, %d %B %Y %I:%M%p")
        commit_id = 'unknown'
        msg = ""
        if 'errorInformation' in info:
            error_info = info['errorInformation']
            msg = error_info['message']
        # else get status...?

        if 'gitHubLocation' in rev_info:
            commit_id = self.commit_id_display(rev_info['gitHubLocation']['commitId'])
        print """ - {}/{} [{}]
     Created: {}
     Status: {}
     Message: {}
     Commit: {}
""".format(app_name, group_name, dep_id, create_time_display, status,
        msg, commit_id)

    def list_applications(self):
        debug("in deploy.py list_applications")
        apps = self.conn.list_applications()
        # TODO: fetch more apps via next_token if available
        app_names = apps['applications']
        for name in app_names:
            print " - Application: {}".format(name)

    def list_deployment_group_info(self, application, group_name):
        if not application:
            application = self.app_name()
        group = self.conn.get_deployment_group(applicationName=application, deploymentGroupName=group_name)
        info = group['deploymentGroupInfo']
        style = info['deploymentConfigName']
        print " - Group: {}/{}  \t\t[{}]".format(application, group_name, style)
        # print target revision info
        if 'targetRevision' in info:
            target_rev = info['targetRevision']
            rev_type = target_rev['revisionType']
            if rev_type and rev_type == 'GitHub':
                github_loc = target_rev['gitHubLocation']
                print "      Repository: {}".format(github_loc['repository'])
                if 'commitId' in github_loc:
                    print "      Last commit ID: {}".format(github_loc['commitId'])
        print ""

    def list_groups(self, application=None):
        debug("in deploy.py list_groups")
        groups = self.get_groups(application)
        group_names = groups['deploymentGroups']
        for name in group_names:
            self.list_deployment_group_info(application, name)

    def get_groups(self, application=None):
        if not application:
            application = self.app_name()
        # TODO: fetch more groups via next_token if available
        groups = self.conn.list_deployment_groups(applicationName=application)
        return groups

    def list_configs(self):
        debug("in deploy.py list_configs")
        cfgs = self.conn.list_deployment_configs()
        # TODO: fetch more cfgs via next_token if available
        cfg_names = cfgs['deploymentConfigsList']
        for name in cfg_names:
            print " - Configuration: {}".format(name)

    def deployment_status(self, deploymentId):
        debug("in deploy.py deployment_status")
        conn = util.deploy_conn()
        deploymentInfo = conn.get_deployment( deploymentId = deploymentId )['deploymentInfo']
        deploymentOverview=deploymentInfo['deploymentOverview']
        # status will be one of the following: 'Created'|'Queued'|'InProgress'|'Succeeded'|'Failed'|'Stopped'
        status=deploymentInfo['status']
        ret = {}
        ret['status'] = status
        ret['overview'] = deploymentOverview
        return(ret)

    # A CodeDeploy deployment group will have 1 or more Auto Scaling Groups defined, which you can get from the AWS api.
    #
    # The udo user will define a post_deploy_hook under cluster:role:post_deploy_hook
    def get_post_deploy_hooks(self, application, deploymentGroup):
        asgs_info = self.conn.get_deployment_group(applicationName=application, deploymentGroupName=deploymentGroup)['deploymentGroupInfo']['autoScalingGroups']
        for asg_info in asgs_info:
            asg_name = asg_info['name']
            p = re.compile('[a-z]+')
            cluster = p.match(asg_name).group(0)
            role = asg_name[len(cluster) + 1:]

            role_info = _cfg.get('clusters', cluster)['roles'][role]
            if 'post_deploy_hook' in role_info.keys():
                return(role_info['post_deploy_hook'])
        return None

    def list_post_deploy_hooks(self, application=None):
        debug("in deploy.py list_deploy_hooks")
        application = self.app_name()
        deploymentGroups = self.conn.list_deployment_groups(applicationName=application)['deploymentGroups']
        deploymentGroup_asg_info = {}
        for deploymentGroup in deploymentGroups:
            print('deploymentGroup: ' + deploymentGroup)
            post_deploy_hooks = self.get_post_deploy_hooks(application, deploymentGroup)
            if post_deploy_hooks:
                print(str(post_deploy_hooks))
            else:
                print("No post deploy hooks defined.")
