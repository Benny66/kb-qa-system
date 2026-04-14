## ADDED Requirements

### Requirement: Frontend Dockerization
The system SHALL provide a `Dockerfile` in the `kb-qa-frontend` directory capable of building and running the frontend application.

#### Scenario: Building frontend image
- **WHEN** running `docker build -t frontend kb-qa-frontend/`
- **THEN** an image is successfully built and can serve the frontend app.

### Requirement: Backend Dockerization
The system SHALL provide a `Dockerfile` in the `kb-qa-backend` directory capable of building and running the backend application.

#### Scenario: Building backend image
- **WHEN** running `docker build -t backend kb-qa-backend/`
- **THEN** an image is successfully built and can run the backend service.

### Requirement: Docker Compose Orchestration
The system SHALL provide a `docker-compose.yml` file in the project root to orchestrate the frontend and backend services.

#### Scenario: Running docker-compose up
- **WHEN** running `docker-compose up -d` at the project root
- **THEN** both frontend and backend services start and are accessible via their respective ports.
