# ePBS -- The Beacon Chain

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Constants](#constants)
  - [Withdrawal prefixes](#withdrawal-prefixes)
- [Configuration](#configuration)
  - [Time parameters](#time-parameters)
- [Preset](#preset)
  - [Misc](#misc)
  - [Domain types](#domain-types)
  - [Gwei values](#gwei-values)
  - [Time parameters](#time-parameters-1)
  - [Rewards and penalties](#rewards-and-penalties)
  - [Incentivization weights](#incentivization-weights)
  - [Execution](#execution)
- [Containers](#containers)
  - [New containers](#new-containers)
    - [`SignedExecutionPayloadHeader`](#signedexecutionpayloadheader)
    - [`ExecutionPayloadEnvelope`](#executionpayloadenvelope)
    - [`SignedExecutionPayloadEnvelope`](#signedexecutionpayloadenvelope)
    - [`InclusionListSummaryEntry`](#inclusionlistsummaryentry)
    - [`InclusionListSummary`](#inclusionlistsummary)
    - [`SignedInclusionListSummary`](#signedinclusionlistsummary)
    - [`InclusionList`](#inclusionlist)
  - [Modified containers](#modified-containers)
    - [`BeaconBlockBody`](#beaconblockbody)
    - [`ExecutionPayload`](#executionpayload)
    - [`ExecutionPayloadHeader`](#executionpayloadheader)
    - [`BeaconState`](#beaconstate)
- [Helper functions](#helper-functions)
  - [Predicates](#predicates)
    - [`is_builder`](#is_builder)
- [Beacon chain state transition function](#beacon-chain-state-transition-function)
  - [Epoch processing](#epoch-processing)
    - [Modified `process_epoch`](#modified-process_epoch)
  - [Execution engine](#execution-engine)
    - [Request data](#request-data)
      - [New `NewInclusionListRequest`](#new-newinclusionlistrequest)
    - [Engine APIs](#engine-apis)
    - [New `notify_new_inclusion_list`](#new-notify_new_inclusion_list)
  - [Block processing](#block-processing)
    - [Modified `process_withdrawals`](#modified-process_withdrawals)
    - [New `verify_execution_payload_header_signature`](#new-verify_execution_payload_header_signature)
    - [New `process_execution_payload_header`](#new-process_execution_payload_header)
    - [New `verify_execution_payload_signature`](#new-verify_execution_payload_signature)
    - [Modified `process_execution_payload`](#modified-process_execution_payload)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

This is the beacon chain specification of the enshrined proposer builder separation feature. 

*Note:* This specification is built upon [Deneb](../../deneb/beacon-chain.md) and is under active development.

This feature adds new staked consensus participants called *Builders* and new honest validators duties called *payload timeliness attestations*. The slot is divided in **four** intervals as opposed to the current three. Honest validators gather *signed bids* from builders and submit their consensus blocks (a `SignedBlindedBeaconBlock`) at the beginning of the slot. At the start of the second interval, honest validators submit attestations just as they do previous to this feature). At the  start of the third interval, aggregators aggregate these attestations (exactly as before this feature) and the honest builder reveals the full payload. At the start of the fourth interval, some honest validators selected to be members of the new **Payload Timeliness Committee** attest to the presence of the builder's payload.

At any given slot, the status of the blockchain's head may be either 
- A *full* block from a previous slot (eg. the current slot's proposer did not submit its block). 
- An *empty* block from the current slot (eg. the proposer submitted a timely block, but the builder did not reveal the payload on time). 
- A full block for the current slot (both the proposer and the builder revealed on time). 

For a further introduction please refer to this [ethresear.ch article](https://ethresear.ch/t/payload-timeliness-committee-ptc-an-epbs-design/16054)

## Constants 

### Withdrawal prefixes

| Name | Value |
| - | - |
| `BUILDER_WITHDRAWAL_PREFIX` | `Bytes1('0x0b')` # (New in ePBS) |


## Configuration

### Time parameters

| Name | Value | Unit | Duration |
| - | - | :-: | :-: |
| `SECONDS_PER_SLOT` | `uint64(16)` | seconds | 16 seconds # (Modified in ePBS) |

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

### Gwei values

| Name | Value | 
| - | - | 
| `BUILDER_MIN_BALANCE` | `Gwei(2**10 * 10**9)` = (1,024,000,000,000) # (New in ePBS)| 
| `MIN_ACTIVATION_BALANCE` | `Gwei(2**5 * 10**9)` (= 32,000,000,000) # (New in ePBS)|
| `EFFECTIVE_BALANCE_INCREMENT` | `Gwei(2**0 * 10**9)` (= 1,000,000,000)  # (New in ePBS)|
| `MAX_EFFECTIVE_BALANCE` | `Gwei(2**11 * 10**9)` = (2,048,000,000,000) # (Modified in ePBS) |

### Time parameters

| Name | Value | Unit | Duration |
| - | - | :-: | :-: |
| `MIN_SLOTS_FOR_INCLUSION_LISTS_REQUESTS` | `uint64(2)` | slots | 32 seconds # (New in ePBS) |

### Rewards and penalties

| Name | Value |
| - | - |
| `PROPOSER_EQUIVOCATION_PENALTY_FACTOR` | `uint64(2**2)` (= 4) # (New in ePBS)|

### Incentivization weights

| Name | Value | 
| - | - | 
| `PTC_PENALTY_WEIGHT` | `uint64(2)` # (New in ePBS)| 

### Execution
| Name | Value | 
| - | - | 
| MAX_TRANSACTIONS_PER_INCLUSION_LIST | `2**4` (=16) # (New in ePBS) | 
| MAX_GAS_PER_INCLUSION_LIST | `2**21` (=2,097,152) # (New in ePBS) |

## Containers

### New containers

#### `PayloadAttestationData`

```python
class PayloadAttestationData(Container):
    beacon_block_root: Root
    payload_present: bool
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
    beacon_block_root: Root
    state_root: Root
```

#### `SignedExecutionPayloadEnvelope`

```python
class SignedExecutionPayloadEnvelope(Container):
    message: ExecutionPayloadEnvelope
    signature: BLSSignature
```

#### `InclusionListSummaryEntry`

```python
class InclusionListSummaryEntry(Container):
    address: ExecutionAddress
    gas_limit: uint64
```

#### `InclusionListSummary`

```python
class InclusionListSummary(Container)
    proposer_index: ValidatorIndex
    summary: List[InclusionListSummaryEntry, MAX_TRANSACTIONS_PER_INCLUSION_LIST]
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
    summary: SignedInclusionListSummary
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
    # Removed execution_payload [ Removed in ePBS]
    signed_execution_payload_header: SignedExecutionPayloadHeader  # [New in ePBS]
    bls_to_execution_changes: List[SignedBLSToExecutionChange, MAX_BLS_TO_EXECUTION_CHANGES]
    blob_kzg_commitments: List[KZGCommitment, MAX_BLOB_COMMITMENTS_PER_BLOCK]
```

#### `ExecutionPayload`

**Note:** The `ExecutionPayload` is modified to contain the builder's index and the bid value. It also contains a transaction inclusion list summary signed by the corresponding beacon block proposer and the list of indices of transactions in the parent block that have to be excluded from the inclusion list summary because they were satisfied in the previous slot. 

TODO: `builder_index` and `value` do not need to be in the payload sent to the engine, but they need to be in the header committed to the state. Either we move them out here to the envelope and we add them to back when comparing with the committed header, or we keep as here and we will be sending 16 extra bytes to the EL that are ignored. 
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
    builder_index: ValidatorIndex # [New in ePBS]
    value: Gwei # [New in ePBS]
    inclusion_list_summary: SignedInclusionListSummary # [New in ePBS]
    inclusion_list_exclusions: List[uint64, MAX_TRANSACTIONS_PER_INCLUSION_LIST] # [New in ePBS]
```

#### `ExecutionPayloadHeader`

**Note:** The `ExecutionPayloadHeader` is modified to include the builder's index and the bid's value. 

```python
class ExecutionPayloadHeader(Container):
    # Execution block header fields
    parent_hash: Hash32
    fee_recipient: ExecutionAddress
    state_root: Bytes32
    receipts_root: Bytes32
    logs_bloom: ByteVector[BYTES_PER_LOGS_BLOOM]
    prev_randao: Bytes32
    block_number: uint64
    gas_limit: uint64
    gas_used: uint64
    timestamp: uint64
    extra_data: ByteList[MAX_EXTRA_DATA_BYTES]
    base_fee_per_gas: uint256
    # Extra payload fields
    block_hash: Hash32  # Hash of execution block
    transactions_root: Root
    withdrawals_root: Root
    builder_index: ValidatorIndex # [New in ePBS]
    value: Gwei # [New in ePBS]
    inclusion_list_summary_root: Root # [New in ePBS]
    inclusion_list_exclusions_root: Root # [New in ePBS]
```

#### `BeaconState`
*Note*: the beacon state is modified to store a signed latest execution payload header.

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
    latest_execution_payload_header: ExecutionPayloadHeader 
    # Withdrawals
    next_withdrawal_index: WithdrawalIndex
    next_withdrawal_validator_index: ValidatorIndex
    # Deep history valid from Capella onwards
    historical_summaries: List[HistoricalSummary, HISTORICAL_ROOTS_LIMIT]
    # PBS
    current_signed_execution_payload_header: SignedExecutionPayloadHeader # [New in ePBS]
    last_withdrawals_root: Root # [New in ePBS]
```

## Helper functions

### Predicates

#### `is_builder`

```python
def is_builder(validator: Validator) -> bool:
    """
    Check if `validator` is a registered builder
    """
    return validator.withdrawal_credentials[0] == BUILDER_WITHDRAWAL_PREFIX
```

#### `is_valid_indexed_payload_attestation`

```python
def is_valid_indexed_payload_attestation(state: BeaconState, indexed_payload_attestation: IndexedPayloadAttestation) -> bool:
    """
    Check if ``indexed_payload_attestation`` is not empty, has sorted and unique indices and has a valid aggregate signature.
    """
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

### Beacon State accessors

#### `get_ptc`

```python
def get_ptc(state: BeaconState, slot: Slot) -> Vector[ValidatorIndex, PTC_SIZE]:
    """
    Get the ptc committee for the give ``slot``
    """
    beacon_committee = get_beacon_committee(state, slot, 0)[:PTC_SIZE]
    validator_indices = [idx for idx in beacon_committee if not is_builder(idx)]
    return validator_indices[:PTC_SIZE]
```

#### `get_payload_attesting_indices`

```python
def get_payload_attesting_indices(state: BeaconState, 
    slot: Slot, payload_attestation: PayloadAttestation) -> Set[ValidatorIndex]:
    """
    Return the set of attesting indices corresponding to ``payload_attestation``.
    """
    ptc = get_ptc(state, slot)
    return set(index for i, index in enumerate(ptc) if payload_attestation.aggregation_bits[i])
```


#### `get_indexed_payload_attestation`

```python
def get_indexed_payload_attestation(state: BeaconState, 
    slot: Slot, payload_attestation: PayloadAttestation) -> IndexedPayloadAttestation:
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

### Epoch processing

#### Modified `process_epoch`

```python
def process_epoch(state: BeaconState) -> None:
    process_justification_and_finalization(state)
    process_inactivity_updates(state)
    process_rewards_and_penalties(state)
    process_registry_updates(state)
    process_slashings(state)
    process_eth1_data_reset(state)
    process_effective_balance_updates(state)
    process_slashings_reset(state)
    process_randao_mixes_reset(state)
    process_historical_summaries_update(state)
    process_participation_flag_updates(state)
    process_sync_committee_updates(state)
    process_builder_updates(state) # [New in ePBS]
```

### Execution engine

#### Request data

##### New `NewInclusionListRequest`

```python
@dataclass
class NewInclusionListRequest(object):
    inclusion_list: InclusionList
    parent_block_hash: Hash32
```
  
#### Engine APIs

#### New `notify_new_inclusion_list`

```python
def notify_new_inclusion_list(self: ExecutionEngine,
                              inclusion_list_request: NewInclusionListRequest) -> bool:
    """
    Return ``True`` if and only if the transactions in the inclusion list can be succesfully executed
    starting from the execution state corresponding to the `parent_block_hash` in the inclusion list 
    summary. The execution engine also checks that the total gas limit is less or equal that
    ```MAX_GAS_PER_INCLUSION_LIST``, and the transactions in the list of transactions correspond to the signed summary
    """
    ...
```

### Block processing

*Note*: the function `process_block` is modified to only process the consensus block. The full state-transition process is broken into separate functions, one to process a `BeaconBlock` and another to process a `SignedExecutionPayload`. Notice that withdrawals are now included in the beacon block, they are processed before the execution payload header as this header may affect validator balances.


```python
def process_block(state: BeaconState, block: BeaconBlock) -> None:
    process_block_header(state, block)
    process_withdrawals(state) [Modified in ePBS]
    process_execution_payload_header(state, block) # [Modified in ePBS]
    process_randao(state, block.body)
    process_eth1_data(state, block.body)
    process_operations(state, block.body)  # [Modified in ePBS]
    process_sync_aggregate(state, block.body.sync_aggregate)
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
    for_ops(body.attestations, process_attestation)
    for_ops(body.deposits, process_deposit)
    for_ops(body.voluntary_exits, process_voluntary_exit)
    for_ops(body.bls_to_execution_changes, process_bls_to_execution_change)
    for_ops(body.payload_attestations, process_payload_attestation) # [New in ePBS]
```

#### Modified `process_attestation`

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
    for index in attesting_indices
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
def process_payload_attestation(state: BeaconState, payload_attestation: PayloadAttestation) -> None:
    ## Check that the attestation is for the parent beacon block
    data = payload_attestation.data
    assert data.beacon_block_root == state.latest_block_header.parent_root
    ## Check that the attestation is for the previous slot
    assert state.slot > 0
    assert data.beacon_block_root == state.block_roots[(state.slot - 1) % SLOTS_PER_HISTORICAL_ROOT]

    #Verify signature
    indexed_payload_attestation = get_indexed_payload_attestation(state, state.slot - 1, payload_attestation)
    assert is_valid_indexed_payload_attestation(state, indexed_payload_attestation)

    ptc = get_ptc(state, state.slot - 1)
    if slot % SLOTS_PER_EPOCH == 0:
        epoch_participation = state.previous_epoch_participation
    else:
        epoch_participation = state.current_epoch_participation

    # Return early if the attestation is for the wrong payload status
    latest_payload_timestamp = state.latest_execution_payload_header.timestamp
    present_timestamp = compute_timestamp_at_slot(state, state.slot - 1)
    payload_was_present = latest_payload_timestamp == present_timestamp
    if data.payload_present != payload_was_present:
        return
    # Reward the proposer and set all the participation flags
    proposer_reward_numerator = 0
    for index in indexed_payload_attestation.attesting_indices:
        for flag_index, weight in enumerate(PARTICIPATION_FLAG_WEIGHTS):
            if not has_flag(epoch_participation[index], flag_index):
                epoch_participation[index] = add_flag(epoch_participation[index], flag_index)
                proposer_reward_numerator += get_base_reward(state, index) * weight

    # Reward proposer
    proposer_reward_denominator = (WEIGHT_DENOMINATOR - PROPOSER_WEIGHT) * WEIGHT_DENOMINATOR // PROPOSER_WEIGHT
    proposer_reward = Gwei(proposer_reward_numerator // proposer_reward_denominator)
    increase_balance(state, get_beacon_proposer_index(state), proposer_reward)
```

#### Modified `process_withdrawals`
**Note:** TODO: This is modified to take only the State as parameter as they are deterministic. Still need to include the MaxEB changes

```python
def process_withdrawals(state: BeaconState) -> None:
    ## return early if the parent block was empty
     state.current_signed_execution_payload_header.message != state.latest_execution_payload_header:
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
def verify_execution_payload_header_signature(state: BeaconState, signed_header: SignedExecutionPayloadHeader) -> bool:
    # Check the signature
    builder = state.validators[signed_header.message.builder_index]
    signing_root = compute_signing_root(signed_header.message, get_domain(state, DOMAIN_BEACON_BUILDER))
    return bls.Verify(builder.pubkey, signing_root, signed_header.signature)
```

#### New `process_execution_payload_header`

```python
def process_execution_payload_header(state: BeaconState, block: BeaconBlock) -> None:
    signed_header = block.body.signed_execution_payload_header
    assert verify_execution_payload_header_signature(state, signed_header)
    # Check that the builder has funds to cover the bid and transfer the funds
    header = signed_header.message
    builder_index = header.builder_index
    amount = header.value
    assert state.balances[builder_index] >= amount: 
    decrease_balance(state, builder_index, amount)
    increase_balance(state, block.proposer_index, amount)
    # Verify the withdrawals_root against the state cached ones
    assert header.withdrawals_root == state.last_withdrawals_root
    # Verify consistency of the parent hash with respect to the previous execution payload header
    assert header.parent_hash == state.latest_execution_payload_header.block_hash
    # Verify prev_randao
    assert header.prev_randao == get_randao_mix(state, get_current_epoch(state))
    # Verify timestamp
    assert header.timestamp == compute_timestamp_at_slot(state, state.slot)
    # Cache execution payload header
    state.current_signed_execution_payload_header = signed_header
```

#### New `verify_execution_payload_signature`

```python
def verify_execution_envelope_signature(state: BeaconState, signed_envelope: SignedExecutionPayloadEnvelope) -> bool:
    builder = state.validators[signed_envelope.message.payload.builder_index]
    signing_root = compute_signing_root(signed_envelope.message, get_domain(state, DOMAIN_BEACON_BUILDER))
    return bls.Verify(builder.pubkey, signing_root, signed_envelope.signature)
```

#### Modified `process_execution_payload`
*Note*: `process_execution_payload` is now an independent check in state transition. It is called when importing a signed execution payload proposed by the builder of the current slot.

```python
def process_execution_payload(state: BeaconState, signed_envelope: SignedExecutionPayloadEnvelope, execution_engine: ExecutionEngine) -> None:
    # Verify signature [New in ePBS]
    assert verify_execution_envelope_signature(state, signed_envelope)
    payload = signed_envelope.message.payload
    # Verify consistency with the committed header
    hash = hash_tree_root(payload)
    previous_hash = hash_tree_root(state.current_signed_execution_payload_header.message)
    assert hash == previous_hash
    # Verify the execution payload is valid
    versioned_hashes = [kzg_commitment_to_versioned_hash(commitment) for commitment in body.blob_kzg_commitments]
    assert execution_engine.verify_and_notify_new_payload(
        NewPayloadRequest(
            execution_payload=payload,
            versioned_hashes=versioned_hashes,
            parent_beacon_block_root=state.latest_block_header.parent_root,
        )
    )
    # Cache the execution payload header
    state.latest_execution_payload_header = state.current_signed_execution_payload_header.message 
    # Verify the state root
    assert signed_envelope.message.state_root == hash_tree_root(state)
```
