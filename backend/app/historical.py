from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import date
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class HistoricalIncident:
    id: str
    project_id: str
    project_category: str
    problem_description: str
    root_cause: str
    resolution: str
    outcome: str
    technologies: tuple[str, ...]
    evidence_source: str
    event_date: date

    @property
    def search_text(self) -> str:
        return " ".join(
            (
                self.project_category,
                self.problem_description,
                self.root_cause,
                self.resolution,
                " ".join(self.technologies),
            )
        )


@dataclass(frozen=True, slots=True)
class RetrievedIncident:
    incident: HistoricalIncident
    score: float


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class IncidentRepository(Protocol):
    def all(self) -> Sequence[HistoricalIncident]: ...


class DeterministicEmbeddingProvider:
    """Stable local embeddings for fixtures and no-key development."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += -1.0 if digest[4] & 1 else 1.0
        magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / magnitude for value in vector]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


class HistoricalContextService:
    def __init__(self, repository: IncidentRepository, embeddings: EmbeddingProvider) -> None:
        self.repository = repository
        self.embeddings = embeddings

    def retrieve(self, query: str, limit: int = 5) -> list[RetrievedIncident]:
        query_embedding = self.embeddings.embed(query)
        matches = [
            RetrievedIncident(
                incident=incident,
                score=round(
                    cosine_similarity(query_embedding, self.embeddings.embed(incident.search_text)),
                    6,
                ),
            )
            for incident in self.repository.all()
        ]
        return sorted(matches, key=lambda item: (-item.score, item.incident.id))[:limit]


class InMemoryIncidentRepository:
    def __init__(self, incidents: Sequence[HistoricalIncident]) -> None:
        self.incidents = tuple(incidents)

    def all(self) -> Sequence[HistoricalIncident]:
        return self.incidents


INCIDENTS = (
    HistoricalIncident("INC-001", "atlas-crm", "CRM integration", "Production API credentials were missing at connector build start.", "Customer security approval was not included in the launch critical path.", "The team used a customer-approved sandbox credential for contract tests while security completed production access review.", "Independent contract tests completed; production cutover remained gated until credentials were validated.", ("CRM", "REST API", "OAuth 2.0"), "Atlas closeout / EVT-214", date(2025, 3, 14)),
    HistoricalIncident("INC-002", "borealis-crm", "CRM integration", "CRM sync failed after deployment with repeated 401 responses.", "The OAuth audience differed between sandbox and production tenants.", "Integration engineering corrected the audience configuration and added a production-token validation checklist.", "Authentication was restored without changing task estimates.", ("Salesforce", "OAuth 2.0", "REST API"), "Borealis incident review / IR-88", date(2025, 6, 2)),
    HistoricalIncident("INC-003", "cobalt-migration", "Data migration", "Customer and source-system fields produced duplicate account records.", "The mapping workbook lacked a stable external identifier.", "The team added an identifier reconciliation workshop and a dry-run duplicate report.", "The second migration rehearsal met the agreed quality threshold.", ("PostgreSQL", "CSV", "ETL"), "Cobalt migration log / MIG-42", date(2025, 1, 29)),
    HistoricalIncident("INC-004", "delta-onboarding", "ERP onboarding", "Configuration sign-off was delayed by two review cycles.", "Customer approvers were not named and feedback arrived asynchronously.", "A single accountable approver and a 48-hour consolidated review window were agreed.", "Approval lead time became predictable; no acceleration metric was recorded.", ("ERP", "Workflow configuration"), "Delta steering notes / ST-17", date(2024, 11, 18)),
    HistoricalIncident("INC-005", "ember-rollout", "Multi-region launch", "Two launch workstreams competed for the same integration engineer.", "The resource plan assumed parallel availability for a shared specialist.", "Nondependent validation moved earlier and regional connector work was serialized.", "The revised schedule removed the resource collision.", ("REST API", "Regional deployment"), "Ember resource review / RR-09", date(2025, 8, 8)),
    HistoricalIncident("INC-006", "forge-crm", "CRM integration", "Integration testing accumulated behind one end-to-end test environment.", "Test data setup and environment validation were coupled to connector completion.", "QA prepared test data and validation scripts before the connector handoff.", "Testing began immediately after the build became available.", ("HubSpot", "REST API", "Playwright"), "Forge test retrospective / QA-31", date(2025, 4, 21)),
    HistoricalIncident("INC-007", "garnet-sso", "SSO rollout", "Pilot users were redirected in a login loop.", "The identity-provider ACS URL used the staging hostname.", "The ACS URL and entity ID were validated against a signed configuration checklist.", "Pilot authentication succeeded after configuration correction.", ("SAML 2.0", "Okta", "SSO"), "Garnet auth incident / AUTH-73", date(2025, 7, 10)),
    HistoricalIncident("INC-008", "harbor-sso", "SSO rollout", "SSO testing could not start because certificate ownership was unclear.", "No customer owner had been assigned to rotate and share the signing certificate.", "The customer named an identity owner and documented certificate exchange steps.", "Testing resumed after the certificate was securely delivered.", ("SAML 2.0", "Azure AD", "X.509"), "Harbor project event / EVT-301", date(2025, 9, 3)),
    HistoricalIncident("INC-009", "ion-data", "Data migration", "A mapping change late in UAT invalidated completed test cases.", "Business terminology differed between the mapping workbook and acceptance criteria.", "The team versioned the mapping specification and linked each field to acceptance tests.", "Subsequent changes were traceable and scoped before approval.", ("ETL", "Data mapping", "UAT"), "Ion lessons register / LES-12", date(2025, 2, 6)),
    HistoricalIncident("INC-010", "juno-api", "API implementation", "Customer firewall rules blocked callback delivery.", "Required egress addresses were absent from the readiness checklist.", "Network prerequisites were added to discovery and callbacks were tested with a diagnostic endpoint.", "Connectivity was verified before functional retesting.", ("Webhooks", "Firewall", "REST API"), "Juno connectivity review / NET-25", date(2024, 12, 9)),
    HistoricalIncident("INC-011", "kepler-erp", "ERP onboarding", "UAT completion slipped because all scenarios required one finance approver.", "The test plan concentrated sign-off authority without backup coverage.", "Approval was delegated by scenario and a final consolidated decision remained with finance leadership.", "Review work proceeded in parallel while preserving final accountability.", ("ERP", "UAT", "Approval workflow"), "Kepler UAT retrospective / UAT-64", date(2025, 5, 27)),
    HistoricalIncident("INC-012", "lumen-crm", "CRM integration", "Connector deployment exposed inconsistent picklist values.", "CRM metadata changed after the original field mapping export.", "The implementation added a metadata refresh check before build and before cutover.", "The corrected mapping passed the repeated integration test suite.", ("Dynamics 365", "CRM", "Data mapping"), "Lumen defect record / DEF-119", date(2025, 10, 16)),
    HistoricalIncident("INC-013", "synthetic-health-erp", "ERP onboarding", "Migration reconciliation failed because legacy patient and facility identifiers were inconsistent.", "Multiple source systems reused local identifiers without a governed crosswalk.", "Qualified data engineers created a versioned identifier crosswalk, remediated exceptions, and verified a sample before the next dry run.", "The dry run proceeded only after reconciliation verification; the case records no invented acceleration metric.", ("ERP", "Data reconciliation", "Identifier crosswalk"), "Synthetic portfolio case / ERP-ID-01", date(2025, 11, 6)),
    HistoricalIncident("INC-014", "synthetic-batch-migration", "Data migration", "A controlled migration rehearsal could not process the required volume inside the cutover window.", "Batch partitioning serialized work and concentrated processing on one qualified engineer.", "The team benchmarked explicit batch configurations and assigned an available qualified engineer to independent tuning work before another rehearsal.", "The next schedule was based on measured rehearsal output; no unmeasured throughput improvement was claimed.", ("ETL", "Batch processing", "Performance benchmark"), "Synthetic portfolio case / MIG-PERF-02", date(2025, 12, 1)),
    HistoricalIncident("INC-015", "synthetic-saml-rollout", "SSO rollout", "Pilot SSO failed after an identity-provider metadata and signing-certificate mismatch.", "Entity identifiers, endpoints, and certificate ownership were validated in separate uncoordinated steps.", "Identity and security specialists validated signed metadata and certificate chain before mandatory approval, then used staged UAT cohorts for phased rollout.", "The pilot resumed after security approval; mandatory validation was not bypassed.", ("SAML 2.0", "X.509", "Security approval", "Phased rollout"), "Synthetic portfolio case / SSO-VAL-03", date(2026, 1, 12)),
    HistoricalIncident("INC-016", "synthetic-retail-regions", "Multi-region launch", "Two regional launches competed for one integration engineer and one QA specialist.", "The portfolio plan treated shared specialists as if they had parallel capacity.", "A qualified regional engineer took one independent configuration stream and launches were phased to preserve QA capacity.", "One region moved earlier while the program retained explicit cross-region stabilization and resource trade-offs.", ("Regional deployment", "Resource capacity", "Phased launch"), "Synthetic portfolio case / REGION-CAP-04", date(2026, 2, 9)),
    HistoricalIncident("INC-017", "synthetic-banking-api", "Banking API integration", "A critical banking integration engineer became unavailable during connector delivery.", "The plan concentrated partner API knowledge with one engineer and omitted handoff effort.", "A qualified backup engineer accepted the connector with explicit handoff time while independent endpoint mapping moved to API support.", "Work resumed earlier without shortening delivery effort or bypassing banking security validation.", ("Banking API", "Resource availability", "Handoff"), "Synthetic portfolio case / BANK-API-05", date(2026, 3, 3)),
    HistoricalIncident("INC-018", "synthetic-logistics-data", "Data migration", "Validation found a material volume of invalid logistics records across independent data batches.", "Cleanup and repeat validation were serialized through one data engineer and one analyst.", "Independent batches were remediated by qualified data engineers in parallel and retained a shared quality gate before rehearsal.", "Rehearsal proceeded only after both batch remediation results passed validation.", ("Data migration", "Data quality", "Parallel remediation"), "Synthetic portfolio case / DATA-QUALITY-06", date(2026, 3, 17)),
    HistoricalIncident("INC-019", "synthetic-enterprise-sso", "Enterprise SSO", "UAT exposed a critical authentication defect while directory hardening was still required.", "Defect remediation and hardening competed for the lead identity engineer.", "A second qualified identity engineer remediated the defect while mandatory authentication retest and security regression remained unchanged.", "Identity work ran in parallel; launch remained gated by completed security validation.", ("Enterprise SSO", "Authentication defect", "Security regression"), "Synthetic portfolio case / SSO-DEFECT-07", date(2026, 4, 7)),
    HistoricalIncident("INC-020", "synthetic-commerce-scope", "Multi-region rollout", "A customer added a region shortly before the original regional launch commitment.", "Expanded scope was initially mixed with the original commitment and shared specialist capacity.", "The program separated original-scope and expanded-scope milestones, phased commitments, and assigned qualified regional specialists to added work.", "Original regions retained a visible commitment while expanded completion remained separately governed.", ("Multi-region rollout", "Scope change", "Phased launch"), "Synthetic portfolio case / SCOPE-REGION-08", date(2026, 4, 21)),
    HistoricalIncident("INC-021", "synthetic-analytics-qa", "Analytics platform deployment", "Platform, data, and regression validation competed for one analytics QA specialist.", "The resource plan treated distinct qualified validation work as one serial queue.", "Eligible data and security validation moved to available qualified specialists while end-to-end regression retained its dependencies.", "The deterministic schedule exposed the capacity gain without reducing test duration.", ("Analytics platform", "QA capacity", "Resource contention"), "Synthetic portfolio case / ANALYTICS-QA-09", date(2026, 5, 5)),
)


DEFAULT_CONTEXT_SERVICE = HistoricalContextService(
    InMemoryIncidentRepository(INCIDENTS), DeterministicEmbeddingProvider()
)

