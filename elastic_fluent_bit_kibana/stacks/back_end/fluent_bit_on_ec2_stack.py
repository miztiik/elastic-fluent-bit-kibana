from aws_cdk import aws_ec2 as _ec2
from aws_cdk import aws_iam as _iam
from aws_cdk import aws_ssm as _ssm
from aws_cdk import core

from elastic_fluent_bit_kibana.constructs.create_ssm_run_command_document_construct import CreateSsmRunCommandDocument


class GlobalArgs:
    """
    Helper to define global statics
    """

    OWNER = "MystiqueAutomation"
    ENVIRONMENT = "production"
    REPO_NAME = "elastic-fluent-bit-kibana"
    SOURCE_INFO = f"https://github.com/miztiik/{REPO_NAME}"
    VERSION = "2020_11_22"
    MIZTIIK_SUPPORT_EMAIL = ["mystique@example.com", ]


class FluentBitOnEc2Stack(core.Stack):

    def __init__(
        self,
        scope: core.Construct, id: str,
        vpc,
        ec2_instance_type: str,
        es_endpoint_param_name: str,
        es_region_param_name: str,
        stack_log_level: str,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Read BootStrap Script):
        try:
            with open("elastic_fluent_bit_kibana/stacks/back_end/bootstrap_scripts/deploy_app.sh",
                      encoding="utf-8",
                      mode="r"
                      ) as f:
                user_data = f.read()
        except OSError as e:
            print("Unable to read UserData script")
            raise e

        # Get the latest AMI from AWS SSM
        linux_ami = _ec2.AmazonLinuxImage(
            generation=_ec2.AmazonLinuxGeneration.AMAZON_LINUX_2)

        # Get the latest ami
        amzn_linux_ami = _ec2.MachineImage.latest_amazon_linux(
            generation=_ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
        )
        # ec2 Instance Role
        _instance_role = _iam.Role(
            self,
            "webAppClientRole",
            assumed_by=_iam.ServicePrincipal(
                "ec2.amazonaws.com"),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                )
            ]
        )

        # Allow CW Agent to create Logs
        _instance_role.add_to_policy(_iam.PolicyStatement(
            actions=[
                "logs:Create*",
                "logs:PutLogEvents"
            ],
            resources=["arn:aws:logs:*:*:*"]
        ))

        # Allow Access to ElasticSearch Domain
        # https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/es-ac.html#es-ac-types-resource
        _instance_role.add_to_policy(_iam.PolicyStatement(
            actions=[
                "es:Describe*",
                "es:List*",
                "es:ESHttpPost",
                "es:ESHttpPut",
            ],
            resources=["*"]
        ))

        # fluent_bit_server Instance
        self.fluent_bit_server = _ec2.Instance(
            self,
            "fluentBitLogRouter",
            instance_type=_ec2.InstanceType(
                instance_type_identifier=f"{ec2_instance_type}"),
            instance_name="fluent_bit_log_router_01",
            machine_image=amzn_linux_ami,
            vpc=vpc,
            vpc_subnets=_ec2.SubnetSelection(
                subnet_type=_ec2.SubnetType.PUBLIC
            ),
            role=_instance_role,
            user_data=_ec2.UserData.custom(
                user_data)
        )

        # Allow Web Traffic to WebServer
        self.fluent_bit_server.connections.allow_from_any_ipv4(
            _ec2.Port.tcp(80),
            description="Allow Incoming HTTP Traffic"
        )

        self.fluent_bit_server.connections.allow_from(
            other=_ec2.Peer.ipv4(vpc.vpc_cidr_block),
            port_range=_ec2.Port.tcp(443),
            description="Allow Incoming FluentBit Traffic"
        )

        # Allow CW Agent to create Logs
        _instance_role.add_to_policy(_iam.PolicyStatement(
            actions=[
                "logs:Create*",
                "logs:PutLogEvents"
            ],
            resources=["arn:aws:logs:*:*:*"]
        ))

        # Let us prepare our FluentBit Configuration Script

        # Use the script below, if you have a pre-written script, if not use the parts below to ASSEMBLE the script
        # Read BootStrap Script):
        try:
            with open("elastic_fluent_bit_kibana/stacks/back_end/bootstrap_scripts/configure_fluent_bit.sh",
                      encoding="utf-8",
                      mode="r"
                      ) as f:
                bash_commands_to_run = f.read()
        except OSError as e:
            print("Unable to read bash commands file")
            raise e

        es_endpoint = _ssm.StringParameter.value_for_string_parameter(
            self, es_endpoint_param_name
        )
        es_region = _ssm.StringParameter.value_for_string_parameter(
            self, es_region_param_name
        )

        bash_commands_to_run_01 = """
#!/bin/bash
set -ex
set -o pipefail

# version: 22Nov2020

##################################################
#############     SET GLOBALS     ################
##################################################

REPO_NAME="elastic-fluent-bit-kibana"

GIT_REPO_URL="https://github.com/miztiik/$REPO_NAME.git"

APP_DIR="/var/$REPO_NAME"

LOG_FILE="/var/log/miztiik-automation-configure-fluent-bit.log"

function install_fluent_bit(){
# https://docs.fluentbit.io/manual/installation/linux/amazon-linux
cat > '/etc/yum.repos.d/td-agent-bit.repo' << "EOF"
[td-agent-bit]
name = TD Agent Bit
baseurl = https://packages.fluentbit.io/amazonlinux/2/$basearch/
gpgcheck=1
gpgkey=https://packages.fluentbit.io/fluentbit.key
enabled=1
EOF

# Install the agent
sudo yum -y install td-agent-bit
sudo service td-agent-bit start
service td-agent-bit status
}

function create_config_files(){
    mkdir -p ${APP_DIR}
    cd ${APP_DIR}

echo "
[INPUT]
    name            tail
    path            /var/log/httpd/*log
    tag             automate_log_parse
    Path_Key        filename
[FILTER]
    Name    record_modifier
    Match   *
    Record  hostname    ${HOSTNAME}
    Record  project     elastic-fluent-bit-kibana-demo
    Add     user        Mystique
" > ${APP_DIR}/es.conf
"""

        bash_commands_to_run_02 = f"""
echo "
[OUTPUT]
    Name            es
    Match           automate_log*
    Host            {es_endpoint}
    Port            443
    tls             On
    AWS_Auth        On
    AWS_Region      {es_region}
    Index           miztiik_automation
    Type            app_logs
    Include_Tag_Key On
" >> ${{APP_DIR}}/es.conf
}}
        """

        bash_commands_to_run_03 = """

function configure_fluent_bit(){
# Stop the agent
sudo service td-agent-bit stop

# DO NOT DO THIS IN ANY SERIOUS CONFIG FILE
# Null the defaults and start fresh
> /etc/td-agent-bit/td-agent-bit.conf

echo "
[SERVICE]
    Flush 3
@INCLUDE ${APP_DIR}/es.conf
" > /etc/td-agent-bit/td-agent-bit.conf

sudo service td-agent-bit start
sudo service td-agent-bit status
}

install_fluent_bit >> "${LOG_FILE}"
create_config_files >> "${LOG_FILE}"
configure_fluent_bit >> "${LOG_FILE}"
"""

        bash_commands_to_run = bash_commands_to_run_01 + \
            bash_commands_to_run_02 + bash_commands_to_run_03

        # Configure Fluent Bit using SSM Run Commands
        config_fluenbit_doc = CreateSsmRunCommandDocument(
            self,
            "configureFluentBitToEs",
            run_document_name="configureFluentBitToEs",
            _doc_desc="Bash script to configure FluentBit to send logs to ES",
            bash_commands_to_run=bash_commands_to_run,
            enable_log=False
        )

        # Create SSM Association to trigger SSM doucment to target (EC2)
        _run_commands_on_ec2 = _ssm.CfnAssociation(
            self,
            "runCommandsOnEc2",
            name=config_fluenbit_doc.get_ssm_linux_document_name,
            targets=[{
                "key": "InstanceIds",
                "values": [self.fluent_bit_server.instance_id]
            }]
        )

        ###########################################
        ################# OUTPUTS #################
        ###########################################
        output_0 = core.CfnOutput(
            self,
            "AutomationFrom",
            value=f"{GlobalArgs.SOURCE_INFO}",
            description="To know more about this automation stack, check out our github page."
        )
        output_1 = core.CfnOutput(
            self,
            "FluentBitPrivateIp",
            value=f"http://{self.fluent_bit_server.instance_private_ip}",
            description=f"Private IP of Fluent Bit Server on EC2"
        )
        output_2 = core.CfnOutput(
            self,
            "FluentBitInstance",
            value=(
                f"https://console.aws.amazon.com/ec2/v2/home?region="
                f"{core.Aws.REGION}"
                f"#Instances:search="
                f"{self.fluent_bit_server.instance_id}"
                f";sort=instanceId"
            ),
            description=f"Login to the instance using Systems Manager and use curl to access the Instance"
        )
        output_3 = core.CfnOutput(
            self,
            "AwsForFluentBit",
            value=(
                f"https://github.com/aws/aws-for-fluent-bit/tree/master/examples/fluent-bit/systems-manager-ec2"
            ),
            description=f"Amazon docs on fluent bit"
        )

        output_4 = core.CfnOutput(
            self,
            "WebServerUrl",
            value=f"{self.fluent_bit_server.instance_public_dns_name}",
            description=f"Public IP of Web Server on EC2"
        )
        output_5 = core.CfnOutput(
            self,
            "GenerateAccessTraffic",
            value=f"ab -n 10 -c 1 http://{self.fluent_bit_server.instance_public_dns_name}/",
            description=f"Public IP of Web Server on EC2"
        )
        output_6 = core.CfnOutput(
            self,
            "GenerateFailedTraffic",
            value=f"ab -n 10 -c 1 http://{self.fluent_bit_server.instance_public_dns_name}/${{RANDOM}}",
            description=f"Public IP of Web Server on EC2"
        )

    # properties to share with other stacks
    @property
    def get_inst_id(self):
        return self.fluent_bit_server.instance_id
