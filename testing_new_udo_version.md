## testing new udo version

#### change dir to root of your repo ( same dir as udo.yml )

#### uninstall systemwide udo, if its installed
    sudo pip uninstall udo

#### make a new virtualenv ( not as root )
    virtualenv venv

#### activate the virtualenv
    source venv/bin/activate

#### install latest pip
    pip install pip --upgrade

#### remove previous version of udo in the virtualenv ( this might not be needed )
    pip uninstall udo

#### install udo from master branch of my fork
    pip install https://github.com/danhdb/udo/archive/master.zip

#### install new pypy requirments
    pip install boto3==1.1.1 \
        botocore==1.1.7 \
        docutils==0.12 \
        futures==2.2.0 \
        jmespath==0.7.1 \
        python-dateutil==2.4.2 \
        PyYAML==3.11 \
        six==1.9.0 \
        wheel==0.24.0

#### test
    $ udo asg policies stage.worker 
    $ udo asg suspend stage.worker
    $ udo asg resume stage.worker 
