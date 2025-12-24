# Biotech Run-Up Radar - Technical Specifications

> **Specs-Driven Development**: All features are documented here before implementation.

## Directory Structure

```
specs/
├── README.md                          # This file - overview and index
├── ROADMAP.md                         # Phased development roadmap
├── architecture/                      # System design and architecture
│   ├── 01-current-state.md           # Current architecture (MVP)
│   ├── 02-target-architecture.md     # Target architecture (n8n-based)
│   ├── 03-data-pipeline.md           # Data pipeline design
│   └── 04-agentic-workflows.md       # AI agent workflow patterns
├── features/                          # Feature specifications
│   ├── 01-stripe-integration.md      # Payment processing
│   ├── 02-free-trial.md              # 7-day trial system
│   ├── 03-paywall.md                 # Content gating
│   ├── 04-user-management.md         # Auth & user accounts
│   ├── 05-email-automation.md        # Trial conversion emails
│   └── 06-analytics.md               # Product analytics
├── api/                               # API contracts and documentation
│   ├── 01-rest-api.md                # REST API specification
│   ├── 02-webhooks.md                # Stripe webhooks
│   └── 03-data-schemas.md            # Data models and schemas
├── workflows/                         # n8n workflow definitions
│   ├── 01-daily-scrape.md            # Daily ClinicalTrials.gov scrape
│   ├── 02-ticker-enrichment.md       # Stock data enrichment
│   ├── 03-report-generation.md       # Report generation & distribution
│   └── 04-trial-conversion.md        # Trial user conversion automation
└── infrastructure/                    # Deployment and operations
    ├── 01-deployment.md              # Hosting and deployment
    ├── 02-monitoring.md              # Observability and alerts
    └── 03-data-storage.md            # Database and caching strategy

```

## Development Workflow

### 1. Specification Phase
- Create detailed spec in appropriate directory
- Include user stories, technical requirements, API contracts
- Review and approve spec before coding

### 2. Implementation Phase
- Reference spec document in PR description
- Implement according to spec
- Update spec if requirements change

### 3. Validation Phase
- Verify implementation matches spec
- Update spec with "Implementation Status" section
- Mark spec as ✅ Implemented or 🚧 Partial

## Current Status

| Area | Status | Priority | Target |
|------|--------|----------|--------|
| **Architecture** | 🚧 Planning | High | Week 1 |
| **Stripe Integration** | 📝 Spec Draft | High | Week 2-3 |
| **Free Trial System** | 📝 Spec Draft | High | Week 2-3 |
| **n8n Workflows** | 🚧 Planning | Medium | Week 3-4 |
| **API Layer** | 📝 Spec Draft | Medium | Week 4-5 |
| **User Management** | ⏳ Not Started | Low | Week 6+ |

## Legend

- 📝 **Spec Draft** - Specification written, not reviewed
- ✅ **Approved** - Spec reviewed and approved
- 🚧 **In Progress** - Implementation underway
- ✅ **Implemented** - Feature complete
- ⏳ **Not Started** - Spec not yet written

## Key Principles

1. **No Code Without Specs** - Write the spec first, code second
2. **Incremental Delivery** - Ship small, testable increments
3. **User Stories First** - Start with "As a user, I want..."
4. **API Contracts** - Define data schemas before implementation
5. **Test Coverage** - Include test scenarios in specs

## Quick Links

- [Development Roadmap](./ROADMAP.md)
- [Current vs Target Architecture](./architecture/02-target-architecture.md)
- [Feature: Stripe Integration](./features/01-stripe-integration.md)
- [Workflow: Daily Scrape (n8n)](./workflows/01-daily-scrape.md)

---

**Last Updated**: 2025-12-24
**Owner**: Development Team
**Status**: 🚧 Active Development
