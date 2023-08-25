# ePBS -- Fork Choice

## Table of contents
<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

This is the modification of the fork choice accompanying the ePBS upgrade.

## Helpers

### `verify_inclusion_list`
*[New in ePBS]*

```python
def verify_inclusion_list(state: BeaconState, block: BeaconBlock, inclusion_list: InclusionList, execution_engine: ExecutionEngine) -> bool:
    """
    returns true if the inclusion list is valid. 
    """
    # Check that the inclusion list corresponds to the block proposer
    signed_summary = inclusion_list.summary
    proposer_index = signed_summary.message.proposer_index
    assert block.proposer_index == proposer_index

    # TODO: These checks will also be performed by the EL surely so we can probably remove them from here.
    # Check the summary and transaction list lengths
    summary = signed_summary.message.summary
    assert len(summary) <= MAX_TRANSACTIONS_PER_INCLUSION_LIST
    assert len(inclusion_list.transactions) == len(summary)

    # TODO: These checks will also be performed by the EL surely so we can probably remove them from here.
    # Check that the total gas limit is bounded
    total_gas_limit = sum( entry.gas_limit for entry in summary)
    assert total_gas_limit <= MAX_GAS_PER_INCLUSION_LIST

    # Check that the signature is correct
    # TODO: do we need a new domain?
    signing_root = compute_signing_root(signed_summary.message, get_domain(state, DOMAIN_BEACON_PROPOSER))
    proposer = state.validators[proposer_index]
    assert bls.Verify(proposer.pubkey, signing_root, signed_summary.signature)
   
    # Check that the inclusion list is valid
    return execution_engine.notify_new_inclusion_list(inclusion_list) 
```

### `is_inclusion_list_available`
*[New in ePBS]*

```python
def is_inclusion_list_available(state: BeaconState, block: BeaconBlock) -> bool:
    """
    Returns whether one inclusion list for the corresponding block was seen in full and has been validated. 
    There is one exception if the parent consensus block did not contain an exceution payload, in which case
    We return true early

    `retrieve_inclusion_list` is implementation and context dependent
    It returns one inclusion list that was broadcasted during the given slot by the given proposer. 
    Note: the p2p network does not guarantee sidecar retrieval outside of
    `MIN_SLOTS_FOR_INCLUSION_LISTS_REQUESTS`
    """
    # Verify that the list is empty if the parent consensus block did not contain a payload
    if state.current_signed_execution_payload_header.message != state.latest_execution_payload_header:
        return true

    # verify the inclusion list
    inclusion_list = retrieve_inclusion_list(block.slot, block.proposer_index)
    return verify_inclusion_list(state, block, inclusion_list, EXECUTION_ENGINE)
```
    

## Updated fork-choice handlers

### `on_block`

*Note*: The handler `on_block` is modified to consider the pre `state` of the given consensus beacon block depending not only on the parent block root, but also on the parent blockhash. There is also the addition of the inclusion list availability check.

```python
def on_block(store: Store, signed_block: SignedBeaconBlock) -> None:
    """
    Run ``on_block`` upon receiving a new block.
    """
    block = signed_block.message
    # Parent block must be known
    assert block.parent_root in store.block_states

    # Check if this blocks builds on empty or full parent block
    parent_block = store.blocks[block.parent_root]
    parent_signed_payload_header = parent_block.body.signed_execution_payload_header
    parent_payload_hash = paernt_signed_payload_header.message.block_hash
    current_signed_payload_header = block.body.signed_execution_payload_header
    current_payload_parent_hash = current_signed_payload_header.message.parent_hash
    # Make a copy of the state to avoid mutability issues
    if current_payload_parent_hash == parent_payload_hash:
        assert block.parent_root in store.execution_payload_states
        state = copy(store.execution_payload_states[block.parent_root])
    else:
        state = copy(store.block_states[block.parent_root])

    # Blocks cannot be in the future. If they are, their consideration must be delayed until they are in the past.
    current_slot = get_current_slot(store)
    assert current_slot >= block.slot

    # Check that block is later than the finalized epoch slot (optimization to reduce calls to get_ancestor)
    finalized_slot = compute_start_slot_at_epoch(store.finalized_checkpoint.epoch)
    assert block.slot > finalized_slot
    # Check block is a descendant of the finalized block at the checkpoint finalized slot
    finalized_checkpoint_block = get_checkpoint_block(
        store,
        block.parent_root,
        store.finalized_checkpoint.epoch,
    )
    assert store.finalized_checkpoint.root == finalized_checkpoint_block

    # Check if blob data is available
    # If not, this block MAY be queued and subsequently considered when blob data becomes available
    assert is_data_available(hash_tree_root(block), block.body.blob_kzg_commitments)

    # Check if there is a valid inclusion list. 
    # This check is performed only if the block's slot is within the visibility window
    # If not, this block MAY be queued and subsequently considered when a valid inclusion list becomes available
    if block.slot + MIN_SLOTS_FOR_INCLUSION_LISTS_REQUESTS >= current_slot:
        assert is_inclusion_list_available(state, block)

    # Check the block is valid and compute the post-state
    block_root = hash_tree_root(block)
    state_transition(state, signed_block, True)

    # Add new block to the store
    store.blocks[block_root] = block
    # Add new state for this block to the store
    store.block_states[block_root] = state

    # Add proposer score boost if the block is timely
    time_into_slot = (store.time - store.genesis_time) % SECONDS_PER_SLOT
    is_before_attesting_interval = time_into_slot < SECONDS_PER_SLOT // INTERVALS_PER_SLOT
    if get_current_slot(store) == block.slot and is_before_attesting_interval:
        store.proposer_boost_root = hash_tree_root(block)

    # Update checkpoints in store if necessary
    update_checkpoints(store, state.current_justified_checkpoint, state.finalized_checkpoint)

    # Eagerly compute unrealized justification and finality.
    compute_pulled_up_tip(store, block_root)
```

## New fork-choice handlers

### `on_execution_payload`

```python
def on_excecution_payload(store: Store, signed_envelope_: SignedExecutionPayloadEnvelope) -> None:
    """
    Run ``on_execution_payload`` upon receiving a new execution payload.
    """
    beacon_block_root = signed_envelope.beacon_block_root
    # The corresponding beacon block root needs to be known
    assert beacon_block_root in store.block_states

    # Make a copy of the state to avoid mutability issues
    state = copy(store.block_states[beacon_block_root])

    # Process the execution payload
    process_execution_payload(state, signed_envelope, EXECUTION_ENGINE)

    #Add new state for this payload to the store
    store.execution_payload_states[beacon_block_root] = state
```   
