# Final SonarQube scan preparation

Post-correction backend Cobertura and frontend LCOV have been regenerated using the initial instrumentation, same analyzed modules, same paths, and same configured scanner report locations. `sonarqube/sonar-project.properties` is unchanged and has SHA-256 `c6d52175bc0623c3c5b64fad0dbe705fb9f8e3cbaf3862466bf8e47277f87ee1`. The final scan must use the same frozen `sdd-sonar-scanner:frozen` image, server mapping, project properties, source scope, exclusions, Python/Node language settings, rule profiles, and Quality Gate. No new scan was submitted in this correction round.

In PowerShell at the project directory, transfer the already provisioned credential by environment variable and run the exact scanner invocation below. This does not put the token value in command arguments or logs:

```powershell
$env:SONAR_TOKEN = $env:SONAR_TOKEN_OPENSPEC3
docker run --rm --add-host=host.docker.internal:host-gateway `
  --env SONAR_TOKEN `
  --env SONAR_HOST_URL=http://host.docker.internal:9000 `
  --volume "${PWD}:/usr/src" `
  --workdir /usr/src `
  sdd-sonar-scanner:frozen `
  -Dproject.settings=/usr/src/sonarqube/sonar-project.properties `
  -Dsonar.verbose=true
```

Before execution, the researcher should confirm the expected variable is present without printing its value. After upload, wait for the CE task to reach SUCCESS; capture task ID, analysis ID, timestamp, metrics, gate conditions, paginated issues, and hotspot results. Compare only against baseline analysis `5242ca1c-0d7b-4acc-961a-e538fb54f1f1`. Do not infer improvement from local code changes or regenerated coverage alone. The initial extraction files and initial source hashes are immutable comparison evidence.

Post-correction source hashes: `E3_OPENSPEC_SONAR_SOURCE_HASHES_POSTCORRECTION.json`. Baseline extraction hashes: `E3_OPENSPEC_SONAR_BASELINE_EVIDENCE_SHA256.json`.
