from aws_cdk import aws_iam as _iam
from aws_cdk import aws_ssm as _ssm
from aws_cdk import core


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


class SsmRunCommandsStack(core.Stack):

    def __init__(
        self,
        scope: core.Construct, construct_id: str,
        run_document_name: str,
        ec2_inst_id: str,
        stack_log_level: str,
        **kwargs
    ) -> None:

        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
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

        # SSM Run Command Document should be JSON Syntax
        # Ref: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ssm-document.html#cfn-ssm-document-content
        # Ref: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ssm/CfnDocument.html
        _run_cmds = {
            "schemaVersion": "2.2",
            "description": "Run script on Linux instances.",
            "parameters": {
                "commands": {
                    "type": "String",
                    "description": "The commands to run or the path to an existing script on the instance.",
                    "default": f"{bash_commands_to_run}"
                }
            },
            "mainSteps": [
                {
                    "action": "aws:runShellScript",
                    "name": "runCommands",
                    "inputs": {
                        "timeoutSeconds": "60",
                        "runCommand": [
                            "{{ commands }}"
                        ]
                    }
                }
            ]
        }

        # Create Linux Shell Script Document
        ssm_linux_document = _ssm.CfnDocument(
            self,
            "ssmLinuxDocument",
            document_type="Command",
            # name=f"{run_document_name}",
            content=_run_cmds
        )

        # Create SSM Association to trigger SSM doucment to target (EC2)
        _run_commands_on_ec2 = _ssm.CfnAssociation(
            self,
            "runCommandsOnEc2",
            name=ssm_linux_document.name,
            targets=[{
                "key": "InstanceIds",
                "values": [ec2_inst_id]
            }]
        )

        # As we are dealing with cloudformaiton resources, let us add a hard dependency
        _run_commands_on_ec2.add_depends_on(ssm_linux_document)

        ###########################################
        ################# OUTPUTS #################
        ###########################################
        output_0 = core.CfnOutput(
            self,
            "AutomationFrom",
            value=f"{GlobalArgs.SOURCE_INFO}",
            description="To know more about this automation stack, check out our github page."
        )
