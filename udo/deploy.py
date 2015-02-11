# create_deployment(application_name, deployment_group_name=None, 
# revision=None, deployment_config_name=None, description=None, 
# ignore_application_stop_failures=None)

import config
import util
import boto
from datetime import datetime
from boto.codedeploy.layer1 import CodeDeployConnection

_cfg = config.Config()

class Deploy:
    # role_name is totally optional
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

    def commit_id_display(self, commit_id):
        return commit_id[:10]

    def get_deploy_config(self):
        if not self.cfg:
            return None
        return self.cfg.get('deploy')

    # create a deployment
    def create(self, commit_id):
        cfg = self.get_deploy_config()
        if not cfg:
            print "deploy configuration not found"
            return
        if not 'group' in cfg:
            print "deployment group not specified in deployment configuration"
            print "deployment configuration:"
            print cfg
            return
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

        group_name = cfg['group']
        application_name = cfg['application']
        deploy_rev = {
            'revisionType': 'GitHub',
            'gitHubLocation': {
                'repository': repo_name,
                'commitId': commit_id,
            }
        }
        msg = "Deploying commit {} to deployment group: {}".format(self.commit_id_display(commit_id), group_name)
        deployment = self.conn.create_deployment(application_name,
            deployment_group_name=group_name,
            revision=deploy_rev,
            ignore_application_stop_failures=False,
        )
        if not deployment:
            # prob won't reach here, will throw error instead
            print "Deployment failed"
            return
        deployment_id = deployment['deploymentId']
        util.message_integrations(msg)
        self.list_deployments(deployment_id)

    def list_deployments(self, dep_id=None):
        deps = self.conn.list_deployments()
        if dep_id:
            self.print_deployment(dep_id)
        else:
            for dep_id in deps['deployments']:
                self.print_deployment(dep_id)

    def print_last_deployment(self):
        deps = self.conn.list_deployments()['deployments']
        if not len(deps):
            print "No deployments found"
            return
        self.print_deployment(deps[0])

    def print_deployment(self, dep_id):
        dep = self.conn.get_deployment(dep_id)
        info = dep['deploymentInfo']
        dep_id = info['deploymentId']
        app_name = info['applicationName']
        group_name = info['deploymentGroupName']
        status = info['status']
        rev_info = info['revision']
        create_time = datetime.fromtimestamp(info['createTime'])
        create_time_display = create_time.strftime("%A, %d. %B %Y %I:%M%p")
        commit_id = 'unknown'
        #print dep
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
        apps = self.conn.list_applications()
        # TODO: fetch more apps via next_token if available
        app_names = apps['applications']
        for name in app_names:
            print " - Application: {}".format(name)

    def list_groups(self, application=None):
        cfg = self.get_deploy_config()
        if not application and cfg and 'application' in cfg:
            application = cfg['application']
        if not application:
            print "Deployment application not specified or configured"
            print "Valid applications are:"
            self.list_applications()
            return
        groups = self.conn.list_deployment_groups(application)
        # TODO: fetch more groups via next_token if available
        group_names = groups['deploymentGroups']
        for name in group_names:
            print " - Group: {}/{}".format(application, name)

    def list_configs(self):
        cfgs = self.conn.list_deployment_configs()
        # TODO: fetch more cfgs via next_token if available
        cfg_names = cfgs['deploymentConfigsList']
        for name in cfg_names:
            print " - Configuration: {}".format(name)

