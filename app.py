#!/usr/bin/env python3

from aws_cdk import core

from elastic_fluent_bit_kibana.elastic_fluent_bit_kibana_stack import ElasticFluentBitKibanaStack


app = core.App()
ElasticFluentBitKibanaStack(app, "elastic-fluent-bit-kibana")

app.synth()
