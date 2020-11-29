from aws_cdk import aws_ssm as _ssm
from aws_cdk import core


class GlobalArgs:
    """
    Helper to define global statics
    """

    OWNER = "MystiqueAutomation"
    ENVIRONMENT = "production"
    REPO_NAME = "ssm_string_parameter_contruct"
    VERSION = "2020_11_24"
    MIZTIIK_SUPPORT_EMAIL = ["mystique@example.com", ]


class CreateSsmStringParameter(core.Construct):
    """
    AWS CDK Construct that defines an SSM String Parameter Store to be used by AWS applications.
    Will get a string value as a dictionary and then it will convert it as JSON String.
    """

    def __init__(
        self,
        scope: core.Construct,
        construct_id: str,
        _param_desc: str,
        _param_name: str,
        _param_value: str,
        **kwargs
    ) -> None:

        super().__init__(scope, construct_id, **kwargs)
        """
        :param _param_desc: Description of the string parameter
        :param configuration: Configuration of the construct. In this case SSM_PARAMETER_STRING.
        """

        self._parameter1_string = _ssm.StringParameter(
            self,
            f"param{id}",
            type=_ssm.ParameterType.STRING,
            description=f"{_param_desc}",
            parameter_name=f"{_param_name}",
            string_value=f"{_param_value}",
            tier=_ssm.ParameterTier.STANDARD
        )

    def grant_read(self, role):
        """
        Grants read permissions to AWS IAM roles.
        :param role: AWS IAM role that will have read access to the AWS SSM String Parameter
        :return:
        """
        self._parameter1_string.grant_read(role)

    @property
    def get_param_arn(self):
        """
        :return: Arn of the parameter.
        """
        return self._parameter1_string.parameter_arn

    @property
    def get_param_name(self):
        """
        :return: Name of the parameter.
        """
        return self._parameter1_string.parameter_name
