from eth2spec.test.context import (
    spec_state_test,
    with_presets,
    with_light_client,
)
from eth2spec.test.helpers.constants import MINIMAL
from eth2spec.test.helpers.forks import (
    is_post_eip7732,
)
from eth2spec.test.helpers.genesis import (
    get_post_eip7732_genesis_execution_payload,
)
from eth2spec.test.helpers.light_client import (
    create_full_block,
    create_update,
)


def create_test_update(spec, test, with_next, with_finality, participation_rate):
    attested, finalized = test
    return create_update(spec, attested, finalized, with_next, with_finality, participation_rate)


@with_light_client
@spec_state_test
@with_presets([MINIMAL], reason="too slow")
def test_update_ranking(spec, state):
    if is_post_eip7732(spec):
        payload = get_post_eip7732_genesis_execution_payload(spec)
    else:
        payload = None

    # Set up blocks and states:
    # - `sig_finalized` / `sig_attested` --> Only signature in next sync committee period
    # - `att_finalized` / `att_attested` --> Attested header also in next sync committee period
    # - `fin_finalized` / `fin_attested` --> Finalized header also in next sync committee period
    # - `lat_finalized` / `lat_attested` --> Like `fin`, but at a later `attested_header.beacon.slot`
    spec, state, sig_finalized, payload = create_full_block(
        spec, state, payload, spec.compute_start_slot_at_epoch(spec.EPOCHS_PER_SYNC_COMMITTEE_PERIOD - 3))
    for _ in range(spec.SLOTS_PER_EPOCH):
        spec, state, att_finalized, payload = create_full_block(spec, state, payload)
    for _ in range(2 * spec.SLOTS_PER_EPOCH - 1):
        spec, state, sig_attested, payload = create_full_block(spec, state, payload)
    spec, state, att_attested, payload = create_full_block(spec, state, payload)
    fin_finalized = att_attested
    for _ in range(2 * spec.SLOTS_PER_EPOCH):
        spec, state, fin_attested, payload = create_full_block(spec, state, payload)
    lat_finalized = fin_finalized
    spec, state, lat_attested, payload = create_full_block(spec, state, payload)
    sig = (sig_attested, sig_finalized)
    att = (att_attested, att_finalized)
    fin = (fin_attested, fin_finalized)
    lat = (lat_attested, lat_finalized)

    # Create updates (in descending order of quality)
    updates = [
        # Updates with sync committee finality
        create_test_update(spec, fin, with_next=1, with_finality=1, participation_rate=1.0),
        create_test_update(spec, lat, with_next=1, with_finality=1, participation_rate=1.0),
        create_test_update(spec, fin, with_next=1, with_finality=1, participation_rate=0.8),
        create_test_update(spec, lat, with_next=1, with_finality=1, participation_rate=0.8),

        # Updates without sync committee finality
        create_test_update(spec, att, with_next=1, with_finality=1, participation_rate=1.0),
        create_test_update(spec, att, with_next=1, with_finality=1, participation_rate=0.8),

        # Updates without indication of any finality
        create_test_update(spec, att, with_next=1, with_finality=0, participation_rate=1.0),
        create_test_update(spec, fin, with_next=1, with_finality=0, participation_rate=1.0),
        create_test_update(spec, lat, with_next=1, with_finality=0, participation_rate=1.0),
        create_test_update(spec, att, with_next=1, with_finality=0, participation_rate=0.8),
        create_test_update(spec, fin, with_next=1, with_finality=0, participation_rate=0.8),
        create_test_update(spec, lat, with_next=1, with_finality=0, participation_rate=0.8),

        # Updates with sync committee finality but no `next_sync_committee`
        create_test_update(spec, sig, with_next=0, with_finality=1, participation_rate=1.0),
        create_test_update(spec, fin, with_next=0, with_finality=1, participation_rate=1.0),
        create_test_update(spec, lat, with_next=0, with_finality=1, participation_rate=1.0),
        create_test_update(spec, sig, with_next=0, with_finality=1, participation_rate=0.8),
        create_test_update(spec, fin, with_next=0, with_finality=1, participation_rate=0.8),
        create_test_update(spec, lat, with_next=0, with_finality=1, participation_rate=0.8),

        # Updates without sync committee finality and also no `next_sync_committee`
        create_test_update(spec, att, with_next=0, with_finality=1, participation_rate=1.0),
        create_test_update(spec, att, with_next=0, with_finality=1, participation_rate=0.8),

        # Updates without indication of any finality nor `next_sync_committee`
        create_test_update(spec, sig, with_next=0, with_finality=0, participation_rate=1.0),
        create_test_update(spec, att, with_next=0, with_finality=0, participation_rate=1.0),
        create_test_update(spec, fin, with_next=0, with_finality=0, participation_rate=1.0),
        create_test_update(spec, lat, with_next=0, with_finality=0, participation_rate=1.0),
        create_test_update(spec, sig, with_next=0, with_finality=0, participation_rate=0.8),
        create_test_update(spec, att, with_next=0, with_finality=0, participation_rate=0.8),
        create_test_update(spec, fin, with_next=0, with_finality=0, participation_rate=0.8),
        create_test_update(spec, lat, with_next=0, with_finality=0, participation_rate=0.8),

        # Updates with low sync committee participation
        create_test_update(spec, fin, with_next=1, with_finality=1, participation_rate=0.4),
        create_test_update(spec, lat, with_next=1, with_finality=1, participation_rate=0.4),
        create_test_update(spec, att, with_next=1, with_finality=1, participation_rate=0.4),
        create_test_update(spec, att, with_next=1, with_finality=0, participation_rate=0.4),
        create_test_update(spec, fin, with_next=1, with_finality=0, participation_rate=0.4),
        create_test_update(spec, lat, with_next=1, with_finality=0, participation_rate=0.4),
        create_test_update(spec, sig, with_next=0, with_finality=1, participation_rate=0.4),
        create_test_update(spec, fin, with_next=0, with_finality=1, participation_rate=0.4),
        create_test_update(spec, lat, with_next=0, with_finality=1, participation_rate=0.4),
        create_test_update(spec, att, with_next=0, with_finality=1, participation_rate=0.4),
        create_test_update(spec, sig, with_next=0, with_finality=0, participation_rate=0.4),
        create_test_update(spec, att, with_next=0, with_finality=0, participation_rate=0.4),
        create_test_update(spec, fin, with_next=0, with_finality=0, participation_rate=0.4),
        create_test_update(spec, lat, with_next=0, with_finality=0, participation_rate=0.4),

        # Updates with very low sync committee participation
        create_test_update(spec, fin, with_next=1, with_finality=1, participation_rate=0.2),
        create_test_update(spec, lat, with_next=1, with_finality=1, participation_rate=0.2),
        create_test_update(spec, att, with_next=1, with_finality=1, participation_rate=0.2),
        create_test_update(spec, att, with_next=1, with_finality=0, participation_rate=0.2),
        create_test_update(spec, fin, with_next=1, with_finality=0, participation_rate=0.2),
        create_test_update(spec, lat, with_next=1, with_finality=0, participation_rate=0.2),
        create_test_update(spec, sig, with_next=0, with_finality=1, participation_rate=0.2),
        create_test_update(spec, fin, with_next=0, with_finality=1, participation_rate=0.2),
        create_test_update(spec, lat, with_next=0, with_finality=1, participation_rate=0.2),
        create_test_update(spec, att, with_next=0, with_finality=1, participation_rate=0.2),
        create_test_update(spec, sig, with_next=0, with_finality=0, participation_rate=0.2),
        create_test_update(spec, att, with_next=0, with_finality=0, participation_rate=0.2),
        create_test_update(spec, fin, with_next=0, with_finality=0, participation_rate=0.2),
        create_test_update(spec, lat, with_next=0, with_finality=0, participation_rate=0.2),
    ]
    yield "updates", updates

    for i in range(len(updates) - 1):
        assert spec.is_better_update(updates[i], updates[i + 1])
