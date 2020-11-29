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
    mkdir -p "${APP_DIR}"
    cd "${APP_DIR}"

cat > ${APP_DIR}/es.conf << EOF
[INPUT]
    name            tail
    path            /var/log/httpd/*.log
    tag             automation_log_lambda
    Path_Key        filename

[FILTER]
    Name record_modifier
    Match *
    Record hostname ${HOSTNAME}
    Record project elastic-fluent-bit-kibana-demo
    Add user Mystique

[OUTPUT]
    Name          es
    Match         automation_log*
    Host          search-theydal-x6x4l7lq62hbb24aeugn7lce3y.us-east-1.es.amazonaws.com
    Port          443
    tls           On
    AWS_Auth      On
    AWS_Region    us-east-1
    Index         miztiik_automation
    Type          app_logs
EOF
}


function configure_fluent_bit(){
# Stop the agent
sudo service td-agent-bit stop

# DO NOT DO THIS IN ANY SERIOUS CONFIG FILE
# Null the defaults and start fresh
> /etc/td-agent-bit/td-agent-bit.conf

cat > '/etc/td-agent-bit/td-agent-bit.conf' << EOF
[SERVICE]
    Flush 2

@INCLUDE ${APP_DIR}/es.conf
EOF

sudo service td-agent-bit start
sudo service td-agent-bit status
}

install_fluent_bit
create_config_files >> /var/log/miztiik-automation-configure-fluent-bit.log
configure_fluent_bit >> /var/log/miztiik-automation-configure-fluent-bit.log