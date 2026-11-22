from datetime import date

from app.historical import DEFAULT_CONTEXT_SERVICE
from app.recovery import RecoveryPlanningService
from app.recovery_profiles import PROFILES
from app.schemas import RecoveryScenarioRequest, TaskChangeRequest
from app.seed import PROJECTS
from app.service import compare_recovery_scenario


EXPECTED_EVIDENCE={"northstar-erp":"INC-013","globex-migration":"INC-014","initech-sso":"INC-015","umbrella-launch":"INC-016","vertex-financial":"INC-017","meridian-logistics":"INC-018","atlas-sso":"INC-019","horizon-commerce":"INC-020","summit-analytics":"INC-021"}


def comparison(project):
    profile=PROFILES[project.id]
    return compare_recovery_scenario(project,RecoveryScenarioRequest(name=profile["title"],unblock_dates={profile["date_blocker_id"]:date(2026,11,23)} if profile.get("date_blocker_id") else {},task_changes=[TaskChangeRequest(**item) for item in profile["task_changes"]],assumptions=profile["assumptions"]))


def test_all_ten_profiles_are_scheduler_validated() -> None:
    results={project.id:comparison(project) for project in PROJECTS}
    assert set(results)==set(PROFILES)
    assert results["acme-crm"]["working_days_saved"]==2
    assert results["northstar-erp"]["working_days_saved"]==4
    assert results["globex-migration"]["working_days_saved"]==4
    assert results["umbrella-launch"]["working_days_saved"]==4
    assert results["initech-sso"]["working_days_saved"]==0
    assert "does not improve" in results["initech-sso"]["explanation"].lower()
    assert results["vertex-financial"]["working_days_saved"] == 2
    assert results["meridian-logistics"]["working_days_saved"] == 2
    assert results["atlas-sso"]["working_days_saved"] == 0
    assert results["horizon-commerce"]["working_days_saved"] == 2
    assert results["summit-analytics"]["working_days_saved"] == 1


def test_each_non_acme_scenario_retrieves_its_synthetic_evidence() -> None:
    service=RecoveryPlanningService(DEFAULT_CONTEXT_SERVICE,planner=None)  # type: ignore[arg-type]
    for project in PROJECTS[1:]:
        ids={item.incident.id for item in service.evidence_for(project)}
        assert EXPECTED_EVIDENCE[project.id] in ids


def test_profiles_preserve_required_dependencies_and_qualifications() -> None:
    for project in PROJECTS:
        result=comparison(project)
        assert result["proposed"].forecast_status in {"feasible","conditional"}
        assert not result["proposed"].unscheduled_task_ids


def test_new_projects_offer_distinct_deterministic_strategy_outcomes() -> None:
    expected={
        "vertex-financial":{"wait":0,"reassign":2,"redistribute":5},
        "meridian-logistics":{"sequential":0,"parallel":2,"validation-capacity":-3},
        "atlas-sso":{"mandatory-fix":0,"prepare":0,"reassign":0},
        "horizon-commerce":{"expanded-first":-2,"phased":0,"specialists":2},
        "summit-analytics":{"current":0,"data-capacity":-2,"security-capacity":1},
    }
    projects={project.id:project for project in PROJECTS}
    for project_id,outcomes in expected.items():
        profile=PROFILES[project_id]
        for strategy in profile["strategies"]:
            result=compare_recovery_scenario(projects[project_id],RecoveryScenarioRequest(name=strategy["title"],task_changes=[TaskChangeRequest(**item) for item in strategy["task_changes"]],assumptions=profile["assumptions"]))
            assert result["working_days_saved"]==outcomes[strategy["id"]]


def test_original_five_project_seed_contract_is_unchanged() -> None:
    expected={
        "acme-crm":("2026-11-30",9),"northstar-erp":("2026-12-04",8),
        "globex-migration":("2026-12-11",8),"initech-sso":("2026-12-02",9),
        "umbrella-launch":("2026-12-18",8),
    }
    assert len(PROJECTS)==10
    for project in PROJECTS[:5]:
        deadline,count=expected[project.id]
        assert project.deadline.isoformat()==deadline
        assert len(project.tasks)==count
