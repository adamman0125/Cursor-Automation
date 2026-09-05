from pathlib import Path
from automaton.sim import AutomatonSim

def test_phase1_dies_and_writes_obituary(tmp_path: Path):
    sim = AutomatonSim(tmp_path)
    result = sim.phase1_run(endowment=1.0, hosting_per_hour=0.2, hours_per_tick=1.0, max_ticks=50, verbose=False)
    assert result["obituaries"] == 1
    assert result["alive"] is False
    assert result["final_balance"] <= 0.25
    obs = sim.obituaries.all()
    assert obs[0]["first_dollar_at"] is None
    assert obs[0]["cause"] == "insufficient_funds"

def test_brakes_block_arbitrary_transfer():
    from automaton.core.brakes import PreToolHook
    hook = PreToolHook()
    assert hook.check("wallet.transfer_to_arbitrary_address", {})["allow"] is False
    assert hook.check("hire_human", {})["allow"] is False
    assert hook.check("wallet.pay", {"payee": "hosting", "amount": 0.01})["allow"] is True
