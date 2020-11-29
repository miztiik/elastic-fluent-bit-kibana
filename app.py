#!/usr/bin/env python3

from elastic_fluent_bit_kibana.stacks.back_end.vpc_stack import VpcStack
from elastic_fluent_bit_kibana.stacks.back_end.cognito_for_es_stack import CognitoForEsStack
from elastic_fluent_bit_kibana.stacks.back_end.elasticsearch_stack import ElasticSearchStack
from elastic_fluent_bit_kibana.stacks.back_end.fluent_bit_on_ec2_stack import FluentBitOnEc2Stack


from aws_cdk import core

app = core.App()


# VPC Stack for hosting Secure API & Other resources
vpc_stack = VpcStack(
    app,
    f"{app.node.try_get_context('service_name')}-vpc-stack",
    stack_log_level="INFO",
    description="Miztiik Automation: Custom Multi-AZ VPC"
)

# Deploy Cognito User Pool to provide secure access to ElasticSearch
cognito_for_es = CognitoForEsStack(
    app,
    f"{app.node.try_get_context('service_name')}-cognito-for-stack",
    cognito_prefix="miztiik-automation",
    stack_log_level="INFO",
    description="Miztiik Automation: Deploy Cognito User Pool to provide secure access to ElasticSearch"
)

# Deploy Elasticsearch
log_search_in_es = ElasticSearchStack(
    app,
    f"{app.node.try_get_context('service_name')}-es-stack",
    vpc=vpc_stack,
    cognito_for_es=cognito_for_es,
    es_domain_name="yen-theydal",
    stack_log_level="INFO",
    description="Miztiik Automation: Deploy Elasticsearch"
)

# Deploy FluentBit on EC2
fluent_bit_on_ec2 = FluentBitOnEc2Stack(
    app,
    f"{app.node.try_get_context('service_name')}-fluent-bit-on-ec2-stack",
    vpc=vpc_stack.vpc,
    ec2_instance_type="t2.micro",
    es_endpoint_param_name=log_search_in_es.es_endpoint_param_name,
    es_region_param_name=log_search_in_es.es_region_param_name,
    stack_log_level="INFO",
    description="Miztiik Automation: Deploy FluentBit on EC2"
)


# Stack Level Tagging
core.Tag.add(app, key="Owner",
             value=app.node.try_get_context("owner"))
core.Tag.add(app, key="OwnerProfile",
             value=app.node.try_get_context("github_profile"))
core.Tag.add(app, key="Project",
             value=app.node.try_get_context("service_name"))
core.Tag.add(app, key="GithubRepo",
             value=app.node.try_get_context("github_repo_url"))
core.Tag.add(app, key="Udemy",
             value=app.node.try_get_context("udemy_profile"))
core.Tag.add(app, key="SkillShare",
             value=app.node.try_get_context("skill_profile"))
core.Tag.add(app, key="AboutMe",
             value=app.node.try_get_context("about_me"))
core.Tag.add(app, key="BuyMeACoffee",
             value=app.node.try_get_context("ko_fi"))
app.synth()
