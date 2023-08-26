# ePBS -- The Beacon Chain

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

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
| `DOMAIN_BEACON_BUILDER`     | `DomainType('0x0B000000')` # (New in ePBS)|

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

*Note*: the function `process_block` is modified to only process the consensus block. The full state-transition process is broken into separate functions, one to process a `BeaconBlock` and another to process a `SignedExecutionPayload`.  


```python
def process_block(state: BeaconState, block: BeaconBlock) -> None:
    process_block_header(state, block)
    process_execution_payload_header(state, block.body.execution_payload_header) # [Modified in ePBS]
    # Removed process_withdrawal in ePBS is processed during payload processing [Modified in ePBS]
    process_randao(state, block.body)
    process_eth1_data(state, block.body)
    process_operations(state, block.body)  # [Modified in ePBS]
    process_sync_aggregate(state, block.body.sync_aggregate)
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
def process_execution_payload_header(state: BeaconState, signed_header: SignedExecutionPayloadHeader) -> None:
    assert verify_execution_payload_header_signature(state, signed_header)
    # Check that the builder has funds to cover the bid
    header = signed_header.message
    builder_index = header.builder_index
    if state.balances[builder_index] < header.value: 
        return false
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
    # Process Withdrawals in the payload
    process_withdrawals(state, payload)
    # Cache the execution payload header
    state.latest_execution_payload_header = state.current_signed_execution_payload_header.message 
    # Verify the state root
    assert signed_envelope.message.state_root == hash_tree_root(state)
```
