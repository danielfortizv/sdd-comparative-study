## SonarQube Evaluation Environment

- SonarQube edition: Community Build
- SonarQube version: 26.9.0.129388
- Deployment: Docker
- SonarScanner CLI version: 8.1.0.6389
- Quality profiles: Sonar way
- Scanner operating system: Linux (Docker / WSL2)
- Analyzed directories:
  - backend/
  - frontend/
- Excluded:
  - virtual environments
  - node_modules
  - dist
  - build
  - coverage
  - SQLite database files
- Project key pattern: `shift-bank-stage1-[tool]`
- Coverage reports added manually: No
- Same analysis configuration for all SDD tools: Yes
- Python runtime observed in OpenSpec implementation: 3.13.2
- SonarQube Python compatibility target: 3.13

## SonarQube Metrics

### Size
- Lines of Code (ncloc)

### Maintainability
- Maintainability issues
- Maintainability rating
- Technical debt
- Technical debt ratio

### Reliability
- Reliability issues
- Reliability rating

### Security
- Security issues
- Security rating
- Security hotspots

### Complexity
- Cyclomatic complexity
- Cognitive complexity

### Duplication
- Duplicated lines
- Duplicated lines density

### Testing
- Coverage

### Overall
- Quality Gate status

### SonarQube Limitations

- SonarQube Community Build reports limited security analysis.
- The Community Build used in this experiment does not scan for some critical injection vulnerabilities such as SQL injection and XSS.
- Security metrics are therefore recorded as reported by SonarQube, but they must not be interpreted as a complete security assessment.