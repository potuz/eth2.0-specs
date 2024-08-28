from eth2spec.test.context import (
    spec_state_test,
    with_eip7732_and_later,
    with_test_suite_name,
)


@with_test_suite_name("BeaconState")
@with_eip7732_and_later
@spec_state_test
def test_execution_merkle_proof(spec, state):
    yield "object", state
    gindex = spec.EXECUTION_PAYLOAD_GINDEX_EIP7732
    branch = spec.compute_merkle_proof(state, gindex)
    yield "proof", {
        "leaf": "0x" + state.latest_execution_payload_root.hash_tree_root().hex(),
        "leaf_index": gindex,
        "branch": ['0x' + root.hex() for root in branch]
    }
    assert spec.is_valid_merkle_branch(
        leaf=state.latest_execution_payload_root.hash_tree_root(),
        branch=branch,
        depth=spec.floorlog2(gindex),
        index=spec.get_subtree_index(gindex),
        root=state.hash_tree_root(),
    )
