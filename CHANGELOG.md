# Release v1.0.0

## Features
- feat: Replace evaluate_feature with update_usage_levels in DashboardService

## Tests
No test changes.
## Documentation
No documentation changes.
## Fixes
No fixes added.
## Continuous integration (CI)
No CI changes.
## Other changes
- Merge pull request #61 from SocialBeats/develop
- Merge branch 'develop' of https://github.com/SocialBeats/analytics-and-dashboards into develop

## Full commit history

For full commit history, see [here](https://github.com/SocialBeats/analytics-and-dashboards/compare/v0.0.3...v1.0.0).

# Release v0.0.3

## Features
- feat: Simplify rate limiting by removing dynamic limit functionality

## Tests
No test changes.
## Documentation
No documentation changes.
## Fixes
No fixes added.
## Continuous integration (CI)
No CI changes.
## Other changes
- Merge pull request #60 from SocialBeats/develop

## Full commit history

For full commit history, see [here](https://github.com/SocialBeats/analytics-and-dashboards/compare/v0.0.2...v0.0.3).

# Release v0.0.2

## Features
- feat: Update rate limiter for simplicity
- feat: Adaptation and integration of SPACE for pricing
- feat: prevent multiple dashboards for the same beat
- feat: Update CORS origins and add Azure Translator API key
- feat: Update CORS origins and add Azure Translator API key
- feat: Added command to delete a dashboard and its beat when requested so
- feat: Add metrics status and real-time event notification endpoints
- feat: Added services and endpoints for new translator API
- feat: Enhance Kafka consumer settings and notify beats service upon metrics creation
- feat: Update Kafka broker configuration and enhance message logging in Kafka consumer service
- feat: Add Quotable API integration with caching and rate limiting
- feat: Enhance testing setup with Docker integration
- feat: Add unit tests for BeatMetricsService with mocked dependencies
- feat: Add unit tests for WidgetService to ensure functionality and error handling
- feat: Add unit tests for DashboardService covering CRUD operations and validation
- feat: Integrate Kafka consumer service and add health check endpoint

## Tests
No test changes.
## Documentation
No documentation changes.
## Fixes
- fix: Added removed sentitive information from .env.example and docker-compose.yml
- fix: Update BEATS_SERVICE_URL and enhance beat ownership verification logging

## Continuous integration (CI)
No CI changes.
## Other changes
- Merge pull request #59 from SocialBeats/develop
- Merge pull request #58 from SocialBeats/feat/space-integration
- Merge pull request #57 from SocialBeats/feat/delete-beats-command
- chore: resolve merge conflict in .env.example
- Merge pull request #56 from SocialBeats/fix/azure-translator-config
- Merge pull request #55 from SocialBeats/feat/metrics-status
- Merge pull request #54 from SocialBeats/feat/microsoft-translator-api
- Merge branch 'develop' into feat/microsoft-translator-api
- Merge pull request #49 from SocialBeats/feat/metrics-pending
- Merge pull request #46 from SocialBeats/feat/calculate-metrics
- Merge pull request #47 from SocialBeats/feat/external-api
- Merge pull request #40 from SocialBeats/feat/test-suite
- Merge pull request #38 from SocialBeats/feat/kafka-integration
- Merge pull request #35 from SocialBeats/fix/beats-upload-connection
- Add MIT License to the project

## Full commit history

For full commit history, see [here](https://github.com/SocialBeats/analytics-and-dashboards/compare/v0.0.1...v0.0.2).

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

