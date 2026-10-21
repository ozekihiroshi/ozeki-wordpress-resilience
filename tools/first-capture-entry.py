"""Mandatory fresh admission at the initial-capture entry; no S3 or signing."""
import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('first_admission',Path(__file__).with_name('first-capture-readiness.py'));gate=importlib.util.module_from_spec(s);s.loader.exec_module(gate)
api=gate.pre.capture

def capture_from_files(*, profile, inventory, report, health, review, workspace, backend):
    """Inputs must be operator-owned protected paths; this is not an authentication boundary.

    Low-level capture remains reusable for existing labs. Initial onboarding must use
    this entry, which cannot accept a previously saved eligibility result.
    """
    config=gate.pre.read_json(profile)
    pin=api.digest(config)
    def recheck(expected):
        check_admission(profile=profile,inventory=inventory,report=report,health=health,
                        review=review,workspace=workspace,expected_config_hash=pin)
    return api.capture(config,pin,backend,workspace,pre_capture_check=recheck)


def check_admission(*, profile, inventory, report, health, review, workspace, expected_config_hash):
    """Fresh read, also used immediately before daily publication."""
    try:
        current=gate.pre.read_json(profile)
        api.require(api.digest(current)==expected_config_hash,'admission_configuration_changed')
        decision=gate.evaluate(current,gate.pre.read_json(inventory),workspace,
                              gate.pre.read_json(report),gate.pre.read_json(health),gate.pre.read_json(review))
        api.require(decision['state']=='eligible_for_dedicated_capture_review',
                    'admission_blocked:'+','.join(decision['blockers']))
        return decision
    except (OSError,ValueError,TypeError,RecursionError) as exc:
        if isinstance(exc,api.Rejected):raise
        raise api.Rejected('admission_input_unreadable_or_invalid') from None
