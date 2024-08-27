from copy import deepcopy

from eth2spec.test.context import (
    spec_state_test_with_matching_config,
    with_presets,
    with_light_client,
)
from eth2spec.test.helpers.constants import MINIMAL
from eth2spec.test.helpers.forks import (
    is_post_eip7732,
)
from eth2spec.test.helpers.light_client import (
    create_full_block,
    create_update,
)
from eth2spec.test.helpers.state import (
    next_slots,
)


def setup_test(spec, state):
    trusted = spec.LightClientBlockContents()
    trusted.block.message.state_root = state.hash_tree_root()
    trusted.state = state.copy()
    if is_post_eip7732(spec):
        payload = spec.ExecutionPayload()
    else:
        payload = None

    trusted_block_root = trusted.block.message.hash_tree_root()
    bootstrap = spec.create_light_client_bootstrap(trusted)
    store = spec.initialize_light_client_store(trusted_block_root, bootstrap, state.genesis_time)
    store.next_sync_committee = state.next_sync_committee

    return spec, state, trusted, payload, store


@with_light_client
@spec_state_test_with_matching_config
def test_process_light_client_update_not_timeout(spec, state):
    spec, state, genesis, payload, store = setup_test(spec, state)

    # Block at slot 1 doesn't increase sync committee period, so it won't force update store.finalized_header
    spec, state, attested, payload = create_full_block(spec, state, payload)
    signature_slot = state.slot + 1

    # Ensure that finality checkpoint is genesis
    assert state.finalized_checkpoint.epoch == 0

    update = create_update(
        spec, attested, genesis, with_next=False, with_finality=False, participation_rate=1.0)

    pre_store = deepcopy(store)

    spec.process_light_client_update(store, update, signature_slot, state.genesis_validators_root)

    assert store.finalized_header == pre_store.finalized_header
    assert store.best_valid_update == update
    assert store.optimistic_header == update.attested_header
    assert store.current_max_active_participants > 0


@with_light_client
@spec_state_test_with_matching_config
@with_presets([MINIMAL], reason="too slow")
def test_process_light_client_update_at_period_boundary(spec, state):
    spec, state, genesis, payload, store = setup_test(spec, state)

    # Forward to slot before next sync committee period so that next block is final one in period
    next_slots(spec, state, spec.UPDATE_TIMEOUT - 2)
    store_period = spec.compute_sync_committee_period_at_slot(store.optimistic_header.beacon.slot)
    update_period = spec.compute_sync_committee_period_at_slot(state.slot)
    assert store_period == update_period

    spec, state, attested, payload = create_full_block(spec, state, payload)
    signature_slot = state.slot + 1

    update = create_update(
        spec, attested, genesis, with_next=False, with_finality=False, participation_rate=1.0)

    pre_store = deepcopy(store)

    spec.process_light_client_update(store, update, signature_slot, state.genesis_validators_root)

    assert store.finalized_header == pre_store.finalized_header
    assert store.best_valid_update == update
    assert store.optimistic_header == update.attested_header
    assert store.current_max_active_participants > 0


@with_light_client
@spec_state_test_with_matching_config
@with_presets([MINIMAL], reason="too slow")
def test_process_light_client_update_timeout(spec, state):
    genesis, store = setup_test(spec, state)

    # Forward to next sync committee period
    next_slots(spec, state, spec.UPDATE_TIMEOUT)
    store_period = spec.compute_sync_committee_period_at_slot(store.optimistic_header.beacon.slot)
    update_period = spec.compute_sync_committee_period_at_slot(state.slot)
    assert store_period + 1 == update_period

    attested = create_update(spec, state)
    signature_slot = state.slot + 1

    update = create_update(
        spec, attested, genesis, with_next=True, with_finality=False, participation_rate=1.0)

    pre_store = deepcopy(store)

    spec.process_light_client_update(store, update, signature_slot, state.genesis_validators_root)

    assert store.finalized_header == pre_store.finalized_header
    assert store.best_valid_update == update
    assert store.optimistic_header == update.attested_header
    assert store.current_max_active_participants > 0


@with_light_client
@spec_state_test_with_matching_config
@with_presets([MINIMAL], reason="too slow")
def test_process_light_client_update_finality_updated(spec, state):
    spec, state, _, payload, store = setup_test(spec, state)

    # Change finality
    contents = []
    next_slots(spec, state, spec.SLOTS_PER_EPOCH * 2)
    for _ in range(3 * spec.SLOTS_PER_EPOCH):
        spec, state, content, payload = create_full_block(spec, state, payload)
        contents += [content]
    # Ensure that finality checkpoint has changed
    assert state.finalized_checkpoint.epoch == 3
    # Ensure that it's same period
    store_period = spec.compute_sync_committee_period_at_slot(store.optimistic_header.beacon.slot)
    update_period = spec.compute_sync_committee_period_at_slot(state.slot)
    assert store_period == update_period

    attested = contents[-1]
    signature_slot = state.slot + 1

    # Updated finality
    finalized = contents[spec.SLOTS_PER_EPOCH - 1]
    assert finalized.block.message.slot == spec.compute_start_slot_at_epoch(state.finalized_checkpoint.epoch)
    assert finalized.block.message.hash_tree_root() == state.finalized_checkpoint.root

    update = create_update(
        spec, attested, finalized, with_next=False, with_finality=True, participation_rate=1.0)

    spec.process_light_client_update(store, update, signature_slot, state.genesis_validators_root)

    assert store.finalized_header == update.finalized_header
    assert store.best_valid_update is None
    assert store.optimistic_header == update.attested_header
    assert store.current_max_active_participants > 0
