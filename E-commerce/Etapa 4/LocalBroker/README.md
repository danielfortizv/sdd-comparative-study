# Local RabbitMQ infrastructure

Run `powershell -ExecutionPolicy Bypass -File .\Start-LocalBroker.ps1` from this folder before starting a tool's application. This uses the installed Ubuntu WSL RabbitMQ service and a localhost-only TCP relay where Windows localhost forwarding is unavailable. Python is required. The relay carries real AMQP traffic; it does not implement an event bus.

The local demo user is `ecommerce`, password `stage4-demo`. Vhosts are `stage4_openspec`, `stage4_kiro`, `stage4_tessl`, and `stage4_speckit`. These credentials are only for local demonstration. No cloud service or paid resource is provisioned.

Stopping RabbitMQ affects all four workspaces. Stop applications using their own stop scripts; leave this broker running while testing another tool. To stop the shared broker after all tests, run `wsl -d Ubuntu -u root -- service rabbitmq-server stop`. A relay process may remain idle; its PID and log are recorded next to the start script when this script starts it.

Infrastructure was prepared by the orchestration driver, outside the evaluated tools' application implementation. Docker was unavailable; each tool also supplies its own Compose configuration.

Startup now checks an actual AMQP response over IPv4, rather than treating any port-5672 listener as ready. When a relay is needed, it resolves the current WSL IPv4 address, verifies the upstream broker, and waits up to 30 seconds for the relay to answer. Failure reports point to `forwarder.err.log`. A stale relay is replaced only when its recorded PID still belongs to this launcher. The 2026-11-09 startup repair is recorded separately under `../Evaluacion/DriverFixes/2026-11-09-broker-startup/`; it is an orchestration repair, not a defect in a tool-generated application.
