from eth2spec.test.helpers.constants import (
    CAPELLA, DENEB, ELECTRA, EIP7732
)
from eth2spec.test.helpers.execution_payload import (
    build_empty_execution_payload,
    build_empty_signed_execution_payload_envelope,
    build_empty_signed_execution_payload_header,
)
from eth2spec.test.helpers.fork_transition import (
    transition_across_forks,
)
from eth2spec.test.helpers.forks import (
    is_post_bellatrix, is_post_capella, is_post_deneb, is_post_electra, is_post_eip7732
)
from eth2spec.test.helpers.sync_committee import (
    compute_aggregate_sync_committee_signature,
    compute_committee_indices,
)
from math import floor


def latest_finalized_root_gindex(spec):
    if hasattr(spec, 'FINALIZED_ROOT_GINDEX_ELECTRA'):
        return spec.FINALIZED_ROOT_GINDEX_ELECTRA
    return spec.FINALIZED_ROOT_GINDEX


def latest_current_sync_committee_gindex(spec):
    if hasattr(spec, 'CURRENT_SYNC_COMMITTEE_GINDEX_ELECTRA'):
        return spec.CURRENT_SYNC_COMMITTEE_GINDEX_ELECTRA
    return spec.CURRENT_SYNC_COMMITTEE_GINDEX


def latest_next_sync_committee_gindex(spec):
    if hasattr(spec, 'NEXT_SYNC_COMMITTEE_GINDEX_ELECTRA'):
        return spec.NEXT_SYNC_COMMITTEE_GINDEX_ELECTRA
    return spec.NEXT_SYNC_COMMITTEE_GINDEX


def compute_start_slot_at_sync_committee_period(spec, sync_committee_period):
    return spec.compute_start_slot_at_epoch(sync_committee_period * spec.EPOCHS_PER_SYNC_COMMITTEE_PERIOD)


def compute_start_slot_at_next_sync_committee_period(spec, state):
    sync_committee_period = spec.compute_sync_committee_period_at_slot(state.slot)
    return compute_start_slot_at_sync_committee_period(spec, sync_committee_period + 1)


def apply_payload_and_transition(spec, state, latest_payload=None, to_slot=None, phases=None):
    # The test framework currently is very restricted regarding ePBS.
    # Once execution payloads are properly routed through the test framework,
    # the logic here should be simplified to avoid assumptions about internals.

    # The `initialize_beacon_state_from_eth1` function is implemented incorrectly
    # and does not properly initialize `latest_execution_payload_root` due to
    # confusion of old `ExecutionPayloadHeader` summary semantics and the new bid concept.
    # Until that is fixed, we have to patch the state to be correct
    if is_post_eip7732(spec) and state.slot == spec.GENESIS_SLOT:
        assert latest_payload is not None
        state = state.copy()
        state.latest_execution_payload_root = latest_payload.hash_tree_root()

    # Reveal and apply latest payload
    if is_post_eip7732(spec):
        assert latest_payload is not None
        if (
            spec.compute_timestamp_at_slot(state, state.slot) == latest_payload.timestamp
            and state.slot != spec.GENESIS_SLOT
        ):
            signed_envelope = build_empty_signed_execution_payload_envelope(spec, latest_payload, state)
            spec.process_execution_payload(state, signed_envelope, spec.EXECUTION_ENGINE)
        assert state.latest_execution_payload_root == latest_payload.hash_tree_root()
    elif latest_payload is not None:
        if latest_payload == spec.ExecutionPayload():
            assert state.latest_execution_payload_header == spec.ExecutionPayloadHeader()
        else:
            assert state.latest_execution_payload_header.hash_tree_root() == latest_payload.hash_tree_root()
    else:
        pass

    # Advance to to_slot, applying fork transitions as necessary
    if to_slot is None:
        to_slot = state.slot + 1
    assert to_slot >= state.slot
    if to_slot > state.slot:
        spec, state, _ = transition_across_forks(spec, state, to_slot, phases=phases)

    return spec, state


def get_sync_aggregate(spec, state, latest_payload=None, num_participants=None, signature_slot=None, phases=None):
    # By default, the sync committee signs the previous slot
    if signature_slot is None:
        signature_slot = state.slot + 1
    assert signature_slot > state.slot

    # Ensure correct sync committee and fork version are selected
    if latest_payload is not None:
        signature_spec, signature_state = apply_payload_and_transition(
            spec, state.copy(), latest_payload, signature_slot, phases)
    else:
        signature_spec, signature_state, _ = transition_across_forks(spec, state, signature_slot, phases=phases)

    # Fetch sync committee
    committee_indices = compute_committee_indices(signature_state)
    committee_size = len(committee_indices)

    # By default, use full participation
    if num_participants is None:
        num_participants = committee_size
    assert committee_size >= num_participants >= 0

    # Compute sync aggregate
    sync_committee_bits = [True] * num_participants + [False] * (committee_size - num_participants)
    sync_committee_signature = compute_aggregate_sync_committee_signature(
        signature_spec,
        signature_state,
        max(signature_slot, 1) - 1,
        committee_indices[:num_participants],
    )
    sync_aggregate = signature_spec.SyncAggregate(
        sync_committee_bits=sync_committee_bits,
        sync_committee_signature=sync_committee_signature,
    )
    return sync_aggregate, signature_slot


def create_update(spec, attested, finalized, with_next, with_finality, participation_rate):
    num_participants = floor(spec.SYNC_COMMITTEE_SIZE * participation_rate)

    update = spec.LightClientUpdate()

    update.attested_header = spec.block_contents_to_light_client_header(attested)

    if with_next:
        update.next_sync_committee = attested.state.next_sync_committee
        update.next_sync_committee_branch = spec.compute_merkle_proof(
            attested.state, latest_next_sync_committee_gindex(spec))

    if with_finality:
        update.finalized_header = spec.block_contents_to_light_client_header(finalized)
        update.finality_branch = spec.compute_merkle_proof(
            attested.state, latest_finalized_root_gindex(spec))

    # Ignore pending payload for simplicity - it cannot affect the sync committee at slot + 1
    update.sync_aggregate, update.signature_slot = get_sync_aggregate(
        spec, attested.state, num_participants=num_participants)

    return update


def create_full_block(spec, state, latest_payload=None, at_slot=None, phases=None, sync_aggregate=None):
    # Advance to at_slot - 1
    if at_slot is None:
        at_slot = state.slot + 1
    assert at_slot > state.slot
    spec, state = apply_payload_and_transition(spec, state, latest_payload, at_slot - 1, phases=phases)

    # Create new block for at_slot (the test framework will create same payload internally)
    tmp_state = state.copy()
    tmp_spec, tmp_state, _ = transition_across_forks(spec, tmp_state, at_slot, phases=phases)
    if is_post_eip7732(tmp_spec):
        payload = build_empty_execution_payload(tmp_spec, tmp_state)
        signed_header = build_empty_signed_execution_payload_header(tmp_spec, payload, tmp_state)
    spec, state, block = transition_across_forks(
        spec, state, at_slot, phases=phases, with_block=True, sync_aggregate=sync_aggregate)
    contents = spec.LightClientBlockContents(block=block, state=state.copy())
    if is_post_eip7732(spec):
        assert block.message.body.signed_execution_payload_header == signed_header
        assert latest_payload is not None
        contents.execution_payload = latest_payload
    elif is_post_bellatrix(spec):
        payload = block.message.body.execution_payload
    else:
        payload = None
    return spec, state, contents, payload


def needs_upgrade_to_capella(spec, new_spec):
    return is_post_capella(new_spec) and not is_post_capella(spec)


def needs_upgrade_to_deneb(spec, new_spec):
    return is_post_deneb(new_spec) and not is_post_deneb(spec)


def needs_upgrade_to_electra(spec, new_spec):
    return is_post_electra(new_spec) and not is_post_electra(spec)


def needs_upgrade_to_eip7732(spec, new_spec):
    return is_post_eip7732(new_spec) and not is_post_eip7732(spec)


def check_merkle_branch_equal(spec, new_spec, data, upgraded, gindex):
    if is_post_electra(new_spec):
        assert (
            new_spec.normalize_merkle_branch(upgraded, gindex)
            == new_spec.normalize_merkle_branch(data, gindex)
        )
    else:
        assert upgraded == data


def check_lc_header_equal(spec, new_spec, data, upgraded, genesis_time):
    assert upgraded.beacon.slot == data.beacon.slot
    assert upgraded.beacon.hash_tree_root() == data.beacon.hash_tree_root()
    if is_post_capella(new_spec):
        execution_root = new_spec.get_lc_execution_root(upgraded, genesis_time)
        if is_post_capella(spec):
            assert execution_root == spec.get_lc_execution_root(data, genesis_time)
        else:
            assert execution_root == new_spec.Root()


def upgrade_lc_header_to_new_spec(spec, new_spec, data, phases, genesis_time):
    upgraded = data

    if needs_upgrade_to_capella(spec, new_spec):
        upgraded = phases[CAPELLA].upgrade_lc_header_to_capella(upgraded)
        check_lc_header_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_deneb(spec, new_spec):
        upgraded = phases[DENEB].upgrade_lc_header_to_deneb(upgraded)
        check_lc_header_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_electra(spec, new_spec):
        upgraded = phases[ELECTRA].upgrade_lc_header_to_electra(upgraded)
        check_lc_header_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_eip7732(spec, new_spec):
        upgraded = phases[EIP7732].upgrade_lc_header_to_eip7732(upgraded)
        check_lc_header_equal(spec, new_spec, data, upgraded, genesis_time)

    return upgraded


def check_lc_bootstrap_equal(spec, new_spec, data, upgraded, genesis_time):
    check_lc_header_equal(spec, new_spec, data.header, upgraded.header, genesis_time)
    assert upgraded.current_sync_committee == data.current_sync_committee
    check_merkle_branch_equal(
        spec,
        new_spec,
        data.current_sync_committee_branch,
        upgraded.current_sync_committee_branch,
        latest_current_sync_committee_gindex(new_spec),
    )


def upgrade_lc_bootstrap_to_new_spec(spec, new_spec, data, phases, genesis_time):
    upgraded = data

    if needs_upgrade_to_capella(spec, new_spec):
        upgraded = phases[CAPELLA].upgrade_lc_bootstrap_to_capella(upgraded)
        check_lc_bootstrap_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_deneb(spec, new_spec):
        upgraded = phases[DENEB].upgrade_lc_bootstrap_to_deneb(upgraded)
        check_lc_bootstrap_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_electra(spec, new_spec):
        upgraded = phases[ELECTRA].upgrade_lc_bootstrap_to_electra(upgraded)
        check_lc_bootstrap_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_eip7732(spec, new_spec):
        upgraded = phases[EIP7732].upgrade_lc_bootstrap_to_eip7732(upgraded)
        check_lc_bootstrap_equal(spec, new_spec, data, upgraded, genesis_time)

    return upgraded


def check_lc_update_equal(spec, new_spec, data, upgraded, genesis_time):
    check_lc_header_equal(spec, new_spec, data.attested_header, upgraded.attested_header, genesis_time)
    assert upgraded.next_sync_committee == data.next_sync_committee
    check_merkle_branch_equal(
        spec,
        new_spec,
        data.next_sync_committee_branch,
        upgraded.next_sync_committee_branch,
        latest_next_sync_committee_gindex(new_spec),
    )
    check_lc_header_equal(spec, new_spec, data.finalized_header, upgraded.finalized_header, genesis_time)
    check_merkle_branch_equal(
        spec,
        new_spec,
        data.finality_branch,
        upgraded.finality_branch,
        latest_finalized_root_gindex(new_spec),
    )
    assert upgraded.sync_aggregate == data.sync_aggregate
    assert upgraded.signature_slot == data.signature_slot


def upgrade_lc_update_to_new_spec(spec, new_spec, data, phases, genesis_time):
    upgraded = data

    if needs_upgrade_to_capella(spec, new_spec):
        upgraded = phases[CAPELLA].upgrade_lc_update_to_capella(upgraded)
        check_lc_update_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_deneb(spec, new_spec):
        upgraded = phases[DENEB].upgrade_lc_update_to_deneb(upgraded)
        check_lc_update_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_electra(spec, new_spec):
        upgraded = phases[ELECTRA].upgrade_lc_update_to_electra(upgraded)
        check_lc_update_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_eip7732(spec, new_spec):
        upgraded = phases[EIP7732].upgrade_lc_update_to_eip7732(upgraded)
        check_lc_update_equal(spec, new_spec, data, upgraded, genesis_time)

    return upgraded


def check_lc_finality_update_equal(spec, new_spec, data, upgraded, genesis_time):
    check_lc_header_equal(spec, new_spec, data.attested_header, upgraded.attested_header, genesis_time)
    check_lc_header_equal(spec, new_spec, data.finalized_header, upgraded.finalized_header, genesis_time)
    check_merkle_branch_equal(
        spec,
        new_spec,
        data.finality_branch,
        upgraded.finality_branch,
        latest_finalized_root_gindex(new_spec),
    )
    assert upgraded.sync_aggregate == data.sync_aggregate
    assert upgraded.signature_slot == data.signature_slot


def upgrade_lc_finality_update_to_new_spec(spec, new_spec, data, phases, genesis_time):
    upgraded = data

    if needs_upgrade_to_capella(spec, new_spec):
        upgraded = phases[CAPELLA].upgrade_lc_finality_update_to_capella(upgraded)
        check_lc_finality_update_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_deneb(spec, new_spec):
        upgraded = phases[DENEB].upgrade_lc_finality_update_to_deneb(upgraded)
        check_lc_finality_update_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_electra(spec, new_spec):
        upgraded = phases[ELECTRA].upgrade_lc_finality_update_to_electra(upgraded)
        check_lc_finality_update_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_eip7732(spec, new_spec):
        upgraded = phases[EIP7732].upgrade_lc_finality_update_to_eip7732(upgraded)
        check_lc_finality_update_equal(spec, new_spec, data, upgraded, genesis_time)

    return upgraded


def check_lc_store_equal(spec, new_spec, data, upgraded, genesis_time):
    check_lc_header_equal(spec, new_spec, data.finalized_header, upgraded.finalized_header, genesis_time)
    assert upgraded.current_sync_committee == data.current_sync_committee
    assert upgraded.next_sync_committee == data.next_sync_committee
    if upgraded.best_valid_update is None:
        assert data.best_valid_update is None
    else:
        check_lc_update_equal(spec, new_spec, data.best_valid_update, upgraded.best_valid_update, genesis_time)
    check_lc_header_equal(spec, new_spec, data.optimistic_header, upgraded.optimistic_header, genesis_time)
    assert upgraded.previous_max_active_participants == data.previous_max_active_participants
    assert upgraded.current_max_active_participants == data.current_max_active_participants


def upgrade_lc_store_to_new_spec(spec, new_spec, data, phases, genesis_time):
    upgraded = data

    if needs_upgrade_to_capella(spec, new_spec):
        upgraded = phases[CAPELLA].upgrade_lc_store_to_capella(upgraded)
        check_lc_store_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_deneb(spec, new_spec):
        upgraded = phases[DENEB].upgrade_lc_store_to_deneb(upgraded)
        check_lc_store_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_electra(spec, new_spec):
        upgraded = phases[ELECTRA].upgrade_lc_store_to_electra(upgraded)
        check_lc_store_equal(spec, new_spec, data, upgraded, genesis_time)

    if needs_upgrade_to_eip7732(spec, new_spec):
        upgraded = phases[EIP7732].upgrade_lc_store_to_eip7732(upgraded)
        check_lc_store_equal(spec, new_spec, data, upgraded, genesis_time)

    return upgraded
