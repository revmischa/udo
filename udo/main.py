#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse 
import os
import pkg_resources
import random
import sys
import warnings

from pprint import pprint

import asgroup
import config
import deploy
import launchconfig
import util

# top-level commands go here
class Udo:
    # launchconfig
    def lc(self, *args):
        args = list(args)
        if not len(args) >= 2:
            print "launchconfig command requires an action. Valid actions are: "
            print " cloudinit (cluster).(role) - view cloud_init bootstrap script"
            print " create (cluster).(role) - create launch configuration"
            print " destroy (cluster).(role) - delete launch configuration"
            return
        action = args.pop(0)
        target = args.pop(0)

        cluster,role = self.get_cluster_and_role_from_args(target)

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
            print "Unrecognized LaunchConfig action"

    # autoscale
    def asg(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "asgroup command requires an action. Valid actions are: "
            print " instances (cluster).(role) - list instances in group"
            print " randomip (cluster).(role) - get an IP address of a host in the group"
            print " create (cluster).(role) - create an autoscale group"
            print " destroy (cluster).(role) - delete an autoscale group and terminate all instances"
            print " reload (cluster).(role) - destroys asgroup and launchconfig, then recreates them"
            print " updatelc (cluster).(role) - generates a new launchconfig version"
            print " scale (cluster).(role) - view current scaling settings"
            print " scale (cluster).(role) (desired) - set desired number of instances"
            print " policies (cluster).(role) - view current autoscaling policies"
            print " suspend (cluster).(role) - suspend autoscaling for group"
            print " resume (cluster.(role) - resume autoscaling for group"
            return
        # TODO: hook up 'list'

        action = args.pop(0)
        target = args.pop(0)

        cluster, role = self.get_cluster_and_role_from_args(target)
        if not cluster or not role:
            return

        ag = asgroup.AutoscaleGroup(cluster, role)

        if not ag.has_valid_role():
            print "Invalid role {} specified for cluster {}".format(role, cluster)
            return

        if action == 'create':
            ag.activate()
        elif action == 'destroy':
            ag.deactivate()
        elif action == 'reload':
            ag.reload()
        elif action == 'updatelc':
            ag.update_lc()
        elif action == 'instances':
            ag.print_instances()
        elif action == 'randomip':
            ips = ag.ip_addresses()
            print(random.choice(ips))
        elif action == 'scale':
            # get scale arg
            if len(args):
                scale = int(args.pop(0))
                ag.scale(scale)
            else:
                ag.get_scale_size()
        elif action == 'policies':
            ag.policies()
        elif action == 'suspend':
            ag.suspend()
        elif action == 'resume':
            ag.resume()
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
            print " status deploymentId" # only for debugging
            return
        action = args.pop(0)

        if action == 'list':
            dep = deploy.Deploy()
            if not len(args):
                print "list what? applications, groups, deployments, post or configs?"
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
            elif what == 'post':
                dep.list_post_deploy_hooks()
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
            group_name = None
            if len(args) == 1:
                group_name = self.get_deployment_group_name(args.pop(0))
            dep.print_last_deployment(deployment_group_name=group_name)
        elif action == 'status':
            deploymentId = args.pop(0)
            dep = deploy.Deploy()
            print(dep.deployment_status(deploymentId))
        elif action == 'stop':
            dep = deploy.Deploy()
            group_name = None
            if len(args) == 1:
                group_name = self.get_deployment_group_name(args.pop(0))
            dep.stop_deployment(deployment_group_name=group_name)
        elif len(args) == 1:
            # assume we want to create a deployment
            group_name = self.get_deployment_group_name(action)
            commit_id = args.pop(0)
            dep = deploy.Deploy()
            dep.create(group_name, commit_id)
        else:
            print "Unknown deploy command: {}".format(action)

    # takes either a deploymentgroup name or a cluster.role name and returns deploymentgroup name
    def get_deployment_group_name(self, group_arg):
        group_name = group_arg  # default to using arg as deploymentgroup name

        # check to see if group_arg is a valid deploymentegroup name or valid cluster/role
        dep = deploy.Deploy()
        groups = dep.get_groups()
        group_names = groups['deploymentGroups']
        if group_name not in group_names: # not valid deployment group name
            # look in config for group name from cluster/role
            cluster,role = self.get_cluster_and_role_from_args(group_arg, quiet=True)
            if role:
                cfg = config.get_role_config(cluster, role)
                group_name = cfg.get('deployment_group')
                if not group_name:
                    print("Failed to find DeploymentGroup name in configuration for role {}".format(role))
                    return None
            else:
                print("Invalid DeploymentGroup name '{}' and no deployment_group is configured for this role.".format(group_arg))
                return None
        return group_name

    def version(self, *args):
        args = list(args)
        try:
            print(pkg_resources.get_distribution('udo').version)
        except:
            print("udo not installed from PyPi")

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

    # returns cluster_name,role_name
    def get_cluster_and_role_from_args(self, arg, quiet=False):
        def fale(msg):
            if not quiet:
                print(msg)
            return None,None

        # need cluster/role
        if not arg:
            return fale("Please specify cluster.role target for this command")
        cluster_role = arg

        help = "Please specify the target of your action using the format: cluster.role"

        cluster_name = None
        role_name = None
        if '.' in cluster_role:
            # split on .
            cluster_name, role_name = cluster_role.split(".")
            if not cluster_name:
                return fale("Cluster name not specified.", help)
            if not role_name:
                return fale("Role name not specified.", help)
        else:
            # assume we're just talking about a cluster with one role
            cluster_name = cluster_role

        cluster = config.get_cluster_config(cluster_name)
        if not cluster:
            return fale("Unknown cluster {}".format(cluster_name))

        roles = cluster.get('roles')
        if not roles:
            return fale("Invalid configuration for {}: no roles are defined".format(cluster_name))

        if not role_name:
            role_names = roles.keys()
            if len(role_names) == 1:
                # assume the only role
                print("No role specified, assuming {}".format(role_names[0]))
                role_name = role_names[0]
            else:
                err = "Multiple roles available for cluster {}".format(cluster_name)
                for r in role_names:
                    err = err + "\n  - {}".format(r)
                return fale(err)

        if not role_name in roles:
            return fale("Role {} not found in cluster {} configuration".format(role_name, cluster_name))

        return cluster_name, role_name

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
  * lc cloudinit - display cloud-init script
  * lc create - create a launch configuration
  * lc destroy - delete a launch configuration
  * asg instances - print instances in autoscaling groups
  * asg reload - destroy and create an autoscaling group to update the config
  * asg create - create an autoscaling group
  * asg destroy - delete an autoscaling group
  * asg updatelc - updates launchconfiguration in-place
  * asg scale - set desired number of instances
  * asg randomip - print IP address of random host in group
  * asg policies - print autoscaling policies for group
  * asg suspend - suspend autoscaling for group
  * asg resume - resume autoscaling for group
  * deploy list apps - view CodeDeploy applications
  * deploy list groups - view CodeDeploy application deployment groups
  * deploy list deployments - view CodeDeploy deployment statuses
  * deploy list configs - view CodeDeploy configurations
  * deploy list post - view post deploy hooks
  * deploy [create] (group) (commit) - create new deployment for commit on group
  * deploy last - shows status of most recent deployment
  * deploy stop - cancel last deployment
  * version - print udo version
        """
        sys.exit(1)

    # execute cmd
    exe = Udo()
    method = getattr(exe, args.cmd)
    method(*args.cmd_args)

if __name__ == '__main__':
    invoke_console()
