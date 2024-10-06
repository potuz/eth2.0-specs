# ePBS -- The Beacon Chain

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Constants](#constants)
  - [Payload status](#payload-status)
- [Preset](#preset)
  - [Misc](#misc)
  - [Domain types](#domain-types)
  - [Time parameters](#time-parameters)
  - [Max operations per block](#max-operations-per-block)
  - [Execution](#execution)
- [Containers](#containers)
  - [New containers](#new-containers)
    - [`PayloadAttestationData`](#payloadattestationdata)
    - [`PayloadAttestation`](#payloadattestation)
    - [`PayloadAttestationMessage`](#payloadattestationmessage)
    - [`IndexedPayloadAttestation`](#indexedpayloadattestation)
    - [`SignedExecutionPayloadHeader`](#signedexecutionpayloadheader)
    - [`ExecutionPayloadEnvelope`](#executionpayloadenvelope)
    - [`SignedExecutionPayloadEnvelope`](#signedexecutionpayloadenvelope)
    - [`InclusionListSummary`](#inclusionlistsummary)
    - [`SignedInclusionListSummary`](#signedinclusionlistsummary)
    - [`InclusionList`](#inclusionlist)
  - [Modified containers](#modified-containers)
    - [`BeaconBlockBody`](#beaconblockbody)
    - [`ExecutionPayload`](#executionpayload)
    - [`ExecutionPayloadHeader`](#executionpayloadheader)
    - [`BeaconState`](#beaconstate)
- [Helper functions](#helper-functions)
  - [Math](#math)
    - [`bit_floor`](#bit_floor)
  - [Predicates](#predicates)
    - [`is_valid_indexed_payload_attestation`](#is_valid_indexed_payload_attestation)
    - [`is_parent_block_full`](#is_parent_block_full)
  - [Beacon State accessors](#beacon-state-accessors)
    - [`get_ptc`](#get_ptc)
    - [`get_payload_attesting_indices`](#get_payload_attesting_indices)
    - [`get_indexed_payload_attestation`](#get_indexed_payload_attestation)
- [Beacon chain state transition function](#beacon-chain-state-transition-function)
  - [Block processing](#block-processing)
    - [Modified `process_withdrawals`](#modified-process_withdrawals)
    - [New `verify_execution_payload_header_signature`](#new-verify_execution_payload_header_signature)
    - [New `process_execution_payload_header`](#new-process_execution_payload_header)
    - [Modified `process_operations`](#modified-process_operations)
      - [Modified `process_attestation`](#modified-process_attestation)
      - [Payload Attestations](#payload-attestations)
    - [New `verify_execution_payload_envelope_signature`](#new-verify_execution_payload_envelope_signature)
    - [New `verify_inclusion_list_summary_signature`](#new-verify_inclusion_list_summary_signature)
    - [Modified `process_execution_payload`](#modified-process_execution_payload)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

This is the beacon chain specification of the enshrined proposer builder separation feature. 

*Note:* This specification is built upon [Deneb](../../deneb/beacon-chain.md) and is under active development.

This feature adds new staked consensus participants called *Builders* and new honest validators duties called *payload timeliness attestations*. The slot is divided in **four** intervals, one more added to the current three. Honest validators gather *signed bids* from builders and submit their consensus blocks (a `SignedBeaconBlock`) at the beginning of the slot. At the start of the second interval, honest validators submit attestations just as they do previous to this feature). At the  start of the third interval, aggregators aggregate these attestations (exactly as before this feature) and the honest builder reveals the full payload. At the start of the fourth interval, some honest validators selected to be members of the new **Payload Timeliness Committee** attest to the presence of the builder's payload.

At any given slot, the status of the blockchain's head may be either 
- A block from a previous slot (e.g. the current slot's proposer did not submit its block). 
- An *empty* block from the current slot (e.g. the proposer submitted a timely block, but the builder did not reveal the payload on time). 
- A full block for the current slot (both the proposer and the builder revealed on time). 

## Constants

### Payload status

| Name | Value | 
| - | - | 
| `PAYLOAD_ABSENT` | `uint8(0)` |
| `PAYLOAD_PRESENT` | `uint8(1)` | 
| `PAYLOAD_WITHHELD` | `uint8(2)` | 
| `PAYLOAD_INVALID_STATUS` | `uint8(3)` |

## Preset

### Misc

| Name | Value | 
| - | - | 
| `PTC_SIZE` | `uint64(2**9)` (=512) # (New in ePBS) |

### Domain types

| Name | Value |
| - | - |
| `DOMAIN_BEACON_BUILDER`     | `DomainType('0x1B000000')` # (New in ePBS)|
| `DOMAIN_PTC_ATTESTER`       | `DomainType('0x0C000000')` # (New in ePBS)|

### Time parameters

| Name | Value | Unit | Duration |
| - | - | :-: | :-: |
| `MIN_SLOTS_FOR_INCLUSION_LISTS_REQUESTS` | `uint64(2)` | slots | 24 seconds # (New in ePBS) |

### Max operations per block

| Name | Value |
| - | - |
| `MAX_PAYLOAD_ATTESTATIONS` | `2**2` (= 4) # (New in ePBS) |

### Execution
| Name | Value | 
| - | - | 
| MAX_TRANSACTIONS_PER_INCLUSION_LIST | `2**10` (=1024) # (New in ePBS) | 

## Containers

### New containers

#### `PayloadAttestationData`

```python
class PayloadAttestationData(Container):
    beacon_block_root: Root
    slot: Slot
    payload_status: uint8
```

#### `PayloadAttestation`

```python
class PayloadAttestation(Container):
    aggregation_bits: BitVector[PTC_SIZE]
    data: PayloadAttestationData
    signature: BLSSignature
```

#### `PayloadAttestationMessage`

```python
class PayloadAttestationMessage(Container):
    validator_index: ValidatorIndex
    data: PayloadAttestationData
    signature: BLSSignature
```

#### `IndexedPayloadAttestation`

```python
class IndexedPayloadAttestation(Container):
    attesting_indices: List[ValidatorIndex, PTC_SIZE]
    data: PayloadAttestationData
    signature: BLSSignature
```

#### `SignedExecutionPayloadHeader`

```python
class SignedExecutionPayloadHeader(Container):
    message: ExecutionPayloadHeader
    signature: BLSSignature
```
    
#### `ExecutionPayloadEnvelope`

```python
class ExecutionPayloadEnvelope(Container):
    payload: ExecutionPayload
    builder_index: ValidatorIndex
    beacon_block_root: Root
    blob_kzg_commitments: List[KZGCommitment, MAX_BLOB_COMMITMENTS_PER_BLOCK]
    inclusion_list_proposer_index: ValidatorIndex
    inclusion_list_slot: Slot
    inclusion_list_signature: BLSSignature
    payload_withheld: bool
    state_root: Root
```

#### `SignedExecutionPayloadEnvelope`

```python
class SignedExecutionPayloadEnvelope(Container):
    message: ExecutionPayloadEnvelope
    signature: BLSSignature
```

#### `InclusionListSummary`

```python
class InclusionListSummary(Container)
    proposer_index: ValidatorIndex
    slot: Slot
    summary: List[ExecutionAddress, MAX_TRANSACTIONS_PER_INCLUSION_LIST]
```

#### `SignedInclusionListSummary`

```python
class SignedInclusionListSummary(Container):
    message: InclusionListSummary
    signature: BLSSignature
```

#### `InclusionList`

```python
class InclusionList(Container)
    signed_summary: SignedInclusionListSummary
    parent_block_hash: Hash32
    transactions: List[Transaction, MAX_TRANSACTIONS_PER_INCLUSION_LIST]
```

### Modified containers


#### `BeaconBlockBody` 
**Note:** The Beacon Block body is modified to contain a Signed `ExecutionPayloadHeader`. The containers `BeaconBlock` and `SignedBeaconBlock` are modified indirectly.

```python
class BeaconBlockBody(Container):
    randao_reveal: BLSSignature
    eth1_data: Eth1Data  # Eth1 data vote
    graffiti: Bytes32  # Arbitrary data
    # Operations
    proposer_slashings: List[ProposerSlashing, MAX_PROPOSER_SLASHINGS]
    attester_slashings: List[AttesterSlashing, MAX_ATTESTER_SLASHINGS]
    attestations: List[Attestation, MAX_ATTESTATIONS]
    deposits: List[Deposit, MAX_DEPOSITS]
    voluntary_exits: List[SignedVoluntaryExit, MAX_VOLUNTARY_EXITS]
    sync_aggregate: SyncAggregate
    # Execution
    # Removed execution_payload [Removed in ePBS]
    # Removed blob_kzg_commitments [Removed in ePBS]
    bls_to_execution_changes: List[SignedBLSToExecutionChange, MAX_BLS_TO_EXECUTION_CHANGES]
    # PBS
    signed_execution_payload_header: SignedExecutionPayloadHeader  # [New in ePBS]
    payload_attestations: List[PayloadAttestation, MAX_PAYLOAD_ATTESTATIONS] # [New in ePBS]
```

#### `ExecutionPayload`

**Note:** The `ExecutionPayload` is modified to contain a transaction inclusion list summary signed by the corresponding beacon block proposer.

```python
class ExecutionPayload(Container):
    # Execution block header fields
    parent_hash: Hash32
    fee_recipient: ExecutionAddress  # 'beneficiary' in the yellow paper
    state_root: Bytes32
    receipts_root: Bytes32
    logs_bloom: ByteVector[BYTES_PER_LOGS_BLOOM]
    prev_randao: Bytes32  # 'difficulty' in the yellow paper
    block_number: uint64  # 'number' in the yellow paper
    gas_limit: uint64
    gas_used: uint64
    timestamp: uint64
    extra_data: ByteList[MAX_EXTRA_DATA_BYTES]
    base_fee_per_gas: uint256
    # Extra payload fields
    block_hash: Hash32  # Hash of execution block
    transactions: List[Transaction, MAX_TRANSACTIONS_PER_PAYLOAD]
    withdrawals: List[Withdrawal, MAX_WITHDRAWALS_PER_PAYLOAD]
    blob_gas_used: uint64
    excess_blob_gas: uint64
    inclusion_list_summary: List[ExecutionAddress, MAX_TRANSACTIONS_PER_INCLUSION_LIST]# [New in ePBS]
```

#### `ExecutionPayloadHeader`

**Note:** The `ExecutionPayloadHeader` is modified to only contain the block hash of the committed `ExecutionPayload` in addition to the builder's payment information and KZG commitments root to verify the inclusion proofs. 

```python
class ExecutionPayloadHeader(Container):
    parent_block_hash: Hash32
    parent_block_root: Root
    block_hash: Hash32
    builder_index: ValidatorIndex
    slot: Slot
    value: Gwei
    blob_kzg_commitments_root: Root
```

#### `BeaconState`
*Note*: the beacon state is modified to store a signed latest execution payload header, and to track the last withdrawals honored in the CL. It is also modified to no longer store the full last execution payload header but rather only the last block hash and the last slot that was full, that is in which there were both consensus and execution blocks included. 

```python
class BeaconState(Container):
    # Versioning
    genesis_time: uint64
    genesis_validators_root: Root
    slot: Slot
    fork: Fork
    # History
    latest_block_header: BeaconBlockHeader
    block_roots: Vector[Root, SLOTS_PER_HISTORICAL_ROOT]
    state_roots: Vector[Root, SLOTS_PER_HISTORICAL_ROOT]
    historical_roots: List[Root, HISTORICAL_ROOTS_LIMIT]  # Frozen in Capella, replaced by historical_summaries
    # Eth1
    eth1_data: Eth1Data
    eth1_data_votes: List[Eth1Data, EPOCHS_PER_ETH1_VOTING_PERIOD * SLOTS_PER_EPOCH]
    eth1_deposit_index: uint64
    # Registry
    validators: List[Validator, VALIDATOR_REGISTRY_LIMIT]
    balances: List[Gwei, VALIDATOR_REGISTRY_LIMIT]
    # Randomness
    randao_mixes: Vector[Bytes32, EPOCHS_PER_HISTORICAL_VECTOR]
    # Slashings
    slashings: Vector[Gwei, EPOCHS_PER_SLASHINGS_VECTOR]  # Per-epoch sums of slashed effective balances
    # Participation
    previous_epoch_participation: List[ParticipationFlags, VALIDATOR_REGISTRY_LIMIT]
    current_epoch_participation: List[ParticipationFlags, VALIDATOR_REGISTRY_LIMIT]
    # Finality
    justification_bits: Bitvector[JUSTIFICATION_BITS_LENGTH]  # Bit set for every recent justified epoch
    previous_justified_checkpoint: Checkpoint
    current_justified_checkpoint: Checkpoint
    finalized_checkpoint: Checkpoint
    # Inactivity
    inactivity_scores: List[uint64, VALIDATOR_REGISTRY_LIMIT]
    # Sync
    current_sync_committee: SyncCommittee
    next_sync_committee: SyncCommittee
    # Execution
    # latest_execution_payload_header: ExecutionPayloadHeader # [Removed in ePBS]
    execution_payload_header: ExecutionPayloadHeader # [New in ePBS]
    # Withdrawals
    next_withdrawal_index: WithdrawalIndex
    next_withdrawal_validator_index: ValidatorIndex
    # Deep history valid from Capella onwards
    historical_summaries: List[HistoricalSummary, HISTORICAL_ROOTS_LIMIT]
    # PBS
    previous_inclusion_list_proposer: ValidatorIndex # [New in ePBS]
    previous_inclusion_list_slot: Slot # [New in ePBS]
    latest_inclusion_list_proposer: ValidatorIndex # [New in ePBS]
    latest_inclusion_list_slot: Slot # [New in ePBS]
    latest_block_hash: Hash32 # [New in ePBS]
    latest_full_slot: Slot # [New in ePBS]
    last_withdrawals_root: Root # [New in ePBS]
```

## Helper functions

### Math

#### `bit_floor`

```python
def bit_floor(n: uint64) -> uint64:
    """
    if ``n`` is not zero, returns the largest power of `2` that is not greater than `n`.
    """
    if n == 0:
        return 0
    return uint64(1) << (n.bit_length() - 1)
```
    
### Predicates

#### `is_valid_indexed_payload_attestation`

```python
def is_valid_indexed_payload_attestation(state: BeaconState, indexed_payload_attestation: IndexedPayloadAttestation) -> bool:
    """
    Check if ``indexed_payload_attestation`` is not empty, has sorted and unique indices and has a valid aggregate signature.
    """
    # Verify the data is valid
    if indexed_payload_attestation.data.payload_status >= PAYLOAD_INVALID_STATUS:
        return False

    # Verify indices are sorted and unique
    indices = indexed_payload_attestation.attesting_indices
    if len(indices) == 0 or not indices == sorted(set(indices)):
        return False
    # Verify aggregate signature
    pubkeys = [state.validators[i].pubkey for i in indices]
    domain = get_domain(state, DOMAIN_PTC_ATTESTER, None)
    signing_root = compute_signing_root(indexed_payload_attestation.data, domain)
    return bls.FastAggregateVerify(pubkeys, signing_root, indexed_payload_attestation.signature)
```

#### `is_parent_block_full`

This function returns true if the last committed payload header was fulfilled with a payload, this can only happen when both beacon block and payload were present. This function must be called on a beacon state before processing the execution payload header in the block. 

```python
def is_parent_block_full(state: BeaconState) -> bool:
    return state.execution_payload_header.block_hash == state.latest_block_hash
```

### Beacon State accessors

#### `get_ptc`

```python
def get_ptc(state: BeaconState, slot: Slot) -> Vector[ValidatorIndex, PTC_SIZE]:
    """
    Get the ptc committee for the given ``slot``
    """
    epoch = compute_epoch_at_slot(slot)
    committees_per_slot = bit_floor(min(get_committee_count_per_slot(state, epoch), PTC_SIZE))
    members_per_committee = PTC_SIZE // committees_per_slot
    
    validator_indices = [] 
    for idx in range(committees_per_slot):
        beacon_committee = get_beacon_committee(state, slot, idx)
        validator_indices += beacon_committee[:members_per_committee]
    return validator_indices
```

#### `get_payload_attesting_indices`

```python
def get_payload_attesting_indices(state: BeaconState, slot: Slot, 
                                  payload_attestation: PayloadAttestation) -> Set[ValidatorIndex]:
    """
    Return the set of attesting indices corresponding to ``payload_attestation``.
    """
    ptc = get_ptc(state, slot)
    return set(index for i, index in enumerate(ptc) if payload_attestation.aggregation_bits[i])
```


#### `get_indexed_payload_attestation`

```python
def get_indexed_payload_attestation(state: BeaconState, slot: Slot, 
                                    payload_attestation: PayloadAttestation) -> IndexedPayloadAttestation:
    """
    Return the indexed payload attestation corresponding to ``payload_attestation``.
    """
    attesting_indices = get_payload_attesting_indices(state, slot, payload_attestation)

    return IndexedPayloadAttestation(
        attesting_indices=sorted(attesting_indices),
        data=payload_attestation.data,
        signature=payload_attestation.signature,
    )
```

## Beacon chain state transition function

*Note*: state transition is fundamentally modified in ePBS. The full state transition is broken in two parts, first importing a signed block and then importing an execution payload.

The post-state corresponding to a pre-state `state` and a signed block `signed_block` is defined as `state_transition(state, signed_block)`. State transitions that trigger an unhandled exception (e.g. a failed `assert` or an out-of-range list access) are considered invalid. State transitions that cause a `uint64` overflow or underflow are also considered invalid. 

The post-state corresponding to a pre-state `state` and a signed execution payload `signed_execution_payload` is defined as `process_execution_payload(state, signed_execution_payload)`. State transitions that trigger an unhandled exception (e.g. a failed `assert` or an out-of-range list access) are considered invalid. State transitions that cause a `uint64` overflow or underflow are also considered invalid. 

### Block processing

*Note*: the function `process_block` is modified to only process the consensus block. The full state-transition process is broken into separate functions, one to process a `BeaconBlock` and another to process a `SignedExecutionPayload`. Notice that withdrawals are now included in the beacon block, they are processed before the execution payload header as this header may affect validator balances.


```python
def process_block(state: BeaconState, block: BeaconBlock) -> None:
    process_block_header(state, block)
    process_withdrawals(state) [Modified in ePBS]
    process_execution_payload_header(state, block) # [Modified in ePBS, removed process_execution_payload]
    process_randao(state, block.body)
    process_eth1_data(state, block.body)
    process_operations(state, block.body)  # [Modified in ePBS]
    process_sync_aggregate(state, block.body.sync_aggregate)
```

#### Modified `process_withdrawals`
**Note:** This is modified to take only the `state` parameter. The payload is required to honor these withdrawals.

```python
def process_withdrawals(state: BeaconState) -> None:
    ## return early if the parent block was empty
    if not is_parent_block_full(state):
        return

    withdrawals = get_expected_withdrawals(state)
    state.last_withdrawals_root = hash_tree_root(withdrawals)
    for withdrawal in withdrawals:
        decrease_balance(state, withdrawal.validator_index, withdrawal.amount)

    # Update the next withdrawal index if this block contained withdrawals
    if len(withdrawals) != 0:
        latest_withdrawal = withdrawals[-1]
        state.next_withdrawal_index = WithdrawalIndex(latest_withdrawal.index + 1)

    # Update the next validator index to start the next withdrawal sweep
    if len(withdrawals) == MAX_WITHDRAWALS_PER_PAYLOAD:
        # Next sweep starts after the latest withdrawal's validator index
        next_validator_index = ValidatorIndex((withdrawals[-1].validator_index + 1) % len(state.validators))
        state.next_withdrawal_validator_index = next_validator_index
    else:
        # Advance sweep by the max length of the sweep if there was not a full set of withdrawals
        next_index = state.next_withdrawal_validator_index + MAX_VALIDATORS_PER_WITHDRAWALS_SWEEP
        next_validator_index = ValidatorIndex(next_index % len(state.validators))
        state.next_withdrawal_validator_index = next_validator_index
```

#### New `verify_execution_payload_header_signature`

```python
def verify_execution_payload_header_signature(state: BeaconState, 
                                           signed_header: SignedExecutionPayloadHeader) -> bool:
    # Check the signature
    builder = state.validators[signed_header.message.builder_index]
    signing_root = compute_signing_root(signed_header.message, get_domain(state, DOMAIN_BEACON_BUILDER))
    return bls.Verify(builder.pubkey, signing_root, signed_header.signature)
```

#### New `process_execution_payload_header`

```python
def process_execution_payload_header(state: BeaconState, block: BeaconBlock) -> None:
    # Verify the header signature
    signed_header = block.body.signed_execution_payload_header
    assert verify_execution_payload_header_signature(state, signed_header)

    # Check that the builder has funds to cover the bid
    header = signed_header.message
    builder_index = header.builder_index
    amount = header.value
    assert state.balances[builder_index] >= amount

    # Verify that the bid is for the current slot
    assert header.slot == block.slot
    # Verify that the bid is for the right parent block
    assert header.parent_block_hash == state.latest_block_hash
    assert header.parent_block_root == block.parent_root

    # Transfer the funds from the builder to the proposer
    decrease_balance(state, builder_index, amount)
    increase_balance(state, block.proposer_index, amount)

    # Cache the inclusion list proposer if the parent block was full
    if is_parent_block_full(state):
        state.latest_inclusion_list_proposer = block.proposer_index
        state.latest_inclusion_list_slot = block.slot
    # Cache the signed execution payload header 
    state.execution_payload_header = header
```


#### Modified `process_operations`

**Note:** `process_operations` is modified to process PTC attestations

```python
def process_operations(state: BeaconState, body: BeaconBlockBody) -> None:
    # Verify that outstanding deposits are processed up to the maximum number of deposits
    assert len(body.deposits) == min(MAX_DEPOSITS, state.eth1_data.deposit_count - state.eth1_deposit_index)

    def for_ops(operations: Sequence[Any], fn: Callable[[BeaconState, Any], None]) -> None:
        for operation in operations:
            fn(state, operation)

    for_ops(body.proposer_slashings, process_proposer_slashing)
    for_ops(body.attester_slashings, process_attester_slashing)
    for_ops(body.attestations, process_attestation) # [Modified in ePBS]
    for_ops(body.deposits, process_deposit)
    for_ops(body.voluntary_exits, process_voluntary_exit)
    for_ops(body.bls_to_execution_changes, process_bls_to_execution_change)
    for_ops(body.payload_attestations, process_payload_attestation) # [New in ePBS]
```

##### Modified `process_attestation`

*Note*: The function `process_attestation` is modified to ignore attestations from the ptc

```python
def process_attestation(state: BeaconState, attestation: Attestation) -> None:
    data = attestation.data
    assert data.target.epoch in (get_previous_epoch(state), get_current_epoch(state))
    assert data.target.epoch == compute_epoch_at_slot(data.slot)
    assert data.slot + MIN_ATTESTATION_INCLUSION_DELAY <= state.slot <= data.slot + SLOTS_PER_EPOCH
    assert data.index < get_committee_count_per_slot(state, data.target.epoch)

    committee = get_beacon_committee(state, data.slot, data.index)
    assert len(attestation.aggregation_bits) == len(committee)

    # Participation flag indices
    participation_flag_indices = get_attestation_participation_flag_indices(state, data, state.slot - data.slot)

    # Verify signature
    assert is_valid_indexed_attestation(state, get_indexed_attestation(state, attestation))

    # Update epoch participation flags
    if data.target.epoch == get_current_epoch(state):
        epoch_participation = state.current_epoch_participation
    else:
        epoch_participation = state.previous_epoch_participation

    ptc = get_ptc(state, data.slot)
    attesting_indices = [i for i in get_attesting_indices(state, data, attestation.aggregation_bits) if i not in ptc]
    proposer_reward_numerator = 0
    for index in attesting_indices:
        for flag_index, weight in enumerate(PARTICIPATION_FLAG_WEIGHTS):
            if flag_index in participation_flag_indices and not has_flag(epoch_participation[index], flag_index):
                epoch_participation[index] = add_flag(epoch_participation[index], flag_index)
                proposer_reward_numerator += get_base_reward(state, index) * weight

    # Reward proposer
    proposer_reward_denominator = (WEIGHT_DENOMINATOR - PROPOSER_WEIGHT) * WEIGHT_DENOMINATOR // PROPOSER_WEIGHT
    proposer_reward = Gwei(proposer_reward_numerator // proposer_reward_denominator)
    increase_balance(state, get_beacon_proposer_index(state), proposer_reward)
```

##### Payload Attestations

```python
def remove_flag(flags: ParticipationFlags, flag_index: int) -> ParticipationFlags:
    flag = ParticipationFlags(2**flag_index)
    return flags & ~flag
``` 

```python
def process_payload_attestation(state: BeaconState, payload_attestation: PayloadAttestation) -> None:
    ## Check that the attestation is for the parent beacon block
    data = payload_attestation.data
    assert data.beacon_block_root == state.latest_block_header.parent_root
    ## Check that the attestation is for the previous slot
    assert data.slot + 1 == state.slot 

    #Verify signature
    indexed_payload_attestation = get_indexed_payload_attestation(state, data.slot, payload_attestation)
    assert is_valid_indexed_payload_attestation(state, indexed_payload_attestation)

    ptc = get_ptc(state, data.slot)
    if state.slot % SLOTS_PER_EPOCH == 0:
        epoch_participation = state.previous_epoch_participation
    else:
        epoch_participation = state.current_epoch_participation

    # Return early if the attestation is for the wrong payload status
    payload_was_present = data.slot == state.latest_full_slot
    voted_present = data.payload_status == PAYLOAD_PRESENT
    proposer_reward_denominator = (WEIGHT_DENOMINATOR - PROPOSER_WEIGHT) * WEIGHT_DENOMINATOR // PROPOSER_WEIGHT
    proposer_index = get_beacon_proposer_index(state)
    if voted_present != payload_was_present:
        # Unset the flags in case they were set by an equivocating ptc attestation
        proposer_penalty_numerator = 0
        for index in indexed_payload_attestation.attesting_indices:
            for flag_index, weight in enumerate(PARTICIPATION_FLAG_WEIGHTS):
                if has_flag(epoch_participation[index], flag_index):
                    epoch_participation[index] = remove_flag(epoch_participation[index], flag_index)
                    proposer_penalty_numerator += get_base_reward(state, index) * weight
        # Penalize the proposer
        proposer_penalty = Gwei(2*proposer_penalty_numerator // proposer_reward_denominator)
        decrease_balance(state, proposer_index, proposer_penalty)
        return

    # Reward the proposer and set all the participation flags in case of correct attestations
    proposer_reward_numerator = 0
    for index in indexed_payload_attestation.attesting_indices:
        for flag_index, weight in enumerate(PARTICIPATION_FLAG_WEIGHTS):
            if not has_flag(epoch_participation[index], flag_index):
                epoch_participation[index] = add_flag(epoch_participation[index], flag_index)
                proposer_reward_numerator += get_base_reward(state, index) * weight

    # Reward proposer
    proposer_reward = Gwei(proposer_reward_numerator // proposer_reward_denominator)
    increase_balance(state, proposer_index, proposer_reward)
```

#### New `verify_execution_payload_envelope_signature`

```python
def verify_execution_payload_envelope_signature(state: BeaconState, signed_envelope: SignedExecutionPayloadEnvelope) -> bool:
    builder = state.validators[signed_envelope.message.builder_index]
    signing_root = compute_signing_root(signed_envelope.message, get_domain(state, DOMAIN_BEACON_BUILDER))
    return bls.Verify(builder.pubkey, signing_root, signed_envelope.signature)
```

#### New `verify_inclusion_list_summary_signature`

```python
def verify_inclusion_list_summary_signature(state: BeaconState, signed_summary: SignedInclusionListSummary) -> bool:
    summary = signed_summary.message
    signing_root = compute_signing_root(summary, get_domain(state, DOMAIN_BEACON_PROPOSER))
    proposer = state.validators[summary.proposer_index]
    return bls.Verify(proposer.pubkey, signing_root, signed_summary.signature)
```

#### Modified `process_execution_payload`
*Note*: `process_execution_payload` is now an independent check in state transition. It is called when importing a signed execution payload proposed by the builder of the current slot.

```python
def process_execution_payload(state: BeaconState, signed_envelope: SignedExecutionPayloadEnvelope, execution_engine: ExecutionEngine, verify = True) -> None:
    # Verify signature
    if verify: 
        assert verify_execution_payload_envelope_signature(state, signed_envelope)
    envelope = signed_envelope.message
    payload = envelope.payload
    # Verify the withdrawals root
    assert hash_tree_root(payload.withdrawals) == state.last_withdrawals_root
    # Verify inclusion list proposer and slot
    assert envelope.inclusion_list_proposer_index == state.previous_inclusion_list_proposer
    assert envelope.inclusion_list_slot == state.previous_inclusion_list_slot
    # Verify inclusion list summary signature
    signed_summary = SignedInclusionListSummary(
        message=InclusionListSummary(
            proposer_index=envelope.inclusion_list_proposer_index,
            slot = envelope.inclusion_list_slot,
            summary=payload.inclusion_list_summary),
        signature=envelope.inclusion_list_signature)
    assert verify_inclusion_list_summary_signature(state, signed_summary)
    # Verify consistency with the beacon block
    assert envelope.beacon_block_root == hash_tree_root(state.latest_block_header)
    # Verify consistency with the committed header
    committed_header = state.execution_payload_header
    assert committed_header.block_hash == payload.block_hash 
    assert committed_header.blob_kzg_commitments_root == hash_tree_root(envelope.blob_kzg_commitments)
    assert envelope.builder_index == committed_header.builder_index
    # Verify consistency of the parent hash with respect to the previous execution payload
    assert payload.parent_hash == state.latest_block_hash
    # Verify prev_randao
    assert payload.prev_randao == get_randao_mix(state, get_current_epoch(state))
    # Verify timestamp
    assert payload.timestamp == compute_timestamp_at_slot(state, state.slot)
    # Verify the execution payload is valid
    versioned_hashes = [kzg_commitment_to_versioned_hash(commitment) for commitment in envelope.blob_kzg_commitments]
    assert execution_engine.verify_and_notify_new_payload(
        NewPayloadRequest(
            execution_payload=payload,
            versioned_hashes=versioned_hashes,
            parent_beacon_block_root=state.latest_block_header.parent_root,
        )
    )
    # Cache the execution payload header and proposer
    state.latest_block_hash = payload.block_hash
    state.latest_full_slot = state.slot
    state.previous_inclusion_list_proposer = state.latest_inclusion_list_proposer
    state.previous_inclusion_list_slot = state.latest_inclusion_list_slot
    # Verify the state root
    if verify: 
        assert envelope.state_root == hash_tree_root(state)
```
