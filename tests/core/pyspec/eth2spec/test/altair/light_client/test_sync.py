from typing import (Any, Dict, List)

from eth_utils import encode_hex
from eth2spec.test.context import (
    default_activation_threshold,
    medium_validator_set,
    single_phase,
    spec_test,
    with_custom_state,
    with_config_overrides,
    with_matching_spec_config,
    with_phases,
    with_presets,
    with_light_client,
    with_state,
)
from eth2spec.test.helpers.constants import (
    ALTAIR, BELLATRIX, CAPELLA, DENEB, ELECTRA, EIP7732,
    MINIMAL,
)
from eth2spec.test.helpers.forks import (
    get_spec_for_fork_version,
    is_post_capella, is_post_deneb, is_post_electra, is_post_eip7732
)
from eth2spec.test.helpers.genesis import (
    get_post_eip7732_genesis_execution_payload,
)
from eth2spec.test.helpers.light_client import (
    apply_payload_and_transition,
    compute_start_slot_at_next_sync_committee_period,
    create_full_block,
    get_sync_aggregate,
    upgrade_lc_bootstrap_to_new_spec,
    upgrade_lc_update_to_new_spec,
    upgrade_lc_store_to_new_spec,
)


class LightClientSyncTest(object):
    steps: List[Dict[str, Any]]
    genesis_time: Any
    genesis_validators_root: Any
    s_spec: Any
    store: Any


def get_store_fork_version(s_spec):
    if is_post_eip7732(s_spec):
        return s_spec.config.EIP7732_FORK_VERSION
    if is_post_electra(s_spec):
        return s_spec.config.ELECTRA_FORK_VERSION
    if is_post_deneb(s_spec):
        return s_spec.config.DENEB_FORK_VERSION
    if is_post_capella(s_spec):
        return s_spec.config.CAPELLA_FORK_VERSION
    return s_spec.config.ALTAIR_FORK_VERSION


def setup_test(spec, state, s_spec=None, phases=None, payload=None):
    test = LightClientSyncTest()
    test.steps = []

    if s_spec is None:
        s_spec = spec
    if phases is None:
        phases = {
            spec.fork: spec,
            s_spec.fork: s_spec,
        }
    test.s_spec = s_spec

    yield "genesis_time", "meta", int(state.genesis_time)
    test.genesis_time = state.genesis_time
    yield "genesis_validators_root", "meta", "0x" + state.genesis_validators_root.hex()
    test.genesis_validators_root = state.genesis_validators_root

    genesis = spec.LightClientBlockContents()
    genesis.block.message.state_root = state.hash_tree_root()
    genesis.state = state.copy()
    if is_post_eip7732(spec) and payload is None:
        payload = get_post_eip7732_genesis_execution_payload(spec)

    spec, state, trusted, payload = create_full_block(
        spec, state, payload, state.slot + 2 * spec.SLOTS_PER_EPOCH)
    trusted_block_root = trusted.block.message.hash_tree_root()
    yield "trusted_block_root", "meta", "0x" + trusted_block_root.hex()

    data_fork_version = spec.compute_fork_version(spec.compute_epoch_at_slot(trusted.block.message.slot))
    data_fork_digest = spec.compute_fork_digest(data_fork_version, test.genesis_validators_root)
    d_spec = get_spec_for_fork_version(spec, data_fork_version, phases)
    data = d_spec.create_light_client_bootstrap(trusted)
    yield "bootstrap_fork_digest", "meta", encode_hex(data_fork_digest)
    yield "bootstrap", data

    upgraded = upgrade_lc_bootstrap_to_new_spec(d_spec, test.s_spec, data, phases, test.genesis_time)
    test.store = test.s_spec.initialize_light_client_store(trusted_block_root, upgraded, state.genesis_time)
    store_fork_version = get_store_fork_version(test.s_spec)
    store_fork_digest = test.s_spec.compute_fork_digest(store_fork_version, test.genesis_validators_root)
    yield "store_fork_digest", "meta", encode_hex(store_fork_digest)

    return spec, state, genesis, trusted, payload, test


def finish_test(test):
    yield "steps", test.steps


def get_update_file_name(d_spec, update):
    if d_spec.is_sync_committee_update(update):
        suffix1 = "s"
    else:
        suffix1 = "x"
    if d_spec.is_finality_update(update):
        suffix2 = "f"
    else:
        suffix2 = "x"
    return f"update_{encode_hex(update.attested_header.beacon.hash_tree_root())}_{suffix1}{suffix2}"


def get_checks(test, s_spec, store):
    if is_post_capella(s_spec):
        return {
            "finalized_header": {
                'slot': int(store.finalized_header.beacon.slot),
                'beacon_root': encode_hex(store.finalized_header.beacon.hash_tree_root()),
                'execution_root': encode_hex(s_spec.get_lc_execution_root(
                    store.finalized_header, test.genesis_time)),
            },
            "optimistic_header": {
                'slot': int(store.optimistic_header.beacon.slot),
                'beacon_root': encode_hex(store.optimistic_header.beacon.hash_tree_root()),
                'execution_root': encode_hex(s_spec.get_lc_execution_root(
                    store.optimistic_header, test.genesis_time)),
            },
        }

    return {
        "finalized_header": {
            'slot': int(store.finalized_header.beacon.slot),
            'beacon_root': encode_hex(store.finalized_header.beacon.hash_tree_root()),
        },
        "optimistic_header": {
            'slot': int(store.optimistic_header.beacon.slot),
            'beacon_root': encode_hex(store.optimistic_header.beacon.hash_tree_root()),
        },
    }


def emit_force_update(test, spec, state):
    current_slot = state.slot
    test.s_spec.process_light_client_store_force_update(test.store, current_slot)

    yield from []  # Consistently enable `yield from` syntax in calling tests
    test.steps.append({
        "force_update": {
            "current_slot": int(current_slot),
            "checks": get_checks(test, test.s_spec, test.store),
        }
    })


def emit_update(test, spec, contents, attested, finalized, with_next=True, phases=None):
    data_fork_version = spec.compute_fork_version(spec.compute_epoch_at_slot(attested.block.message.slot))
    data_fork_digest = spec.compute_fork_digest(data_fork_version, test.genesis_validators_root)
    d_spec = get_spec_for_fork_version(spec, data_fork_version, phases)
    data = d_spec.create_light_client_update(contents, attested, finalized)
    if not with_next:
        data.next_sync_committee = spec.SyncCommittee()
        data.next_sync_committee_branch = spec.NextSyncCommitteeBranch()
    current_slot = contents.state.slot

    upgraded = upgrade_lc_update_to_new_spec(d_spec, test.s_spec, data, phases, test.genesis_time)
    test.s_spec.process_light_client_update(
        test.store, upgraded, current_slot, test.genesis_time, test.genesis_validators_root)

    yield get_update_file_name(d_spec, data), data
    test.steps.append({
        "process_update": {
            "update_fork_digest": encode_hex(data_fork_digest),
            "update": get_update_file_name(d_spec, data),
            "current_slot": int(current_slot),
            "checks": get_checks(test, test.s_spec, test.store),
        }
    })
    return upgraded


def emit_upgrade_store(test, new_s_spec, phases=None):
    test.store = upgrade_lc_store_to_new_spec(test.s_spec, new_s_spec, test.store, phases, test.genesis_time)
    test.s_spec = new_s_spec
    store_fork_version = get_store_fork_version(test.s_spec)
    store_fork_digest = test.s_spec.compute_fork_digest(store_fork_version, test.genesis_validators_root)

    yield from []  # Consistently enable `yield from` syntax in calling tests
    test.steps.append({
        "upgrade_store": {
            "store_fork_digest": encode_hex(store_fork_digest),
            "checks": get_checks(test, test.s_spec, test.store),
        }
    })


@with_light_client
@spec_test
@with_custom_state(balances_fn=medium_validator_set, threshold_fn=default_activation_threshold)
@with_matching_spec_config()
@with_presets([MINIMAL], reason="too slow")
@single_phase
def test_light_client_sync(spec, state):
    # Start test
    spec, state, _, _, payload, test = yield from setup_test(spec, state)

    # Initial `LightClientUpdate`, populating `store.next_sync_committee`
    # ```
    #                                                                   |
    #    +-----------+                   +----------+     +-----------+ |
    #    | finalized | <-- (2 epochs) -- | attested | <-- | signature | |
    #    +-----------+                   +----------+     +-----------+ |
    #                                                                   |
    #                                                                   |
    #                                                            sync committee
    #                                                            period boundary
    # ```
    spec, state, finalized, payload = create_full_block(
        spec, state, payload, state.slot + spec.SLOTS_PER_EPOCH)
    for _ in range(2 * spec.SLOTS_PER_EPOCH):
        spec, state, attested, payload = create_full_block(spec, state, payload)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, finalized)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Advance to next sync committee period
    # ```
    #                                                                   |
    #    +-----------+                   +----------+     +-----------+ |
    #    | finalized | <-- (2 epochs) -- | attested | <-- | signature | |
    #    +-----------+                   +----------+     +-----------+ |
    #                                                                   |
    #                                                                   |
    #                                                            sync committee
    #                                                            period boundary
    # ```
    spec, state, finalized, payload = create_full_block(
        spec, state, payload, compute_start_slot_at_next_sync_committee_period(spec, state) + spec.SLOTS_PER_EPOCH)
    for _ in range(2 * spec.SLOTS_PER_EPOCH):
        spec, state, attested, payload = create_full_block(spec, state, payload)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, finalized)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Edge case: Signature in next period
    # ```
    #                                                  |
    #    +-----------+                   +----------+  |  +-----------+
    #    | finalized | <-- (2 epochs) -- | attested | <-- | signature |
    #    +-----------+                   +----------+  |  +-----------+
    #                                                  |
    #                                                  |
    #                                           sync committee
    #                                           period boundary
    # ```
    spec, state, finalized, payload = create_full_block(
        spec, state, payload, state.slot + spec.SLOTS_PER_EPOCH - 1)
    for _ in range(2 * spec.SLOTS_PER_EPOCH):
        spec, state, attested, payload = create_full_block(spec, state, payload)
    signature_slot = compute_start_slot_at_next_sync_committee_period(spec, state) + 1
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload, signature_slot=signature_slot)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, signature_slot, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, finalized)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Edge case: Finalized header not included
    # ```
    #                          |
    #    + - - - - - +         |         +----------+     +-----------+
    #    ¦ finalized ¦ <-- (2 epochs) -- | attested | <-- | signature |
    #    + - - - - - +         |         +----------+     +-----------+
    #                          |
    #                          |
    #                   sync committee
    #                   period boundary
    # ```
    attested = contents
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(spec, state, payload, sync_aggregate=sync_aggregate)
    update = yield from emit_update(test, spec, contents, attested, finalized=None)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Non-finalized case: Attested `next_sync_committee` is not finalized
    # ```
    #                          |
    #    +-----------+         |         +----------+     +-----------+
    #    | finalized | <-- (2 epochs) -- | attested | <-- | signature |
    #    +-----------+         |         +----------+     +-----------+
    #                          |
    #                          |
    #                   sync committee
    #                   period boundary
    # ```
    attested = contents
    store_state = attested.state
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(spec, state, payload, sync_aggregate=sync_aggregate)
    update = yield from emit_update(test, spec, contents, attested, finalized)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Force-update using timeout
    # ```
    #                          |
    #    +-----------+         |         +----------+
    #    | finalized | <-- (2 epochs) -- | attested |
    #    +-----------+         |         +----------+
    #                          |            ^
    #                          |             \
    #                   sync committee        `--- store.finalized_header
    #                   period boundary
    # ```
    attested = contents
    spec, state = apply_payload_and_transition(
        spec, state, payload, state.slot + spec.UPDATE_TIMEOUT - 1)
    yield from emit_force_update(test, spec, state)
    assert test.store.finalized_header.beacon.slot == store_state.slot
    assert test.store.next_sync_committee == store_state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == store_state.slot

    # Edge case: Finalized header not included, after force-update
    # ```
    #                          |                                |
    #    + - - - - - +         |         +--+     +----------+  |  +-----------+
    #    ¦ finalized ¦ <-- (2 epochs) -- |  | <-- | attested | <-- | signature |
    #    + - - - - - +         |         +--+     +----------+  |  +-----------+
    #                          |          /                     |
    #                          |  store.fin                     |
    #                   sync committee                   sync committee
    #                   period boundary                  period boundary
    # ```
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(spec, state, payload, sync_aggregate=sync_aggregate)
    update = yield from emit_update(test, spec, contents, attested, finalized=None)
    assert test.store.finalized_header.beacon.slot == store_state.slot
    assert test.store.next_sync_committee == store_state.next_sync_committee
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Edge case: Finalized header older than store
    # ```
    #                          |               |
    #    +-----------+         |         +--+  |  +----------+     +-----------+
    #    | finalized | <-- (2 epochs) -- |  | <-- | attested | <-- | signature |
    #    +-----------+         |         +--+  |  +----------+     +-----------+
    #                          |          /    |
    #                          |  store.fin    |
    #                   sync committee       sync committee
    #                   period boundary      period boundary
    # ```
    attested = contents
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(spec, state, payload, sync_aggregate=sync_aggregate)
    update = yield from emit_update(test, spec, contents, attested, finalized)
    assert test.store.finalized_header.beacon.slot == store_state.slot
    assert test.store.next_sync_committee == store_state.next_sync_committee
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot
    yield from emit_force_update(test, spec, state)
    assert test.store.finalized_header.beacon.slot == attested.state.slot
    assert test.store.next_sync_committee == attested.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Advance to next sync committee period
    # ```
    #                                                                   |
    #    +-----------+                   +----------+     +-----------+ |
    #    | finalized | <-- (2 epochs) -- | attested | <-- | signature | |
    #    +-----------+                   +----------+     +-----------+ |
    #                                                                   |
    #                                                                   |
    #                                                            sync committee
    #                                                            period boundary
    # ```
    spec, state, finalized, payload = create_full_block(
        spec, state, payload, compute_start_slot_at_next_sync_committee_period(spec, state) + spec.SLOTS_PER_EPOCH)
    for _ in range(2 * spec.SLOTS_PER_EPOCH):
        spec, state, attested, payload = create_full_block(spec, state, payload)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, finalized)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Finish test
    yield from finish_test(test)


@with_light_client
@spec_test
@with_custom_state(balances_fn=medium_validator_set, threshold_fn=default_activation_threshold)
@with_matching_spec_config()
@with_presets([MINIMAL], reason="too slow")
@single_phase
def test_supply_sync_committee_from_past_update(spec, state):
    if is_post_eip7732(spec):
        payload = get_post_eip7732_genesis_execution_payload(spec)
    else:
        payload = None

    # Advance the chain, so that a `LightClientUpdate` from the past is available
    spec, state, finalized, payload = create_full_block(
        spec, state, payload, state.slot + 2 * spec.SLOTS_PER_EPOCH)
    for _ in range(2 * spec.SLOTS_PER_EPOCH):
        spec, state, attested, payload = create_full_block(spec, state, payload)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, sync_aggregate=sync_aggregate)

    # Start test
    spec, state, _, _, payload, test = yield from setup_test(spec, state, payload=payload)
    assert not spec.is_next_sync_committee_known(test.store)

    # Apply `LightClientUpdate` from the past, populating `store.next_sync_committee`
    yield from emit_update(test, spec, contents, attested, finalized)
    assert test.store.finalized_header.beacon.slot == state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == state.slot

    # Finish test
    yield from finish_test(test)


@with_light_client
@spec_test
@with_custom_state(balances_fn=medium_validator_set, threshold_fn=default_activation_threshold)
@with_matching_spec_config()
@with_presets([MINIMAL], reason="too slow")
@single_phase
def test_advance_finality_without_sync_committee(spec, state):
    # Start test
    spec, state, _, _, payload, test = yield from setup_test(spec, state)

    # Initial `LightClientUpdate`, populating `store.next_sync_committee`
    spec, state, finalized, payload = create_full_block(
        spec, state, payload, state.slot + spec.SLOTS_PER_EPOCH)
    for _ in range(2 * spec.SLOTS_PER_EPOCH):
        spec, state, attested, payload = create_full_block(spec, state, payload)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, finalized)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Advance finality into next sync committee period, but omit `next_sync_committee`
    spec, state, finalized, payload = create_full_block(
        spec, state, payload, compute_start_slot_at_next_sync_committee_period(spec, state) + spec.SLOTS_PER_EPOCH)
    for _ in range(spec.SLOTS_PER_EPOCH):
        spec, state, justified, payload = create_full_block(spec, state, payload)
    for _ in range(spec.SLOTS_PER_EPOCH):
        spec, state, attested, payload = create_full_block(spec, state, payload)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(spec, state, payload, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, finalized, with_next=False)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert not spec.is_next_sync_committee_known(test.store)
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Advance finality once more, with `next_sync_committee` still unknown
    past_state = finalized.state
    finalized = justified
    for _ in range(spec.SLOTS_PER_EPOCH - 1):
        spec, state, attested, payload = create_full_block(spec, state, payload)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, sync_aggregate=sync_aggregate)

    # Apply `LightClientUpdate` without `finalized_header` nor `next_sync_committee`
    update = yield from emit_update(test, spec, contents, attested, finalized=None, with_next=False)
    assert test.store.finalized_header.beacon.slot == past_state.slot
    assert not spec.is_next_sync_committee_known(test.store)
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Apply `LightClientUpdate` with `finalized_header` but no `next_sync_committee`
    yield from emit_update(test, spec, contents, attested, finalized, with_next=False)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert not spec.is_next_sync_committee_known(test.store)
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Apply full `LightClientUpdate`, supplying `next_sync_committee`
    yield from emit_update(test, spec, contents, attested, finalized)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Finish test
    yield from finish_test(test)


def run_test_single_fork(spec, phases, state, fork):
    # Start test
    spec, state, genesis, trusted, payload, test = yield from setup_test(spec, state, phases=phases)

    # Initial `LightClientUpdate`
    spec, state, attested, payload = create_full_block(
        spec, state, payload, phases=phases)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload, phases=phases)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, phases=phases, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, genesis, phases=phases)
    assert test.store.finalized_header.beacon.slot == trusted.state.slot
    assert test.store.next_sync_committee == trusted.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Jump to two slots before fork
    fork_epoch = getattr(phases[fork].config, fork.upper() + '_FORK_EPOCH')
    spec, state, attested, payload = create_full_block(
        spec, state, payload, spec.compute_start_slot_at_epoch(fork_epoch) - 3, phases=phases)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload, phases=phases)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, phases=phases, sync_aggregate=sync_aggregate)
    update = yield from emit_update(
        test, spec, contents, attested, genesis, phases=phases)
    assert test.store.finalized_header.beacon.slot == trusted.state.slot
    assert test.store.next_sync_committee == trusted.state.next_sync_committee
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Perform `LightClientStore` upgrade
    yield from emit_upgrade_store(test, phases[fork], phases=phases)
    update = test.store.best_valid_update

    # Final slot before fork, check that importing the pre-fork format still works
    attested = contents
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload, phases=phases)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, phases=phases, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, genesis, phases=phases)
    assert test.store.finalized_header.beacon.slot == trusted.state.slot
    assert test.store.next_sync_committee == trusted.state.next_sync_committee
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Upgrade to post-fork spec, attested block is still before the fork
    attested = contents
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload, phases=phases)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, spec.compute_start_slot_at_epoch(fork_epoch),
        phases=phases, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, genesis, phases=phases)
    assert test.store.finalized_header.beacon.slot == trusted.state.slot
    assert test.store.next_sync_committee == trusted.state.next_sync_committee
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Another block after the fork, this time attested block is after the fork
    attested = contents
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload, phases=phases)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, phases=phases, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, genesis, phases=phases)
    assert test.store.finalized_header.beacon.slot == trusted.state.slot
    assert test.store.next_sync_committee == trusted.state.next_sync_committee
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Jump to next epoch
    spec, state, attested, payload = create_full_block(
        spec, state, payload, spec.compute_start_slot_at_epoch(fork_epoch + 1) - 1, phases=phases)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload, phases=phases)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, phases=phases, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, genesis, phases=phases)
    assert test.store.finalized_header.beacon.slot == trusted.state.slot
    assert test.store.next_sync_committee == trusted.state.next_sync_committee
    assert test.store.best_valid_update == update
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Finalize the fork
    finalized = contents
    for _ in range(2 * spec.SLOTS_PER_EPOCH):
        spec, state, attested, payload = create_full_block(
            spec, state, payload, phases=phases)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload, phases=phases)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, phases=phases, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, finalized, phases=phases)
    assert test.store.finalized_header.beacon.slot == finalized.state.slot
    assert test.store.next_sync_committee == finalized.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Finish test
    yield from finish_test(test)


@with_phases(phases=[BELLATRIX], other_phases=[CAPELLA])
@spec_test
@with_config_overrides({
    'CAPELLA_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
}, emit=False)
@with_state
@with_matching_spec_config(emitted_fork=CAPELLA)
@with_presets([MINIMAL], reason="too slow")
def test_capella_fork(spec, phases, state):
    yield from run_test_single_fork(spec, phases, state, CAPELLA)


@with_phases(phases=[CAPELLA], other_phases=[DENEB])
@spec_test
@with_config_overrides({
    'DENEB_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
}, emit=False)
@with_state
@with_matching_spec_config(emitted_fork=DENEB)
@with_presets([MINIMAL], reason="too slow")
def test_deneb_fork(spec, phases, state):
    yield from run_test_single_fork(spec, phases, state, DENEB)


@with_phases(phases=[DENEB], other_phases=[ELECTRA])
@spec_test
@with_config_overrides({
    'ELECTRA_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
}, emit=False)
@with_state
@with_matching_spec_config(emitted_fork=ELECTRA)
@with_presets([MINIMAL], reason="too slow")
def test_electra_fork(spec, phases, state):
    yield from run_test_single_fork(spec, phases, state, ELECTRA)


@with_phases(phases=[ELECTRA], other_phases=[EIP7732])
@spec_test
@with_config_overrides({
    'EIP7732_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
}, emit=False)
@with_custom_state(balances_fn=medium_validator_set, threshold_fn=default_activation_threshold)
@with_matching_spec_config(emitted_fork=EIP7732)
@with_presets([MINIMAL], reason="too slow")
def test_eip7732_fork(spec, phases, state):
    yield from run_test_single_fork(spec, phases, state, EIP7732)


def run_test_multi_fork(spec, phases, state, fork_1, fork_2):
    # Start test so that finalized is from `spec`, ...
    spec, state, genesis, trusted, payload, test = yield from setup_test(spec, state, phases[fork_2], phases)

    # ..., attested is from `fork_1`, ...
    fork_1_epoch = getattr(phases[fork_1].config, fork_1.upper() + '_FORK_EPOCH')
    spec, state, attested, payload = create_full_block(
        spec, state, payload, spec.compute_start_slot_at_epoch(fork_1_epoch), phases)

    # ..., and signature is from `fork_2`
    fork_2_epoch = getattr(phases[fork_2].config, fork_2.upper() + '_FORK_EPOCH')
    signature_slot = spec.compute_start_slot_at_epoch(fork_2_epoch)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload, signature_slot=signature_slot, phases=phases)
    spec, state, contents, payload = create_full_block(
        spec, state, payload, signature_slot, phases, sync_aggregate=sync_aggregate)

    # Check that update applies
    yield from emit_update(test, spec, contents, attested, genesis, phases=phases)
    assert test.store.finalized_header.beacon.slot == trusted.state.slot
    assert test.store.next_sync_committee == trusted.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Finish test
    yield from finish_test(test)


@with_phases(phases=[BELLATRIX], other_phases=[CAPELLA, DENEB])
@spec_test
@with_config_overrides({
    'CAPELLA_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
    'DENEB_FORK_EPOCH': 4,
}, emit=False)
@with_state
@with_matching_spec_config(emitted_fork=DENEB)
@with_presets([MINIMAL], reason="too slow")
def test_capella_deneb_fork(spec, phases, state):
    yield from run_test_multi_fork(spec, phases, state, CAPELLA, DENEB)


@with_phases(phases=[BELLATRIX], other_phases=[CAPELLA, DENEB, ELECTRA])
@spec_test
@with_config_overrides({
    'CAPELLA_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
    'DENEB_FORK_EPOCH': 4,
    'ELECTRA_FORK_EPOCH': 5,
}, emit=False)
@with_state
@with_matching_spec_config(emitted_fork=ELECTRA)
@with_presets([MINIMAL], reason="too slow")
def test_capella_electra_fork(spec, phases, state):
    yield from run_test_multi_fork(spec, phases, state, CAPELLA, ELECTRA)


@with_phases(phases=[BELLATRIX], other_phases=[CAPELLA, DENEB, ELECTRA, EIP7732])
@spec_test
@with_config_overrides({
    'CAPELLA_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
    'DENEB_FORK_EPOCH': 4,
    'ELECTRA_FORK_EPOCH': 5,
    'EIP7732_FORK_EPOCH': 6,
}, emit=False)
@with_state
@with_matching_spec_config(emitted_fork=EIP7732)
@with_presets([MINIMAL], reason="too slow")
def test_capella_eip7732_fork(spec, phases, state):
    yield from run_test_multi_fork(spec, phases, state, CAPELLA, EIP7732)


@with_phases(phases=[CAPELLA], other_phases=[DENEB, ELECTRA])
@spec_test
@with_config_overrides({
    'DENEB_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
    'ELECTRA_FORK_EPOCH': 4,
}, emit=False)
@with_state
@with_matching_spec_config(emitted_fork=ELECTRA)
@with_presets([MINIMAL], reason="too slow")
def test_deneb_electra_fork(spec, phases, state):
    yield from run_test_multi_fork(spec, phases, state, DENEB, ELECTRA)


@with_phases(phases=[CAPELLA], other_phases=[DENEB, ELECTRA, EIP7732])
@spec_test
@with_config_overrides({
    'DENEB_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
    'ELECTRA_FORK_EPOCH': 4,
    'EIP7732_FORK_EPOCH': 5,
}, emit=False)
@with_state
@with_matching_spec_config(emitted_fork=EIP7732)
@with_presets([MINIMAL], reason="too slow")
def test_deneb_eip7732_fork(spec, phases, state):
    yield from run_test_multi_fork(spec, phases, state, DENEB, EIP7732)


@with_phases(phases=[DENEB], other_phases=[ELECTRA, EIP7732])
@spec_test
@with_config_overrides({
    'ELECTRA_FORK_EPOCH': 3,  # `setup_test` advances to epoch 2
    'EIP7732_FORK_EPOCH': 4,
}, emit=False)
@with_state
@with_matching_spec_config(emitted_fork=EIP7732)
@with_presets([MINIMAL], reason="too slow")
def test_electra_eip7732_fork(spec, phases, state):
    yield from run_test_multi_fork(spec, phases, state, ELECTRA, EIP7732)


def run_test_upgraded_store_with_legacy_data(spec, phases, state, fork):
    # Start test (Legacy bootstrap with an upgraded store)
    spec, state, genesis, trusted, payload, test = yield from setup_test(spec, state, phases[fork], phases)

    # Initial `LightClientUpdate` (check that the upgraded store can process it)
    spec, state, attested, payload = create_full_block(spec, state, payload)
    sync_aggregate, _ = get_sync_aggregate(spec, state, payload)
    spec, state, contents, payload = create_full_block(spec, state, payload, sync_aggregate=sync_aggregate)
    yield from emit_update(test, spec, contents, attested, genesis, phases=phases)
    assert test.store.finalized_header.beacon.slot == trusted.state.slot
    assert test.store.next_sync_committee == trusted.state.next_sync_committee
    assert test.store.best_valid_update is None
    assert test.store.optimistic_header.beacon.slot == attested.state.slot

    # Finish test
    yield from finish_test(test)


@with_phases(phases=[ALTAIR, BELLATRIX], other_phases=[CAPELLA])
@spec_test
@with_state
@with_matching_spec_config(emitted_fork=CAPELLA)
@with_presets([MINIMAL], reason="too slow")
def test_capella_store_with_legacy_data(spec, phases, state):
    yield from run_test_upgraded_store_with_legacy_data(spec, phases, state, CAPELLA)


@with_phases(phases=[ALTAIR, BELLATRIX, CAPELLA], other_phases=[CAPELLA, DENEB])
@spec_test
@with_state
@with_matching_spec_config(emitted_fork=DENEB)
@with_presets([MINIMAL], reason="too slow")
def test_deneb_store_with_legacy_data(spec, phases, state):
    yield from run_test_upgraded_store_with_legacy_data(spec, phases, state, DENEB)


@with_phases(phases=[ALTAIR, BELLATRIX, CAPELLA, DENEB], other_phases=[CAPELLA, DENEB, ELECTRA])
@spec_test
@with_state
@with_matching_spec_config(emitted_fork=ELECTRA)
@with_presets([MINIMAL], reason="too slow")
def test_electra_store_with_legacy_data(spec, phases, state):
    yield from run_test_upgraded_store_with_legacy_data(spec, phases, state, ELECTRA)


@with_phases(phases=[ALTAIR, BELLATRIX, CAPELLA, DENEB, ELECTRA], other_phases=[CAPELLA, DENEB, ELECTRA, EIP7732])
@spec_test
@with_state
@with_matching_spec_config(emitted_fork=EIP7732)
@with_presets([MINIMAL], reason="too slow")
def test_eip7732_store_with_legacy_data(spec, phases, state):
    yield from run_test_upgraded_store_with_legacy_data(spec, phases, state, EIP7732)
