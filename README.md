# Ezzat Mohamed

**Java Back-End Developer** — Spring Boot · REST APIs · API Security
Helwan, Cairo, Egypt

I build back-end services for systems where being wrong is expensive: payment integration for Bank Misr, multi-tenant enterprise APIs on Oracle, and a national food-subsidy platform. That shapes how I work — I reproduce a problem before I change anything, and I write a test that proves it is fixed.

My focus is **API security**: OAuth2 and OpenID Connect, JWT issuance and validation, role- and permission-based access control, and multi-tenant isolation. Most of that work is public below, with the design decisions written down.

---

## What I work on

- **Secure REST APIs** — Spring Boot services with validation, consistent error contracts, OpenAPI documentation, and tests that exercise the real security filter chain
- **Authentication and authorization** — OAuth2 / OIDC authorization servers, JWT with JWKS-based verification, refresh-token rotation, key and secret rotation without downtime
- **Multi-tenant systems** — tenant isolation enforced at both authentication and authorization, so a valid token from one tenant cannot read another's data
- **Microservices** — service discovery, centralized configuration, API gateways, event-driven messaging over Kafka
- **Enterprise and legacy Java** — Java EE, JSF/PrimeFaces and Oracle systems, including incremental modernization toward Spring Boot

---

## Core stack

| | |
|---|---|
| **Languages** | Java (8 / 11 / 17 / 21), SQL |
| **Frameworks** | Spring Boot, Spring Security, Spring Data JPA, Spring Cloud, Spring Authorization Server, Hibernate |
| **Security** | OAuth2, OpenID Connect, JWT / JWKS, PKCE, RBAC, multi-tenancy |
| **Data** | PostgreSQL, Oracle, MySQL, MongoDB, Redis, Flyway |
| **Messaging** | Apache Kafka |
| **Testing** | JUnit 5, Mockito, Testcontainers, MockMvc, WebTestClient, WireMock |
| **Tooling** | Docker, Docker Compose, Maven, Git, OpenAPI / Swagger, Actuator |
| **Legacy** | Java EE, JSF / PrimeFaces, WebLogic, Apache POI |

---

## Selected projects

### [authcore](https://github.com/ezat141/authcore) — Multi-tenant OAuth2 / OpenID Connect authorization server

The component behind enterprise SSO, built from scratch rather than configured. Issues signed tokens for three client types — a server-side web app, a browser SPA, and machine services — and enforces what each token holder may do through roles and permissions. Multiple isolated tenants share one server, so the same username can belong to two unrelated organizations.

The parts that usually go wrong are the point of the project: refresh tokens rotate on every use and a replayed token revokes the entire family; signing keys and client secrets rotate while the server is running, without invalidating anything still legitimately in use; a revoked token stops working immediately rather than at expiry.

`Java 21 · Spring Boot · Spring Authorization Server · PostgreSQL · Redis · Flyway · Testcontainers` — **65 tests against real PostgreSQL and Redis, not mocks.**

### [gatekeeper](https://github.com/ezat141/gatekeeper) — Reactive zero-trust API gateway

A Spring Cloud Gateway edge running on Netty that verifies every request's token against the authorization server's published JWKS, strips any identity headers a client tried to forge, and stamps the caller's verified identity for downstream services.

The design position matters more than the code: the gateway is a coarse first layer, not the security boundary. Services behind it re-verify independently, so bypassing it entirely gains an attacker nothing — a gateway that owns authorization becomes a single point whose compromise unlocks everything behind it.

`Java 21 · Spring Cloud Gateway · WebFlux / Netty · Spring Security · Redis · WireMock`

### [ledger-service](https://github.com/ezat141/ledger-service) — Resource server that trusts nothing upstream

The other half of the argument above. It verifies JWTs itself and enforces tenant isolation on its own data, so it is exactly as secure called directly as it is behind the gateway. A dedicated endpoint reports header-asserted identity beside token-derived identity and flags any disagreement, which demonstrates in one response why headers are informational and never authoritative.

`Java 21 · Spring Boot · Spring Security OAuth2 Resource Server` — **26 tests.**

### [E-commerce-Microservices-](https://github.com/ezat141/E-commerce-Microservices-) — Distributed e-commerce platform

Eight Spring Boot services — customer, product, order, payment, notification, gateway, discovery, and config server — wired together with Eureka service discovery, centralized configuration, an API gateway secured by Keycloak, and asynchronous messaging over Kafka. Order and payment events drive notifications rather than synchronous calls. Distributed tracing through Zipkin, with the full infrastructure defined in Docker Compose.

`Java · Spring Boot · Spring Cloud · Eureka · OpenFeign · Kafka · PostgreSQL · MongoDB · Keycloak · Zipkin · Docker Compose`

### [spring-boot-api-starter](https://github.com/ezat141/spring-boot-api-starter) — Production-shaped REST API template

The starting point I use for new services, with the parts every project needs and nobody enjoys rebuilding: JWT authentication, role-based authorization, bean validation with per-field errors, one consistent error contract across controllers *and* the security filter chain, Flyway migrations, OpenAPI docs, and a multi-stage Docker build with a non-root runtime.

Schema and entities are validated against each other on startup, and the tests send real JWTs through the real filter chain rather than mocking authentication.

`Java 17 · Spring Boot 3.3 · Spring Security 6 · PostgreSQL · Flyway · springdoc · Docker` — **23 tests, no Docker required to run them.**

---

## Experience

**Java Back-End Developer — Smart Digital Services** · Jan 2025 – Present
Spring Boot microservices and enterprise Java for banking and government clients: a payment integration platform with Bank Misr, multi-tenant REST APIs on Oracle with organization-scoped isolation and audit trails, and maintenance of large Java EE / JSF systems including modules for a national food-subsidy platform.

## Education

**B.Sc. Computer Engineering** — Helwan University, 2019–2024
**Java Spring Advanced** — Egyptian Banking Institute, 2024

---

## Contact

[LinkedIn](https://linkedin.com/in/ezzat-mohamed-1935751bb) · [ezat71101@gmail.com](mailto:ezat71101@gmail.com)

Open to back-end roles and contract work in Java / Spring Boot, particularly around API security and system integration.
