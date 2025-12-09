# Release v0.0.1

## Features
- feat: Update BEATS_SERVICE_URL to point to the new microservice endpoint
- feat: Add GitHub Actions workflow for release automation and update Docker Compose with Beats service URL
- feat: Update environment configuration and modify container names and ports in docker-compose
- feat: Enhance beat ownership verification to include userId as a fallback for owner identification
- feat: Implement beat ownership verification for dashboard and metrics operations
- feat: Add beat ownership verification for metrics operations and update service configuration
- feat: Implement dashboard ownership validation for widget operations
- feat: Enhance dashboard permissions and ownership management
- feat: Add example endpoints demonstrating rate limiting
- feat: Implement rate limiting with Redis support
- feat: Add Circuit Breaker middleware to enhance service resilience
- feat: Integrate user authentication into beat metrics, dashboards, and widgets endpoints
- feat: Add documentation for JWT authentication implementation and usage examples
- feat: Implement JWT authentication middleware and update configuration for security
- feat: Configure Docker for audio processing support
- feat: Integrate automatic audio analysis in BeatMetrics creation
- feat: Add audio analysis with librosa
- feat: Refactor API endpoints to use '/analytics' prefix for consistency
- feat: Update application to use port 3003; modify configurations and documentation accordingly
- feat: Remove item endpoints and related code; add beat metrics functionality with CRUD operations
- feat: add Docker build command to README
- feat: Implement the dashboards feature with CRUD operations as an initial version.
- feat: Implement the dashboards feature with CRUD operations as an initial version.
- feat: Initial repository skeleton, dependecies and config

## Tests
No test changes.
## Documentation
- docs: Update authentication documentation to reflect migration to API Gateway-based authentication
- docs: Add docs for Rate limiting and modify docs Beat analysis, and JWT auth
- docs: Add comprehensive documentation for audio analysis

## Fixes
- fix: Remove unnecessary parameter from create_beat_metrics endpoint
- fix: Change location of examples for JWT authentication
- fix: Remove unnecessary parameter from create_beat_metrics endpoint
- fix: Update container name in docker-compose.yml for api gateway conection
- fix: Update BeatMetrics and related schemas to enhance serialization and optional fields

## Continuous integration (CI)
No CI changes.
## Other changes
- Merge pull request #34 from SocialBeats/develop
- Merge pull request #32 from SocialBeats/feat/create-dashboard
- Merge pull request #29 from SocialBeats/fix/service-auth
- refactor: Remove JWT_SECRET and update authentication middleware to rely on API Gateway headers
- Merge pull request #27 from SocialBeats/feat/throttling
- Merge branch 'develop' into feat/throttling
- Merge pull request #26 from SocialBeats/feat/circuit-breaker
- refactor: Update tier labels
- Merge pull request #23 from SocialBeats/feat/beat-analysis
- Merge branch 'develop' into feat/beat-analysis
- Merge pull request #19 from SocialBeats/feat/jwt-auth
- Merge pull request #14 from SocialBeats/fix/change-docker-image-name
- Merge pull request #13 from SocialBeats/feat/conexion-gateway
- Merge pull request #11 from SocialBeats/feat/entidades-bdd
- Initial commit

## Full commit history

For full commit history, see [here](https://github.com/SocialBeats/analytics-and-dashboards/compare/...v0.0.1).

