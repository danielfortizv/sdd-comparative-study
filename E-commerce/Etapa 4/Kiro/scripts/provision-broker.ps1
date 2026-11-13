# Provision the Stage 4 RabbitMQ vhost, user, and permissions (idempotent).
#
# The tool-isolated broker parameters come from stage4-runtime.json:
#   user=ecommerce  password=stage4-demo  vhost=stage4_kiro
#
# RabbitMQ runs in Ubuntu/WSL on this host (Docker is unavailable). This script
# is a no-op when the entities already exist. It requires rabbitmqctl privileges
# inside WSL; if the broker is already provisioned (the common case here) you do
# NOT need to run this script.

$ErrorActionPreference = "Stop"

$vhost = "stage4_kiro"
$user = "ecommerce"
$pass = "stage4-demo"

Write-Host "Provisioning RabbitMQ vhost '$vhost' and user '$user' via WSL..."

$script = @"
set -e
sudo rabbitmqctl add_vhost $vhost 2>/dev/null || true
sudo rabbitmqctl add_user $user $pass 2>/dev/null || true
sudo rabbitmqctl set_permissions -p $vhost $user '.*' '.*' '.*'
echo 'Provisioned.'
"@

wsl bash -lc $script
Write-Host "Done. (If this failed on sudo, the broker is likely already provisioned.)"
