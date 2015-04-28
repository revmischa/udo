#!/usr/bin/env python

import sys
import warnings
import os
import argparse
from pprint import pprint

import cluster
import launchconfig
import util
import asgroup
import config
import deploy

#####


# top-level commands go here
class Udo:
    def cluster(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "cluster command requires an action. Valid actions are: "
            print " list\n status"
            return
        action = args.pop(0)

        if action == 'list':
            cluster.list()
        else:
            # actions that require a cluster name
            if not len(args) or not args[0]:
                print "cluster name required for {}".format(action)
                return
            cluster_name = args.pop(0)
            cl = cluster.Cluster(cluster_name)
            if action == 'status':
                print "{} status: {}".format(cluster_name, cl.status())
            elif action == 'create':
                if not cl.create():
                    print "Failed to bring up {} cluster".format(cluster_name)
            else:
                print "Unknown cluster command: {}".format(action)


    # launchconfig
    def lc(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "launchconfig command requires an action. Valid actions are: "
            print " cloudinit (cluster) (role) - view cloud_init bootstrap script"
            print " create (cluster) (role) - create launch configuration"
            print " destroy (cluster) (role) - delete launch configuration"
            return
        action = args.pop(0)

        cluster,role = self.get_cluster_and_role_from_args(*args)
        if not cluster or not role:
            return

        lc = launchconfig.LaunchConfig(cluster, role)

        if action == 'cloudinit':
            cloudinit = lc.cloud_init_script()
            print cloudinit
        elif action == 'create':
            lc.activate()
        elif action == 'destroy':
            lc.deactivate()
        else:
            print "Unrecognized launchconfig action"


    # autoscale
    def asg(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "asgroup command requires an action. Valid actions are: "
            print " create (cluster) (role) - create an autoscale group"
            print " destroy (cluster) (role) - delete an autoscale group and terminate all instances"
            print " reload (cluster) (role) - destroys asgroup and launchconfig, then recreates them"
            print " updatelc (cluster) (role) - generates a new launchconfig version"
            print " scale (cluster) (role) - view current scaling settings"
            print " scale (cluster) (role) (desired) - set desired number of instances"
            return
        action = args.pop(0)

        # TODO: hook up 'list'

        cluster,role,extra = self.get_cluster_and_role_from_args(*args)
        if not cluster or not role:
            return

        ag = asgroup.AutoscaleGroup(cluster, role)

        if action == 'create':
            ag.activate()
        elif action == 'destroy':
            ag.deactivate()
        elif action == 'reload':
            ag.reload()
        elif action == 'updatelc':
            ag.update_lc()
        elif action == 'scale':
            # get scale arg
            if extra:
                scale = int(extra)
                ag.scale(scale)
            else:
                ag.get_scale_size()
        else:
            print "Unrecognized asgroup action {}".format(action)


    # CodeDeploy
    def deploy(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "deploy command requires an action. Valid actions are: "
            print " list applications"
            print " list groups [application]"
            print " list deployments"
            print " list configs"
            print " create (group) (commit_id)"
            print " last [group]"
            return
        action = args.pop(0)

        if action == 'list':
            dep = deploy.Deploy()
            if not len(args):
                print "list what? applications, groups, deployments or configs?"
                return
            what = args.pop(0)
            if what == 'applications' or what == 'apps':
                dep.list_applications()
            elif what == 'groups':
                # application name?
                application = None
                if len(args):
                    application = args.pop(0)
                dep.list_groups(application)
            elif what == 'configs':
                dep.list_configs()
            elif what == 'deployments':
                dep.list_deployments()
            else:
                print "Unknown list type: {}".format(what)
        elif action == 'create':
            # require group, commit_id
            if len(args) != 2:
                print "deploy create requires group and commit id"
                return

            group = args.pop(0)
            commit_id = args.pop(0)
            dep = deploy.Deploy()
            dep.create(group, commit_id)
        elif action == 'last':
            dep = deploy.Deploy()
            group = None
            if len(args) == 1:
                group = args.pop(0)
                dep.print_last_deployment(deployment_group_name=group)
            else:
                dep.print_last_deployment()
        elif action == 'stop':
            dep = deploy.Deploy()
            dep.stop_deployment()
        elif len(args) == 1:
            # let's just assume we wanna create a deployment
            group = action
            commit_id = args.pop(0)
            dep = deploy.Deploy()
            dep.create(group, commit_id)
        else:
            print "Unknown deploy command: {}".format(action)


    # for testing features
    def test(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "test command requires an action. Valid actions are: "
            print " integrations"
            return
        action = args.pop(0)

        if action == 'integrations':
            util.message_integrations("Testing Udo integrations")
        else:
            print "Unknown test command: {}".format(action)

    def get_cluster_and_role_from_args(self, *args):
        args = list(args)

        # need cluster/role
        if len(args) < 1:
            print "Please specify cluster name for this command"
            return None,None
        cluster = args.pop(0)

        # use role name if specified, otherwise assume they meant the obvious thing
        # if there's only one role
        if len(args):
            role = args.pop(0)
        else:
            roles = config.get_cluster_config(cluster).get('roles')
            if not roles:
                print "Cluster config for {} not found".format(cluster)
                return None,None

            rolenames = roles.keys()
            if len(rolenames) == 1:
                # assume the only role
                print "No role specified, assuming {}".format(rolenames[0])
                role = rolenames[0]
            else:
                print "Multiple roles available for cluster {}".format(cluster)
                for r in rolenames:
                    print "  - {}".format(r)
                return None,None

        # still stuff?
        extra = None
        if len(args):
            extra = args.pop(0)

        return cluster, role, extra
#####


def invoke_console():
    # argument parsing
    parser = argparse.ArgumentParser(description='Manage AWS clusters.')
    parser.add_argument('cmd', metavar='command', type=str, nargs='?',
                       help='Action to perform. Valid actions: status.')
    parser.add_argument('cmd_args', metavar='args', type=str, nargs='*',
                       help='Additional arguments for command.')
    args = parser.parse_args()
    
    if args.cmd not in dir(Udo):
        if args.cmd:
            print "'{}' is not a valid command".format(args.cmd)
        else:
            print "You must specify a command"
        # full command summary
        print """
Valid commands are:
  * cluster list - view state of clusters
  * cluster status - view state of a cluster
  * cluster create - create a VPC
  * lc cloudinit - display cloud-init script
  * lc create - create a launch configuration
  * lc destroy - delete a launch configuration
  * asg reload - destroy and create an autoscaling group to update the config
  * asg create - create an autoscaling group
  * asg destroy - delete an autoscaling group
  * asg updatelc - updates launchconfiguration in-place
  * asg scale - set desired number of instances
  * deploy list apps - view CodeDeploy applications
  * deploy list groups - view CodeDeploy application deployment groups
  * deploy list deployments - view CodeDeploy deployment statuses
  * deploy list configs - view CodeDeploy configurations
  * deploy create (group) (commit) - create new deployment for commit on group
  * deploy last - shows status of most recent deployment
  * deploy stop - cancel last deployment
        """
        sys.exit(1)

    # execute cmd
    exe = Udo()
    method = getattr(exe, args.cmd)
    method(*args.cmd_args)



if __name__ == '__main__':
    invoke_console()
