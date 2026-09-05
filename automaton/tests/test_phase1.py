from pathlib import Path

from automaton.core.brakes import PreToolHook
from automaton.phase1 import expected_death_ticks, run_phase1


def test_expected_death_math():
    # $2 endowment, $0.25 floor, $0.05/h -> usable $1.75 -> 35 ticks
    assert expected_death_ticks(2.0, 0.05) == 35


def test_phase1_dies_on_time(tmp_path: Path):
    report = run_phase1(
        tmp_path,
        endowment=2.0,
        hosting_per_hour=0.05,
        verbose=False,
    )
    assert report["passed"] is True
    assert report["actual_death_ticks"] == 35
    assert report["obituaries"] == 1
    assert report["alive"] is False
    assert report["revenue_usd"] == 0
    assert report["obituary"]["cause"] == "insufficient_funds"
    assert report["obituary"]["first_dollar_at"] is None


def test_phase1_fast_burn(tmp_path: Path):
    report = run_phase1(
        tmp_path,
        endowment=1.0,
        hosting_per_hour=0.25,
        verbose=False,
    )
    # usable = 0.75 / 0.25 = 3 ticks
    assert report["passed"] is True
    assert report["actual_death_ticks"] == 3


def test_brakes_block_arbitrary_transfer():
    hook = PreToolHook()
    assert hook.check("wallet.transfer_to_arbitrary_address", {})["allow"] is False
    assert hook.check("hire_human", {})["allow"] is False
    assert hook.check("wallet.pay", {"payee": "hosting", "amount": 0.01})["allow"] is True
