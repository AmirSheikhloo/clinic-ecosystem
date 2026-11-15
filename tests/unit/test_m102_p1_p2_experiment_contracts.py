"""Static contracts for the M1-02 P1/P2 experimental physical probes."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from experiments.m102_hmac_physical.p1_staged_columns import (
    P1_GEN2_INDEX,
    P1_GEN2_INDEX_DDL,
    P1_GEN3_INDEX_DDL,
)
from experiments.m102_hmac_physical.p2_generation_sidecar import (
    P2_CANDIDATE_INDEX_DDL,
    P2_TABLE,
)
from experiments.m102_hmac_physical.synthetic_hmac import synthetic_lookup_hmac

REPO = Path(__file__).resolve().parents[2]


def test_synthetic_hmac_domain_separated_and_version_sensitive() -> None:
    tid = UUID("01900000-0000-7000-8000-0000000000aa")
    a = synthetic_lookup_hmac(
        tenant_id=tid,
        id_type="IR_NATIONAL_ID",
        issuing_country_or_authority="IR",
        normalized_identifier="0012345678",
        hmac_key_version=1,
    )
    b = synthetic_lookup_hmac(
        tenant_id=tid,
        id_type="IR_NATIONAL_ID",
        issuing_country_or_authority="IR",
        normalized_identifier="0012345678",
        hmac_key_version=2,
    )
    assert len(a) == 32 and len(b) == 32
    assert a != b


def test_p1_phase6_index_targets_gen2_not_lookup_hmac_next() -> None:
    assert "exp_lookup_hmac_gen2" in P1_GEN2_INDEX_DDL
    assert "lookup_hmac_next" not in P1_GEN2_INDEX_DDL
    assert "CONCURRENTLY" in P1_GEN2_INDEX_DDL
    assert P1_GEN2_INDEX in P1_GEN2_INDEX_DDL
    assert "exp_lookup_hmac_gen3" in P1_GEN3_INDEX_DDL


def test_p2_candidate_index_is_status_scoped_and_non_tp0002_next() -> None:
    assert P2_TABLE in P2_CANDIDATE_INDEX_DDL
    assert "generation_status = 'CANDIDATE'" in P2_CANDIDATE_INDEX_DDL
    assert "lookup_hmac_next" not in P2_CANDIDATE_INDEX_DDL
    assert "CONCURRENTLY" in P2_CANDIDATE_INDEX_DDL


def test_experiments_are_not_official_alembic_revisions() -> None:
    versions = REPO / "migrations" / "tenant_plane" / "versions"
    assert not list(versions.glob("*exp*"))
    assert not list(versions.glob("tp0008*"))
    exp_root = REPO / "experiments" / "m102_hmac_physical"
    assert exp_root.is_dir()
