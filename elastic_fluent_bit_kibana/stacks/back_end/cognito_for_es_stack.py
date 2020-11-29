from aws_cdk import aws_iam as _iam
from aws_cdk import aws_cognito as _cognito
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


class CognitoForEsStack(core.Stack):

    def __init__(
        self,
        scope: core.Construct, construct_id: str,
        cognito_prefix: str,
        stack_log_level: str,
        **kwargs
    ) -> None:

        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        # Cognito User Pool for Kibana Access
        self.es_user_pool = _cognito.UserPool(
            self,
            "esCognitoUserPool",
            user_pool_name=f"{cognito_prefix}-log-parser-es-users",
            self_sign_up_enabled=False,
            sign_in_aliases=_cognito.SignInAliases(username=True, email=True),
            sign_in_case_sensitive=False,
            standard_attributes={
                "email": {
                    "required": True,
                    "mutable": False
                },
                "fullname": {
                    "required": False,
                    "mutable": True
                }
            },
            password_policy=_cognito.PasswordPolicy(
                min_length=8
            ),
            auto_verify=_cognito.AutoVerifiedAttrs(email=True)
        )

        # Create User Pool Domain to enable SignUp, SignIn, Auth & Callback Urls
        es_auth_domain = _cognito.UserPoolDomain(
            self,
            "esCognitoUserPoolDomain",
            user_pool=self.es_user_pool,
            cognito_domain=_cognito.CognitoDomainOptions(
                domain_prefix=f"{cognito_prefix}-{core.Aws.ACCOUNT_ID}"
            )
        )

        # Role Authenticated Cognito Users will assume in ES Service
        self.es_role = _iam.Role(
            self,
            "esKibanaIamRole",
            assumed_by=_iam.ServicePrincipal("es.amazonaws.com"),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    managed_policy_name="AmazonESCognitoAccess"
                )
            ],
        )

        # Create Cognito Federated Identity Pool to exchange Cognito auth token for AWS Token
        self.es_id_pool = _cognito.CfnIdentityPool(
            self,
            "esIdentityPool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[],
        )

        # Role For Cognito Federated Idenity Pool Authenticated Users
        self.es_auth_role = _iam.Role(
            self,
            "esAuthIamRole",
            assumed_by=_iam.FederatedPrincipal(
                federated="cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {"cognito-identity.amazonaws.com:aud": self.es_id_pool.ref},
                    "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "authenticated"},
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity"),
        )

        # Attach a Role to Cognito Federated Idenity Pool Authenticated Users
        _cognito.CfnIdentityPoolRoleAttachment(
            self,
            "cognitoFederatedIdentityPoolRoleAttachment",
            identity_pool_id=self.es_id_pool.ref,
            roles={
                "authenticated": self.es_auth_role.role_arn
            }
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
            "CreateCognitoUserConsole",
            value=f"https://{core.Aws.REGION}.console.aws.amazon.com/cognito/users?region={core.Aws.REGION}#/pool/{self.es_user_pool.user_pool_id}/users",
            description="Create a new user in the user pool here."
        )

    # properties to share with other stacks
    @property
    def get_es_user_pool_id(self):
        return self.es_user_pool.user_pool_id

    @property
    def get_es_identity_pool_ref(self):
        return self.es_id_pool.ref

    @property
    def get_es_role_arn(self):
        return self.es_role.role_arn

    @property
    def get_es_auth_role_arn(self):
        return self.es_auth_role.role_arn
