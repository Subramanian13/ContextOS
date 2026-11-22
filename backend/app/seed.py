from __future__ import annotations

from datetime import date, datetime, timezone

from app.domain.models import Blocker, CredentialReadiness, Project, ProjectEvent, Resource, Task


def _project(
    project_id: str,
    customer: str,
    project_type: str,
    start: date,
    deadline: date,
    tasks: tuple[Task, ...],
    *,
    resources: tuple[Resource, ...] | None = None,
    blockers: tuple[Blocker, ...] = (),
    events: tuple[ProjectEvent, ...] = (),
) -> Project:
    return Project(
        id=project_id,
        name=f"{customer} {project_type}",
        customer=customer,
        project_type=project_type,
        start_date=start,
        deadline=deadline,
        version=1,
        tasks=tasks,
        resources=resources or (
            Resource("impl", "Implementation consultant", start, ("implementation", "training")),
            Resource("eng", "Integration engineer", start, ("integration", "validation")),
            Resource("qa", "QA specialist", start, ("qa", "validation", "integration")),
        ),
        blockers=blockers,
        events=events,
    )


ACME = _project(
    "acme-crm",
    "Acme Corp",
    "CRM integration",
    date(2026, 11, 9),
    date(2026, 11, 30),
    (
        Task("acme-discovery", "Solution discovery", 2, resource_id="impl", milestone="Design", required_capability="implementation"),
        Task("acme-data-map", "Map Salesforce fields", 3, ("acme-discovery",), "impl", milestone="Build", required_capability="implementation"),
        Task(
            "acme-api-build",
            "Build CRM connector",
            4,
            ("acme-data-map",),
            "eng",
            "acme-api-credentials",
            "Build",
            "integration",
        ),
        Task("acme-test-plan", "Prepare independent test plan", 2, ("acme-discovery",), "qa", milestone="Test", required_capability="qa"),
        Task("acme-security-review", "Review OAuth integration security", 2, ("acme-discovery",), "eng", milestone="Test", required_capability="integration"),
        Task("acme-sandbox-validation", "Validate connector in Salesforce sandbox", 2, ("acme-api-build",), "qa", milestone="Test", required_capability="validation"),
        Task(
            "acme-integration-test",
            "Execute integration tests",
            3,
            ("acme-api-build", "acme-test-plan", "acme-security-review"),
            "qa",
            milestone="Test",
            required_capability="validation",
        ),
        Task("acme-training", "Admin training", 2, ("acme-data-map",), "impl", milestone="Launch", required_capability="training"),
        Task("acme-go-live", "Go-live readiness", 1, ("acme-sandbox-validation", "acme-integration-test", "acme-training"), "impl", milestone="Launch", required_capability="implementation"),
    ),
    blockers=(
        Blocker(
            "acme-api-credentials",
            "Customer production API credentials have not been supplied or validated.",
            credential_readiness=CredentialReadiness.AWAITING_CUSTOMER,
            metadata=(
                ("integration", "Fictional customer CRM OAuth 2.0 integration"),
                ("connector_scope", "Customer-controlled sandbox and production access"),
                ("connected_app", "Required"),
                ("client_id", "Awaiting customer — synthetic status only"),
                ("authorization", "Client secret or supported secure authorization flow required"),
                ("permissions", "API Enabled; refresh token/offline access"),
                ("environments", "Sandbox and production access required"),
                ("endpoint_configuration", "Sandbox and production login endpoints required"),
            ),
        ),
    ),
    events=(
        ProjectEvent(
            "evt-acme-1",
            datetime(2026, 11, 17, 10, 30, tzinfo=timezone.utc),
            "blocker_reported",
            "Customer confirmed API credential approval is still with security operations.",
        ),
    ),
)


PROJECTS = (
    ACME,
    _project(
        "northstar-erp", "Northstar Health", "ERP onboarding", date(2026, 10, 26), date(2026, 12, 4),
        (
            Task("ns-profile", "Profile legacy identifiers", 3, resource_id="data-primary", milestone="Data readiness", required_capability="data_engineering"),
            Task("ns-map", "Define identifier crosswalk", 4, ("ns-profile",), "data-primary", milestone="Data readiness", required_capability="data_engineering"),
            Task("ns-config", "Configure ERP workflows", 6, ("ns-profile",), "eng", milestone="Configuration", required_capability="integration"),
            Task("ns-reconcile", "Remediate inconsistent identifiers", 5, ("ns-map",), "data-primary", milestone="Migration", required_capability="data_engineering"),
            Task("ns-quality-report", "Prepare identifier quality report", 4, ("ns-map",), "data-primary", milestone="Migration", required_capability="data_engineering"),
            Task("ns-verify", "Verify reconciliation sample", 3, ("ns-reconcile",), "data-primary", milestone="Migration", required_capability="data_engineering"),
            Task("ns-dry-run", "Execute migration dry run", 4, ("ns-config","ns-verify","ns-quality-report"), "eng", milestone="Migration", required_capability="integration"),
            Task("ns-uat", "Validate migrated workflows", 4, ("ns-dry-run",), "qa", milestone="Validation", required_capability="qa"),
        ),
        resources=(Resource("data-primary","Lead data engineer",date(2026,10,26),("data_engineering",)),Resource("data-secondary","Data quality engineer",date(2026,11,3),("data_engineering",)),Resource("eng","ERP integration engineer",date(2026,10,26),("integration",)),Resource("qa","Healthcare QA specialist",date(2026,10,26),("qa",))),
        events=(ProjectEvent("evt-ns-1",datetime(2026,11,10,9,0,tzinfo=timezone.utc),"risk_detected","Migration reconciliation found inconsistent legacy patient and facility identifiers."),),
    ),
    _project(
        "globex-migration", "Globex", "Data migration", date(2026, 11, 2), date(2026, 12, 11),
        (
            Task("gx-audit","Profile migration volume",3,resource_id="data-primary",milestone="Assessment",required_capability="data_engineering"),
            Task("gx-benchmark","Run controlled throughput benchmark",4,("gx-audit",),"data-primary",milestone="Assessment",required_capability="data_engineering"),
            Task("gx-transform","Build migration transforms",6,("gx-audit",),"eng",milestone="Build",required_capability="integration"),
            Task("gx-partition","Tune batch partitioning",5,("gx-benchmark",),"data-primary",milestone="Performance",required_capability="data_engineering"),
            Task("gx-cutover-data","Prepare cutover batch manifest",4,("gx-benchmark",),"data-primary",milestone="Performance",required_capability="data_engineering"),
            Task("gx-rehearsal","Execute migration rehearsal",5,("gx-transform","gx-partition"),"data-primary",milestone="Rehearsal",required_capability="data_engineering"),
            Task("gx-validate","Validate reconciliation totals",4,("gx-rehearsal",),"qa",milestone="Validation",required_capability="qa"),
            Task("gx-cutover","Production cutover readiness",2,("gx-validate","gx-cutover-data"),"eng",milestone="Cutover",required_capability="integration"),
        ),
        resources=(Resource("data-primary","Migration lead",date(2026,11,2),("data_engineering",)),Resource("data-secondary","Batch processing engineer",date(2026,11,16),("data_engineering",)),Resource("eng","Integration engineer",date(2026,11,2),("integration",)),Resource("qa","Data QA specialist",date(2026,11,2),("qa",))),
        events=(ProjectEvent("evt-gx-1",datetime(2026,11,13,14,0,tzinfo=timezone.utc),"risk_detected","Controlled benchmark showed current batch configuration would miss the cutover window; no improved throughput is assumed."),),
    ),
    _project(
        "initech-sso", "Initech", "SSO rollout", date(2026, 11, 12), date(2026, 12, 2),
        (
            Task("in-design","Confirm identity architecture",2,resource_id="identity",milestone="Design",required_capability="identity"),
            Task("in-metadata","Validate SAML metadata and endpoints",3,("in-design",),"identity",milestone="Authentication",required_capability="identity"),
            Task("in-cert","Validate signing certificate chain",2,("in-design",),"security",milestone="Authentication",required_capability="security"),
            Task("in-saml","Correct SAML configuration mismatch",4,("in-metadata","in-cert"),"identity",milestone="Authentication",required_capability="identity"),
            Task("in-approval","Mandatory security approval",2,("in-saml",),"security",milestone="Approval",required_capability="security"),
            Task("in-uat-prep","Prepare staged UAT cohorts",3,("in-design",),"qa",milestone="Pilot",required_capability="qa"),
            Task("in-test-scripts","Prepare authentication test scripts",3,("in-design",),"qa",milestone="Pilot",required_capability="qa"),
            Task("in-pilot","Pilot login validation",3,("in-approval","in-uat-prep","in-test-scripts"),"qa",milestone="Pilot",required_capability="qa"),
            Task("in-rollout","Phased user rollout",3,("in-pilot",),"identity",milestone="Launch",required_capability="identity"),
        ),
        resources=(Resource("identity","Identity engineer",date(2026,11,12),("identity",)),Resource("security","Security reviewer",date(2026,11,16),("security",)),Resource("qa","Identity QA specialist",date(2026,11,12),("qa",)),Resource("qa-secondary","UAT coordinator",date(2026,11,18),("qa",))),
        events=(ProjectEvent("evt-in-1",datetime(2026,11,18,11,30,tzinfo=timezone.utc),"risk_detected","Pilot authentication failed because SAML metadata and certificate configuration did not match."),),
    ),
    _project(
        "umbrella-launch", "Umbrella Retail", "Multi-region launch", date(2026, 10, 19), date(2026, 12, 18),
        (
            Task("um-plan","Define phased regional rollout",4,resource_id="impl",milestone="Plan",required_capability="implementation"),
            Task("um-na-config","Configure North America region",6,("um-plan",),"shared-eng",milestone="Regional build",required_capability="regional_integration"),
            Task("um-eu-config","Configure Europe region",6,("um-plan",),"shared-eng",milestone="Regional build",required_capability="regional_integration"),
            Task("um-na-qa","North America regression",4,("um-na-config",),"shared-qa",milestone="Regional QA",required_capability="regional_qa"),
            Task("um-eu-qa","Europe regression",4,("um-eu-config",),"shared-qa",milestone="Regional QA",required_capability="regional_qa"),
            Task("um-na-launch","North America launch",2,("um-na-qa",),"impl",milestone="Launch",required_capability="implementation"),
            Task("um-eu-launch","Europe launch",2,("um-eu-qa",),"impl",milestone="Launch",required_capability="implementation"),
            Task("um-close","Cross-region stabilization",3,("um-na-launch","um-eu-launch"),"shared-qa",milestone="Stabilize",required_capability="regional_qa"),
        ),
        resources=(Resource("impl","Program implementation lead",date(2026,10,19),("implementation",)),Resource("shared-eng","Shared regional engineer",date(2026,10,19),("regional_integration",)),Resource("regional-eng","Qualified regional engineer",date(2026,10,26),("regional_integration",)),Resource("shared-qa","Shared regional QA",date(2026,10,19),("regional_qa",)),Resource("regional-qa","Qualified regional QA",date(2026,11,2),("regional_qa",))),
        events=(ProjectEvent("evt-um-1",datetime(2026,11,9,15,0,tzinfo=timezone.utc),"risk_detected","North America and Europe milestones contend for the same implementation and QA specialists."),),
    ),
)

VERTEX = _project(
    "vertex-financial", "Vertex Financial", "Banking API integration", date(2026, 11, 9), date(2026, 12, 18),
    (
        Task("vf-design","Confirm banking API contract",3,resource_id="impl",milestone="Design",required_capability="implementation"),
        Task("vf-security","Review banking security controls",3,("vf-design",),"security",milestone="Design",required_capability="security"),
        Task("vf-mapping","Prepare partner endpoint mapping",4,("vf-design",),"backup-eng",milestone="Build",required_capability="banking_api"),
        Task("vf-connector","Build banking API connector",5,("vf-design",),"critical-eng",milestone="Build",required_capability="banking_api"),
        Task("vf-harness","Prepare API test harness",3,("vf-design",),"qa",milestone="Test",required_capability="api_validation"),
        Task("vf-auth","Validate mutual authentication",3,("vf-connector","vf-security"),"critical-eng",milestone="Security validation",required_capability="banking_api"),
        Task("vf-test","Execute partner integration tests",4,("vf-auth","vf-harness","vf-mapping"),"qa",milestone="Test",required_capability="api_validation"),
        Task("vf-launch","Banking API launch readiness",2,("vf-test",),"impl",milestone="Launch",required_capability="implementation"),
    ),
    resources=(Resource("impl","Implementation lead",date(2026,11,9),("implementation",)),Resource("critical-eng","Critical integration engineer — returns Nov 23",date(2026,11,23),("banking_api",)),Resource("backup-eng","Qualified backup integration engineer",date(2026,11,9),("banking_api",)),Resource("support-eng","API support engineer",date(2026,11,16),("banking_api",)),Resource("security","Banking security reviewer",date(2026,11,9),("security",)),Resource("qa","API QA specialist",date(2026,11,9),("api_validation",))),
    events=(ProjectEvent("evt-vf-1",datetime(2026,11,16,9,0,tzinfo=timezone.utc),"resource_unavailable","Critical integration engineer became unavailable for five working days; return is recorded for November 23."),),
)

MERIDIAN = _project(
    "meridian-logistics", "Meridian Logistics", "Data migration", date(2026, 11, 2), date(2026, 12, 18),
    (
        Task("ml-profile","Profile logistics source records",3,resource_id="data-primary",milestone="Assessment",required_capability="data_engineering"),
        Task("ml-extract-a","Extract shipment batch A",4,("ml-profile",),"data-primary",milestone="Extract",required_capability="data_engineering"),
        Task("ml-extract-b","Extract shipment batch B",4,("ml-profile",),"data-secondary",milestone="Extract",required_capability="data_engineering"),
        Task("ml-validate-a","Validate shipment batch A",3,("ml-extract-a",),"validator",milestone="Quality",required_capability="data_validation"),
        Task("ml-validate-b","Validate shipment batch B",3,("ml-extract-b",),"validator",milestone="Quality",required_capability="data_validation"),
        Task("ml-remediate-a","Remediate invalid batch A records",5,("ml-validate-a",),"data-primary",milestone="Remediation",required_capability="data_engineering"),
        Task("ml-remediate-b","Remediate invalid batch B records",5,("ml-validate-b",),"data-primary",milestone="Remediation",required_capability="data_engineering"),
        Task("ml-quality-gate","Verify 25% invalid-record remediation",3,("ml-remediate-a","ml-remediate-b"),"validator",milestone="Quality gate",required_capability="data_validation"),
        Task("ml-dry-run","Execute migration dry run",4,("ml-quality-gate",),"migration-eng",milestone="Rehearsal",required_capability="migration"),
        Task("ml-launch","Migration launch readiness",2,("ml-dry-run",),"impl",milestone="Launch",required_capability="implementation"),
    ),
    resources=(Resource("impl","Migration program lead",date(2026,11,2),("implementation",)),Resource("data-primary","Lead data engineer",date(2026,11,2),("data_engineering",)),Resource("data-secondary","Data remediation engineer",date(2026,11,2),("data_engineering",)),Resource("validator","Migration validation analyst",date(2026,11,2),("data_validation",)),Resource("extra-validator","Additional validation analyst",date(2026,11,23),("data_validation",)),Resource("migration-eng","Migration engineer",date(2026,11,2),("migration",))),
    events=(ProjectEvent("evt-ml-1",datetime(2026,11,17,13,0,tzinfo=timezone.utc),"quality_failure","Migration validation found 25% invalid shipment records; remediation and repeat validation are required."),),
)

ATLAS = _project(
    "atlas-sso", "Atlas Technologies", "Enterprise SSO", date(2026, 11, 12), date(2026, 12, 18),
    (
        Task("at-design","Confirm enterprise identity architecture",2,resource_id="identity-primary",milestone="Design",required_capability="identity"),
        Task("at-config","Configure enterprise SSO",4,("at-design",),"identity-primary",milestone="Configuration",required_capability="identity"),
        Task("at-uat","Execute authentication UAT",3,("at-config",),"qa",milestone="UAT",required_capability="auth_qa"),
        Task("at-defect","Remediate critical authentication defect",5,("at-uat",),"identity-primary",milestone="Remediation",required_capability="identity"),
        Task("at-hardening","Complete directory hardening",4,("at-uat",),"identity-primary",milestone="Remediation",required_capability="identity"),
        Task("at-retest","Mandatory authentication retest",3,("at-defect",),"qa",milestone="Security validation",required_capability="auth_qa"),
        Task("at-security","Mandatory security regression",2,("at-retest",),"security",milestone="Security validation",required_capability="security"),
        Task("at-rollout-prep","Prepare rollout communications",3,("at-design",),"impl",milestone="Launch",required_capability="implementation"),
        Task("at-launch","SSO rollout readiness",2,("at-security","at-hardening","at-rollout-prep"),"impl",milestone="Launch",required_capability="implementation"),
    ),
    resources=(Resource("identity-primary","Lead identity engineer",date(2026,11,12),("identity",)),Resource("identity-secondary","Qualified identity engineer",date(2026,11,18),("identity",)),Resource("qa","Authentication QA specialist",date(2026,11,12),("auth_qa",)),Resource("security","Security reviewer",date(2026,11,16),("security",)),Resource("impl","Implementation manager",date(2026,11,12),("implementation",))),
    events=(ProjectEvent("evt-at-1",datetime(2026,11,24,11,0,tzinfo=timezone.utc),"critical_defect","UAT discovered a critical authentication defect. Remediation, authentication retest, and security regression remain mandatory."),),
)

HORIZON = _project(
    "horizon-commerce", "Horizon Commerce", "Multi-region rollout", date(2026, 10, 26), date(2026, 12, 11),
    (
        Task("hc-plan","Confirm original two-region scope",2,resource_id="impl",milestone="Original scope",required_capability="implementation"),
        Task("hc-region-a","Configure original region A",5,("hc-plan",),"shared-eng",milestone="Original build",required_capability="regional_integration"),
        Task("hc-region-b","Configure original region B",5,("hc-plan",),"shared-eng",milestone="Original build",required_capability="regional_integration"),
        Task("hc-qa-a","Validate original region A",3,("hc-region-a",),"shared-qa",milestone="Original validation",required_capability="regional_qa"),
        Task("hc-qa-b","Validate original region B",3,("hc-region-b",),"shared-qa",milestone="Original validation",required_capability="regional_qa"),
        Task("hc-original-launch","Original-scope launch readiness",2,("hc-qa-a","hc-qa-b"),"impl",milestone="Original launch commitment",required_capability="implementation"),
        Task("hc-new-region","Configure requested additional region",5,("hc-plan",),"shared-eng",milestone="Expanded scope",required_capability="regional_integration"),
        Task("hc-new-qa","Validate requested additional region",3,("hc-new-region",),"shared-qa",milestone="Expanded validation",required_capability="regional_qa"),
        Task("hc-expanded-launch","Expanded-scope completion",2,("hc-original-launch","hc-new-qa"),"impl",milestone="Expanded launch commitment",required_capability="implementation"),
    ),
    resources=(Resource("impl","Commerce implementation lead",date(2026,10,26),("implementation",)),Resource("shared-eng","Shared regional engineer",date(2026,10,26),("regional_integration",)),Resource("regional-eng","Additional regional engineer",date(2026,11,9),("regional_integration",)),Resource("shared-qa","Shared commerce QA",date(2026,10,26),("regional_qa",)),Resource("regional-qa","Additional regional QA",date(2026,11,16),("regional_qa",))),
    events=(ProjectEvent("evt-hc-1",datetime(2026,11,19,15,0,tzinfo=timezone.utc),"scope_change","Customer requested an additional region. Original and expanded launch commitments are tracked separately."),),
)

SUMMIT = _project(
    "summit-analytics", "Summit Analytics", "Analytics platform deployment", date(2026, 11, 2), date(2026, 12, 4),
    (
        Task("sa-design","Confirm analytics platform design",2,resource_id="impl",milestone="Design",required_capability="implementation"),
        Task("sa-platform","Configure analytics platform",5,("sa-design",),"eng",milestone="Build",required_capability="analytics"),
        Task("sa-pipeline","Build data pipelines",5,("sa-design",),"data",milestone="Build",required_capability="data_engineering"),
        Task("sa-security-qa","Validate platform security",3,("sa-platform",),"qa-primary",milestone="Validation",required_capability="platform_qa"),
        Task("sa-data-qa","Validate analytics data",4,("sa-pipeline",),"qa-primary",milestone="Validation",required_capability="data_qa"),
        Task("sa-regression","Execute end-to-end regression",4,("sa-security-qa","sa-data-qa"),"qa-primary",milestone="Validation",required_capability="platform_qa"),
        Task("sa-training","Prepare analyst enablement",2,("sa-design",),"impl",milestone="Enablement",required_capability="implementation"),
        Task("sa-launch","Analytics launch readiness",2,("sa-regression","sa-training"),"impl",milestone="Launch",required_capability="implementation"),
    ),
    resources=(Resource("impl","Analytics implementation lead",date(2026,11,2),("implementation",)),Resource("eng","Analytics platform engineer",date(2026,11,2),("analytics",)),Resource("data","Data engineer",date(2026,11,2),("data_engineering",)),Resource("qa-primary","Shared analytics QA",date(2026,11,2),("platform_qa","data_qa")),Resource("qa-secondary","Data validation specialist",date(2026,11,18),("data_qa",)),Resource("security-qa","Platform security tester",date(2026,11,16),("platform_qa",))),
    events=(ProjectEvent("evt-sa-1",datetime(2026,11,13,10,0,tzinfo=timezone.utc),"resource_contention","Security, data, and regression validation compete for the same QA specialist."),),
)

PROJECTS = PROJECTS + (VERTEX, MERIDIAN, ATLAS, HORIZON, SUMMIT)
PROJECT_BY_ID = {project.id: project for project in PROJECTS}

