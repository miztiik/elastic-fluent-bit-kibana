from aws_cdk import aws_ec2 as _ec2
from aws_cdk import aws_iam as _iam
from aws_cdk import aws_ssm as _ssm
from aws_cdk import aws_elasticsearch as _es
from aws_cdk import core

from elastic_fluent_bit_kibana.constructs.create_ssm_parameter_construct import CreateSsmStringParameter


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


class ElasticSearchStack(core.Stack):

    def __init__(
        self,
        scope: core.Construct, id: str,
        vpc,
        cognito_for_es,
        es_domain_name: str,
        stack_log_level: str,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # AWS Elasticsearch Domain
        # It is experimental as on Q2 2020
        """
        es_log_search = _es.Domain(
            self,
            "logSearcher",
            version=_es.ElasticsearchVersion.V7_1,
            capacity={
                "master_nodes": 1,
                "data_nodes": 1
            },
            ebs={
                "volume_size": 20,
                "volume_type": _ec2.EbsDeviceVolumeType.GP2
            },
            zone_awareness={
                "availability_zone_count": 1
            },
            logging={
                "slow_search_log_enabled": True,
                "app_log_enabled": True,
                "slow_index_log_enabled": True
            }
        )
        """

        # Access Policy for Elastic
        elastic_policy = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW,
            actions=["es:*", ],
            # principals={"AWS": es_auth_role.role_arn},
            resources=[
                # f"arn:aws:es:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:domain/{es_domain_name}/*"
                "*"
            ],
        )

        elastic_policy.add_aws_account_principal(
            core.Aws.ACCOUNT_ID
        )
        elastic_document = _iam.PolicyDocument()
        elastic_document.add_statements(elastic_policy)

        # Security group for elastic
        self.elastic_security_group = _ec2.SecurityGroup(
            self,
            "elastic_security_group",
            vpc=vpc.get_vpc,
            description="elastic security group",
            allow_all_outbound=True,
        )

        self.elastic_security_group.connections.allow_from(
            other=_ec2.Peer.ipv4(vpc.get_vpc.vpc_cidr_block),
            port_range=_ec2.Port.tcp(9200),
            description="Allow Incoming FluentBit Traffic"
        )
        self.elastic_security_group.connections.allow_from(
            other=_ec2.Peer.ipv4(vpc.get_vpc.vpc_cidr_block),
            port_range=_ec2.Port.tcp(443),
            description="Allow Kibana Access"
        )

        # Amazon ElasticSearch Cluster
        es_log_search = _es.CfnDomain(
            self,
            "logSearcher",
            domain_name=f"{es_domain_name}",
            elasticsearch_cluster_config={
                # "dedicated_master_count": 1,
                "dedicated_master_enabled": False,
                "instanceCount": 2,
                "instanceType": "t3.small.elasticsearch",
                "zoneAwarenessEnabled": True,
                # "zoneAwarenessConfig": {"availability_zone_count": 2},
            },
            elasticsearch_version="7.1",
            ebs_options=_es.CfnDomain.EBSOptionsProperty(
                ebs_enabled=True,
                volume_size=10
            ),
            # vpc_options={
            #     "securityGroupIds": [self.elastic_security_group.security_group_id],
            #     "subnetIds": vpc.get_vpc_private_subnet_ids,
            # },
            access_policies=elastic_document,
            cognito_options=_es.CfnDomain.CognitoOptionsProperty(
                enabled=True,
                identity_pool_id=cognito_for_es.get_es_identity_pool_ref,
                user_pool_id=cognito_for_es.get_es_user_pool_id,
                role_arn=cognito_for_es.get_es_role_arn
            )
        )

        es_log_search.access_policies = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": cognito_for_es.get_es_auth_role_arn},
                    "Action": "es:*",
                    "Resource": f"arn:aws:es:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:domain/{es_domain_name}/*"
                }
            ]
        }

        es_endpoint_param = CreateSsmStringParameter(
            self,
            "esEndpointSsmParameter",
            _param_desc=f"ElasticSearch Domain Endpoint",
            _param_name="/miztiik-automation/es/endpoint",
            _param_value=f"{es_log_search.attr_domain_endpoint}"
        )

        es_region_param = CreateSsmStringParameter(
            self,
            "esRegionSsmParameter",
            _param_desc=f"ElasticSearch Domain Region",
            _param_name="/miztiik-automation/es/region",
            _param_value=f"{core.Aws.REGION}"
        )

        # Get latest version of Elasticsearch Endpoint & Region Parameter Name
        self.es_endpoint_param_name = "/miztiik-automation/es/endpoint"
        self.es_region_param_name = "/miztiik-automation/es/region"

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
            "LogSearchInEsDomainEndpoint",
            value=f"{es_log_search.attr_domain_endpoint}",
            description=f"ElasticSearch Domain Endpoint"
        )

        output_2 = core.CfnOutput(
            self,
            "kibanaUrl",
            value=f"https://{es_log_search.attr_domain_endpoint}/_plugin/kibana/",
            description="Access Kibana via this URL."
        )
