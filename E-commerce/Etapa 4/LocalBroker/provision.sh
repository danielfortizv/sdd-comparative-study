#!/usr/bin/env bash
set -e
export RABBITMQ_CTL_ERL_ARGS='+S 2:2 +A 4'
service rabbitmq-server start
rabbitmqctl await_startup --timeout 30
if ! rabbitmqctl list_users -q | awk '{print $1}' | grep -qx ecommerce; then
  rabbitmqctl add_user ecommerce stage4-demo
fi
for name in openspec kiro tessl speckit; do
  vhost="stage4_${name}"
  rabbitmqctl add_vhost "$vhost"
  rabbitmqctl set_permissions -p "$vhost" ecommerce '.*' '.*' '.*'
done
rabbitmq-diagnostics -q ping
rabbitmqctl list_vhosts -q
