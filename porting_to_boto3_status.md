still needs work:

asgroup create ( need to test when availability zone is set, test when more than one subnet_id is defined,
  test when more than one availability zone is set )

cluster create

deploy stop # probably works, I just havent bothered testing

asg updatelc  # doesnt work at all.  dict error

util retry function in util is based on boto, not boto3, commented out

util 'wait' function in util could be better.  it also may not be used.

there might redundant calls to get name

make sure vpc creating in cluster.py works. im not confident the vpc creating stuff works.

Nice to have:

We should remove 'cluster'.  it has not proven to be very useful.  

we should use the token/next token stuff, in case we are managing large amounts of resources

sometimes we use applicationName , application_name , application .  should standardize
same deal with groupName, group_name, deployment_group_name

should hide output of the post_build_steps , only output it if DEBUG is set
add labels for the post_build steps , that can be outputted later

make sure the wget doesn't leave files around 

should have udo deploy, then block until a deployment status is failed or not failed
