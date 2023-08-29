# ePBS -- Fork Choice

## Table of contents
<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Helpers](#helpers)
  - [`verify_inclusion_list`](#verify_inclusion_list)
  - [`is_inclusion_list_available`](#is_inclusion_list_available)
- [Updated fork-choice handlers](#updated-fork-choice-handlers)
  - [`on_block`](#on_block)
- [New fork-choice handlers](#new-fork-choice-handlers)
  - [`on_execution_payload`](#on_execution_payload)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

This is the modification of the fork choice accompanying the ePBS upgrade.

## Constant

| Name                 | Value       |
| -------------------- | ----------- |
| `PAYLOAD_TIMELY_THRESHOLD` | `PTC_SIZE/2` (=`uint64(256)`) | 

## Helpers

### Modified `Store` 
**Note:** `Store` is modified to track the intermediate states of "empty" consensus blocks, that is, those consensus blocks for which the corresponding execution payload has not been revealed or has not been included on chain. 

```python
@dataclass
class Store(object):
    time: uint64
    genesis_time: uint64
    justified_checkpoint: Checkpoint
    finalized_checkpoint: Checkpoint
    unrealized_justified_checkpoint: Checkpoint
    unrealized_finalized_checkpoint: Checkpoint
    proposer_boost_root: Root
    equivocating_indices: Set[ValidatorIndex]
    blocks: Dict[Root, BeaconBlock] = field(default_factory=dict)
    block_states: Dict[Root, BeaconState] = field(default_factory=dict)
    checkpoint_states: Dict[Checkpoint, BeaconState] = field(default_factory=dict)
    latest_messages: Dict[ValidatorIndex, LatestMessage] = field(default_factory=dict)
    unrealized_justifications: Dict[Root, Checkpoint] = field(default_factory=dict)
    execution_payload_states: Dict[Root, BeaconState] = field(default_factory=dict) # [New in ePBS]
    ptc_vote: Dict[Root, Vector[bool, PTC_SIZE]] = field(default_factory=dict) # [New in ePBS]
```

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

    # Check that the signature is correct
    # TODO: do we need a new domain?
    signing_root = compute_signing_root(signed_summary.message, get_domain(state, DOMAIN_BEACON_PROPOSER))
    proposer = state.validators[proposer_index]
    assert bls.Verify(proposer.pubkey, signing_root, signed_summary.signature)
 
    # TODO: These checks will also be performed by the EL surely so we can probably remove them from here.
    # Check the summary and transaction list lengths
    summary = signed_summary.message.summary
    assert len(summary) <= MAX_TRANSACTIONS_PER_INCLUSION_LIST
    assert len(inclusion_list.transactions) == len(summary)

    # TODO: These checks will also be performed by the EL surely so we can probably remove them from here.
    # Check that the total gas limit is bounded
    total_gas_limit = sum( entry.gas_limit for entry in summary )
    assert total_gas_limit <= MAX_GAS_PER_INCLUSION_LIST
  
    # Check that the inclusion list is valid
    return execution_engine.notify_new_inclusion_list(NewInclusionListRequest(
            inclusion_list=inclusion_list.transactions, 
            summary=inclusion_list.summary.message.summary,
            parent_block_hash = state.latest_execution_payload_header.block_hash))
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
    if state.signed_execution_payload_header_envelope.message.header != state.latest_execution_payload_header:
        return true

    # verify the inclusion list
    inclusion_list = retrieve_inclusion_list(block.slot, block.proposer_index)
    return verify_inclusion_list(state, block, inclusion_list, EXECUTION_ENGINE)
```
    
### `notify_ptc_messages`

```python
def notify_ptc_messages(store: Store, state: BeaconState, payload_attestations: Sequence[PayloadAttestation]) -> None:
    """
    Extracts a list of ``PayloadAttestationMessage`` from ``payload_attestations`` and updates the store with them
    """
    for payload_attestation in payload_attestations:
        indexed_payload_attestation = get_indexed_payload_attestation(state, state.slot - 1, payload_attestation)
        for idx in indexed_payload_attestation.attesting_indices:
            store.on_payload_attestation_message(PayloadAttestationMessage(validator_index=idx,
                    data=payload_attestation.data, signature: BLSSignature(), is_from_block=true)
```

### `is_payload_present`

```python
def is_payload_present(store: Store, beacon_block_root: Root) -> bool:
    """
    return wether the execution payload for the beacon block with root ``beacon_block_root`` was voted as present 
    by the PTC
    """
    # The beacon block root must be known
    assert beacon_block_root in store.ptc_vote
    return ptc_vote[beacon_block_root].count(True) > PAYLOAD_TIMELY_THRESHOLD
```
   
## Updated fork-choice handlers

### `on_block`

*Note*: The handler `on_block` is modified to consider the pre `state` of the given consensus beacon block depending not only on the parent block root, but also on the parent blockhash. There is also the addition of the inclusion list availability check.

In addition we delay the checking of blob availability until the processing of the execution payload. 

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
    parent_signed_payload_header_envelope = parent_block.body.signed_execution_payload_header_envelope
    parent_payload_hash = parent_signed_payload_header_envelope.message.header.block_hash
    current_signed_payload_header_envelope = block.body.signed_execution_payload_header_envelope
    current_payload_parent_hash = current_signed_payload_header_envelope.message.header.parent_hash
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
    # Add a new PTC voting for this block to the store
    store.ptc_vote[block_root] = [False]*PTC_SIZE

    # Notify the store about the payload_attestations in the block
    store.notify_ptc_messages(state, block.body.payload_attestations)

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
def on_excecution_payload(store: Store, signed_envelope: SignedExecutionPayloadEnvelope) -> None:
    """
    Run ``on_execution_payload`` upon receiving a new execution payload.
    """
    envelope = signed_envelope.message 
    # The corresponding beacon block root needs to be known
    assert envelope.beacon_block_root in store.block_states

    # Check if blob data is available
    # If not, this payload MAY be queued and subsequently considered when blob data becomes available
    assert is_data_available(envelope.beacon_block_root, envelope.blob_kzg_commitments)

    # Make a copy of the state to avoid mutability issues
    state = copy(store.block_states[envelope.beacon_block_root])

    # Process the execution payload
    process_execution_payload(state, signed_envelope, EXECUTION_ENGINE)

    #Add new state for this payload to the store
    store.execution_payload_states[beacon_block_root] = state
```   

### `on_payload_attestation_message`

```python
def on_payload_attestation_message(store: Store, 
    ptc_message: PayloadAttestationMessage, is_from_block: bool=False) -> None:
    """
    Run ``on_payload_attestation_message`` upon receiving a new ``ptc_message`` directly on the wire.
    """
    # The beacon block root must be known
    data = ptc_message.data
    # PTC attestation must be for a known block. If block is unknown, delay consideration until the block is found
    state = store.block_states[data.beacon_block_root]
    ptc = get_ptc(state, state.slot)

    # Verify the signature and check that its for the current slot if it is coming from the wire
    if not is_from_block:
        # Check that the attestation is for the current slot
        assert state.slot == get_current_slot(store)
        # Check that the attester is from the current ptc
        assert ptc_message.validator_index in ptc
        # Verify the signature
        assert is_valid_indexed_payload_attestation(state, 
            IndexedPayloadAttestation(attesting_indices = [ptc_message.validator_index], data = data,
                                      signature = ptc_message signature))
    # Update the ptc vote for the block
    # TODO: Do we want to slash ptc members that equivocate? 
    # we are updating here the message and so the last vote will be the one that counts.
    ptc_index = ptc.index(ptc_message.validator_index)
    ptc_vote = store.ptc_vote[data.beacon_block_root]
    ptc_vote[ptc_index] = data.present
```
