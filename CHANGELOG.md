# Changelog

All notable changes to the impact-check skill will be documented in this file.

## [1.0.0] - 2026-07-27

### Added
- Initial release of impact-check skill
- Python static analyzer for cross-repo dependency tracing
- HTTP API call pattern detection (FastAPI, Flask)
- Test coverage integration via pytest-cov
- Impact level classification (HIGH/MEDIUM/LOW)
- Structured IMPACT CHECK REPORT generation
- Automatic PR description append via GitHub CLI
- Non-blocking CAUTION/WARNING verdicts
- Support for both JSON and XML coverage formats
- Comprehensive test suite
- Documentation and quick start guide

### Features
- Scans all repos under ~/work/ for dependencies
- Traces Python imports across microservices
- Detects HTTP calls to changed API endpoints
- Maps test coverage to changed files
- Flags coverage gaps below 80% threshold
- Generates both text and markdown formatted reports
- Integrates with story-to-pr and pr-review workflows

### Technical Details
- Pure Python implementation (3.7+)
- No external dependencies required
- Uses AST for static code analysis
- Regex patterns for API call detection
- Git CLI for change detection
- GitHub CLI for PR integration

### Limitations
- Python-only analysis (no JS/TS support yet)
- Requires local repos under work directory
- HTTP call detection limited to common patterns
- Coverage requires recent pytest-cov run

## Future Roadmap

### [1.1.0] - Planned
- [ ] JavaScript/TypeScript support
- [ ] Database dependency tracking (SQLAlchemy, Django ORM)
- [ ] Message queue dependency detection (Celery, RabbitMQ)
- [ ] Caching for faster re-runs
- [ ] Service registry integration
- [ ] Deployment coordination helpers

### [1.2.0] - Planned
- [ ] Go language support
- [ ] gRPC call detection
- [ ] GraphQL schema change impact
- [ ] Docker/K8s deployment dependencies
- [ ] Historical impact analysis
- [ ] Team notification integration (Slack, email)

### [2.0.0] - Vision
- [ ] Real-time dependency graph
- [ ] Machine learning for impact prediction
- [ ] Integration test impact analysis
- [ ] Performance regression detection
- [ ] Security vulnerability propagation tracking
- [ ] Auto-generated coordination plan for high-impact changes
