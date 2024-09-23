# ePBS -- The Beacon Chain

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Constants](#constants)
  - [Withdrawal prefixes](#withdrawal-prefixes)
  - [Slashing flags](#slashing-flags)
- [Configuration](#configuration)
  - [Time parameters](#time-parameters)
- [Preset](#preset)
  - [Misc](#misc)
  - [Domain types](#domain-types)
  - [Gwei values](#gwei-values)
  - [Time parameters](#time-parameters-1)
  - [State list lenghts](#state-list-lenghts)
  - [Rewards and penalties](#rewards-and-penalties)
  - [Max operations per block](#max-operations-per-block)
  - [Incentivization weights](#incentivization-weights)
  - [Execution](#execution)
- [Containers](#containers)
  - [New containers](#new-containers)
    - [`PendingBalanceDeposit`](#pendingbalancedeposit)
    - [`PartialWithdrawal`](#partialwithdrawal)
    - [`ExecutionLayerWithdrawRequest`](#executionlayerwithdrawrequest)
    - [`PayloadAttestationData`](#payloadattestationdata)
    - [`PayloadAttestation`](#payloadattestation)
    - [`PayloadAttestationMessage`](#payloadattestationmessage)
    - [`IndexedPayloadAttestation`](#indexedpayloadattestation)
    - [`ExecutionPayloadHeaderEnvelope`](#executionpayloadheaderenvelope)
    - [`SignedExecutionPayloadHeaderEnvelope`](#signedexecutionpayloadheaderenvelope)
    - [`ExecutionPayloadEnvelope`](#executionpayloadenvelope)
    - [`SignedExecutionPayloadEnvelope`](#signedexecutionpayloadenvelope)
    - [`InclusionListSummaryEntry`](#inclusionlistsummaryentry)
    - [`InclusionListSummary`](#inclusionlistsummary)
    - [`SignedInclusionListSummary`](#signedinclusionlistsummary)
    - [`InclusionList`](#inclusionlist)
  - [Modified containers](#modified-containers)
    - [`Validator`](#validator)
    - [`BeaconBlockBody`](#beaconblockbody)
    - [`ExecutionPayload`](#executionpayload)
    - [`ExecutionPayloadHeader`](#executionpayloadheader)
    - [`BeaconState`](#beaconstate)
- [Helper functions](#helper-functions)
  - [Math](#math)
    - [`bit_floor`](#bit_floor)
  - [Predicates](#predicates)
    - [`is_builder`](#is_builder)
    - [`is_eligible_for_activation_queue`](#is_eligible_for_activation_queue)
    - [`is_slashed_proposer`](#is_slashed_proposer)
    - [`is_slashed_attester`](#is_slashed_attester)
    - [Modified `is_slashable_validator`](#modified-is_slashable_validator)
    - [Modified `is_fully_withdrawable_validator`](#modified-is_fully_withdrawable_validator)
    - [`is_partially_withdrawable_validator`](#is_partially_withdrawable_validator)
    - [`is_valid_indexed_payload_attestation`](#is_valid_indexed_payload_attestation)
    - [`is_parent_block_full`](#is_parent_block_full)
  - [Beacon State accessors](#beacon-state-accessors)
    - [Modified `get_eligible_validator_indices`](#modified-get_eligible_validator_indices)
    - [`get_ptc`](#get_ptc)
    - [`get_payload_attesting_indices`](#get_payload_attesting_indices)
    - [`get_indexed_payload_attestation`](#get_indexed_payload_attestation)
    - [`get_validator_excess_balance`](#get_validator_excess_balance)
    - [Modified `get_validator_churn_limit`](#modified-get_validator_churn_limit)
    - [Modified `get_expected_withdrawals`](#modified-get_expected_withdrawals)
  - [Beacon state mutators](#beacon-state-mutators)
    - [`compute_exit_epoch_and_update_churn`](#compute_exit_epoch_and_update_churn)
    - [Modified `initiate_validator_exit`](#modified-initiate_validator_exit)
    - [Modified `slash_validator`](#modified-slash_validator)
- [Genesis](#genesis)
  - [Modified  `initialize_beacon_statre_from_eth1`](#modified--initialize_beacon_statre_from_eth1)
- [Beacon chain state transition function](#beacon-chain-state-transition-function)
  - [Epoch processing](#epoch-processing)
    - [Modified `process_epoch`](#modified-process_epoch)
    - [Helper functions](#helper-functions-1)
      - [Modified `process_registry_updates`](#modified-process_registry_updates)
      - [`process_pending_balance_deposits`](#process_pending_balance_deposits)
      - [Modified `process_effective_balance_updates`](#modified-process_effective_balance_updates)
      - [Modified `process_slashings`](#modified-process_slashings)
      - [Modified `get_unslashed_attesting_indices`](#modified-get_unslashed_attesting_indices)
  - [Execution engine](#execution-engine)
    - [Request data](#request-data)
      - [New `NewInclusionListRequest`](#new-newinclusionlistrequest)
    - [Engine APIs](#engine-apis)
    - [New `notify_new_inclusion_list`](#new-notify_new_inclusion_list)
  - [Block processing](#block-processing)
    - [Modified `process_block_header`](#modified-process_block_header)
    - [Modified `process_operations`](#modified-process_operations)
      - [Modified Proposer slashings](#modified-proposer-slashings)
      - [Modified Attester slashings](#modified-attester-slashings)
      - [Modified `process_attestation`](#modified-process_attestation)
      - [Modified `get_validator_from_deposit`](#modified-get_validator_from_deposit)
      - [Modified `apply_deposit`](#modified-apply_deposit)
      - [Payload Attestations](#payload-attestations)
      - [Execution Layer Withdraw Requests](#execution-layer-withdraw-requests)
    - [Modified `process_withdrawals`](#modified-process_withdrawals)
    - [New `verify_execution_payload_header_envelope_signature`](#new-verify_execution_payload_header_envelope_signature)
    - [New `process_execution_payload_header`](#new-process_execution_payload_header)
    - [New `verify_execution_payload_signature`](#new-verify_execution_payload_signature)
    - [New `verify_inclusion_list_summary_signature`](#new-verify_inclusion_list_summary_signature)
    - [Modified `process_execution_payload`](#modified-process_execution_payload)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

This is the beacon chain specification of the enshrined proposer builder separation feature. 

*Note:* This specification is built upon [Deneb](../../deneb/beacon-chain.md) and is under active development.

This feature adds new staked consensus participants called *Builders* and new honest validators duties called *payload timeliness attestations*. The slot is divided in **four** intervals as opposed to the current three. Honest validators gather *signed bids* from builders and submit their consensus blocks (a `SigneddBeaconBlock`) at the beginning of the slot. At the start of the second interval, honest validators submit attestations just as they do previous to this feature). At the  start of the third interval, aggregators aggregate these attestations (exactly as before this feature) and the honest builder reveals the full payload. At the start of the fourth interval, some honest validators selected to be members of the new **Payload Timeliness Committee** attest to the presence of the builder's payload.

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

### Slashing flags
| Name | Value |
| - | - |
| `SLASHED_ATTESTER_FLAG_INDEX`| `0` # (New in ePBS)|
| `SLASHED_PROPOSER_FLAG_INDEX`| `1` # (New in ePBS)|

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

### State list lenghts
| Name | Value | Unit | Duration |
| - | - | :-: | :-: |
| `MAX_PENDING_BALANCE_DEPOSITS` | `uint64(2**20) = 1 048 576` | `PendingBalanceDeposits` | #(New in ePBS) |
| `MAX_PENDING_PARTIAL_WITHDRAWALS` | `uint64(2**20) = 1 048 576` | `PartialWithdrawals` | # (New in ePBS) |

### Rewards and penalties

| Name | Value |
| - | - |
| `PROPOSER_EQUIVOCATION_PENALTY_FACTOR` | `uint64(2**2)` (= 4) # (New in ePBS)|

### Max operations per block

| Name | Value |
| - | - |
| `MAX_PAYLOAD_ATTESTATIONS` | `2**1` (= 2) # (New in ePBS) |
| `MAX_EXECUTION_LAYER_WITHDRAW_REQUESTS` | `2**4` (= 16) # (New in ePBS) |

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

#### `PendingBalanceDeposit`

```python
class PendingBalanceDeposit(Container):
    index: ValidatorIndex
    amount: Gwei
```

#### `PartialWithdrawal`

```python
class PartialWithdrawal(Container)
    index: ValidatorIndex
    amount: Gwei
    withdrawable_epoch: Epoch
```

#### `ExecutionLayerWithdrawRequest`

```python
class ExecutionLayerWithdrawRequest(Container)
    source_address: ExecutionAddress
    validator_pubkey: BLSPubkey
    balance: Gwei
```

#### `PayloadAttestationData`

```python
class PayloadAttestationData(Container):
    beacon_block_root: Root
    slot: Slot
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

#### `ExecutionPayloadHeaderEnvelope`

```python
class ExecutionPayloadHeaderEnvelope(Container):
    header: ExecutionPayloadHeader
    builder_index: ValidatorIndex
    value: Gwei
```

#### `SignedExecutionPayloadHeaderEnvelope`

```python
class SignedExecutionPayloadHeaderEnvelope(Container):
    message: ExecutionPayloadHeaderEnvelope
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
    inclusion_list_signature: BLSSignature
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
    slot: Slot
    transactions: List[Transaction, MAX_TRANSACTIONS_PER_INCLUSION_LIST]
```

### Modified containers

#### `Validator`
**Note:** The `Validator` class is modified to keep track of the slashed categories.

```python
class Validator(Container):
    pubkey: BLSPubkey
    withdrawal_credentials: Bytes32  # Commitment to pubkey for withdrawals
    effective_balance: Gwei  # Balance at stake
    slashed: uint8 # (Modified in ePBS)
    # Status epochs
    activation_eligibility_epoch: Epoch  # When criteria for activation were met
    activation_epoch: Epoch
    exit_epoch: Epoch
    withdrawable_epoch: Epoch  # When validator can withdraw funds
```


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
    signed_execution_payload_header_envelope: SignedExecutionPayloadHeaderEnvelope  # [New in ePBS]
    payload_attestations: List[PayloadAttestation, MAX_PAYLOAD_ATTESTATIONS] # [New in ePBS]
    execution_payload_withdraw_requests: List[ExecutionLayerWithdrawRequest, MAX_EXECUTION_LAYER_WITHDRAW_REQUESTS] # [New in ePBS]
    
```

#### `ExecutionPayload`

**Note:** The `ExecutionPayload` is modified to contain a transaction inclusion list summary signed by the corresponding beacon block proposer and the list of indices of transactions in the parent block that have to be excluded from the inclusion list summary because they were satisfied in the previous slot. 

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
    inclusion_list_summary: List[InclusionListSummaryEntry, MAX_TRANSACTIONS_PER_INCLUSION_LIST] # [New in ePBS]
    inclusion_list_exclusions: List[uint64, MAX_TRANSACTIONS_PER_INCLUSION_LIST] # [New in ePBS]
```

#### `ExecutionPayloadHeader`

**Note:** The `ExecutionPayloadHeader` is modified to account for the transactions inclusion lists. 

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
    blob_gas_used: uint64
    excess_blob_gas: uint64
    inclusion_list_summary_root: Root # [New in ePBS]
    inclusion_list_exclusions_root: Root # [New in ePBS]
```

#### `BeaconState`
*Note*: the beacon state is modified to store a signed latest execution payload header, to track the last withdrawals and increased Maximum effective balance fields: `deposit_balance_to_consume`, `exit_balance_to_consume` and `earliest_exit_epoch`. 

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
    previous_inclusion_list_proposer: ValidatorIndex # [New in ePBS]
    latest_inclusion_list_proposer: ValidatorIndex # [New in ePBS]
    signed_execution_payload_header_envelope: SignedExecutionPayloadHeaderEnvelope # [New in ePBS]
    last_withdrawals_root: Root # [New in ePBS]
    deposit_balance_to_consume: Gwei # [New in ePBS]
    exit_balance_to_consume: Gwei # [New in ePBS]
    earliest_exit_epoch: Epoch # [New in ePBS]
    pending_balance_deposits: List[PendingBalanceDeposit, MAX_PENDING_BALANCE_DEPOSITS] # [New in ePBS]
    pending_partial_withdrawals: List[PartialWithdrawals, MAX_PENDING_PARTIAL_WITHDRAWALS] # [New in ePBS]
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

#### `is_builder`

```python
def is_builder(validator: Validator) -> bool:
    """
    Check if `validator` is a registered builder
    """
    return validator.withdrawal_credentials[0] == BUILDER_WITHDRAWAL_PREFIX
```

#### `is_eligible_for_activation_queue`

```python
def is_eligible_for_activation_queue(validator: Validator) -> bool:
    """
    Check if ``validator`` is eligible to be placed into the activation queue.
    """
    return (
        validator.activation_eligibility_epoch == FAR_FUTURE_EPOCH
        and validator.effective_balance >= MIN_ACTIVATION_BALANCE
    )
```

#### `is_slashed_proposer`

```python
def is_slashed_proposer(validator: Validator) -> bool:
    """
    return ``true`` if ``validator`` has committed a proposer equivocation
    """
    return has_flag(ParticipationFlags(validator.slashed), SLASHED_PROPOSER_FLAG_INDEX)
```

#### `is_slashed_attester`

```python
def is_slashed_attester(validator: Validator) -> bool:
    """
    return ``true`` if ``validator`` has committed an attestation slashing offense
    """
    return has_flag(ParticipationFlags(validator.slashed), SLASHED_ATTESTSER_FLAG_INDEX)
```


#### Modified `is_slashable_validator`
**Note:** The function `is_slashable_validator` is modified and renamed to `is_attester_slashable_validator`.

```python
def is_attester_slashable_validator(validator: Validator, epoch: Epoch) -> bool:
    """
    Check if ``validator`` is slashable.
    """
    return (not is_slashed_attester(validator)) and (validator.activation_epoch <= epoch < validator.withdrawable_epoch)
```

#### Modified `is_fully_withdrawable_validator`

```python
def is_fully_withdrawable_validator(validator: Validator, balance: Gwei, epoch: Epoch) -> bool:
    """
    Check if ``validator`` is fully withdrawable.
    """
    return (
        (has_eth1_withdrawal_credential(validator) or is_builder(validator))
        and validator.withdrawable_epoch <= epoch
        and balance > 0
    )
```

#### `is_partially_withdrawable_validator`

```python
def is_partially_withdrawable_validator(validator: Validator, balance: Gwei) -> bool:
    """
    Check if ``validator`` is partially withdrawable.
    """
    if not (has_eth1_withdrawal_credential(validator) or is_builder(validator)):
        return False
    return get_validator_excess_balance(validator, balance) > 0
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

#### `is_parent_block_full`

```python
def is_parent_block_full(state: BeaconState) -> bool:
    return state.signed_execution_payload_header_envelope.message.header == state.latest_execution_payload_header
```

### Beacon State accessors

#### Modified `get_eligible_validator_indices`
**Note:** The function `get_eligible_validator_indices` is modified to use the new flag mechanism for slashings. 

```python
def get_eligible_validator_indices(state: BeaconState) -> Sequence[ValidatorIndex]:
    previous_epoch = get_previous_epoch(state)
    return [
        ValidatorIndex(index) for index, v in enumerate(state.validators)
        if is_active_validator(v, previous_epoch) or (is_slashed_attester(v) and previous_epoch + 1 < v.withdrawable_epoch)
    ]
```

#### `get_ptc`

```python
def get_ptc(state: BeaconState, slot: Slot) -> Vector[ValidatorIndex, PTC_SIZE]:
    """
    Get the ptc committee for the given ``slot``
    """
    epoch = compute_epoch_at_slot(slot)
    committees_per_slot = bit_floor(max(get_committee_count_per_slot(state, epoch), PTC_SIZE))
    members_per_committee = PTC_SIZE/committees_per_slot
    
    validator_indices = [] 
    for idx in range(committees_per_slot)
        beacon_committee = get_beacon_committee(state, slot, idx)
        vals = [idx for idx in beacon_committee if not is_builder(idx)]
        validator_indices += vals[:members_per_commitee]
    return validator_indices
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

#### `get_validator_excess_balance`

```python
def get_validator_excess_balance(validator: Validator, balance: Gwei) -> Gwei:
    if has_eth1_withdrawal_credential(validator) and balance > MIN_ACTIVATION_BALANCE:
        return balance - MIN_ACTIVATION_BALANCE
    if is_builder(validator) and balance > MAX_EFFECTIVE_BALANCE:
        return balance - MAX_EFFECTIVE_BALANCE
    return Gwei(0)
```

#### Modified `get_validator_churn_limit`

```python
def get_validator_churn_limit(state: BeaconState) -> Gwei:
    """
    Return the validator churn limit for the current epoch.
    """
    churn = max(MIN_PER_EPOCH_CHURN_LIMIT * MIN_ACTIVATION_BALANCE, get_total_active_balance(state) // CHURN_LIMIT_QUOTIENT)
    return churn - churn % EFFECTIVE_BALANCE_INCREMENT
```

#### Modified `get_expected_withdrawals` 
**Note:** the function `get_expected_withdrawals` is modified to churn the withdrawals by balance because of the increase in `MAX_EFFECTIVE_BALANCE`

```python
def get_expected_withdrawals(state: BeaconState) -> Sequence[Withdrawal]:
    epoch = get_current_epoch(state)
    withdrawal_index = state.next_withdrawal_index
    validator_index = state.next_withdrawal_validator_index
    withdrawals: List[Withdrawal] = []
    consumed = 0
    for withdrawal in state.pending_partial_withdrawals:
        if withdrawal.withdrawable_epoch > epoch or len(withdrawals) == MAX_WITHDRAWALS_PER_PAYLOAD // 2:
            break
        validator = state.validators[withdrawal.index]
        if validator.exit_epoch == FAR_FUTURE_EPOCH and state.balances[withdrawal.index] > MIN_ACTIVATION_BALANCEa:
            withdrawble_balance = min(state.balances[withdrawal.index] - MIN_ACTIVATION_BALANCE, withdrawal.amount)
            withdrawals.append(Withdrawal(
                index=withdrawal_index,
                validator_index=withdrawal.index,
                address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                amount=withdrawable_balance,
            ))
            withdrawal_index += WithdrawalIndex(1)
            consumed += 1
    state.pending_partial_withdrawals = state.pending_partial_withdrawals[consumed:] 
    
    # Sweep for remaining
    bound = min(len(state.validators), MAX_VALIDATORS_PER_WITHDRAWALS_SWEEP)
    for _ in range(bound):
        validator = state.validators[validator_index]
        balance = state.balances[validator_index]
        if is_fully_withdrawable_validator(validator, balance, epoch):
            withdrawals.append(Withdrawal(
                index=withdrawal_index,
                validator_index=validator_index,
                address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                amount=balance,
            ))
            withdrawal_index += WithdrawalIndex(1)
        elif is_partially_withdrawable_validator(validator, balance):
            withdrawals.append(Withdrawal(
                index=withdrawal_index,
                validator_index=validator_index,
                address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                amount=get_validator_excess_balance(validator, balance),
            ))
            withdrawal_index += WithdrawalIndex(1)
        if len(withdrawals) == MAX_WITHDRAWALS_PER_PAYLOAD:
            break
        validator_index = ValidatorIndex((validator_index + 1) % len(state.validators))
    return withdrawals
```

### Beacon state mutators

#### `compute_exit_epoch_and_update_churn`

```python
def compute_exit_epoch_and_update_churn(state: BeaconState, exit_balance: Gwei) -> Epoch:
    earliest_exit_epoch = compute_activation_exit_epoch(get_current_epoch(state))
    per_epoch_churn = get_validator_churn_limit(state)
    # New epoch for exits.
    if state.earliest_exit_epoch < earliest_exit_epoch:
        state.earliest_exit_epoch = earliest_exit_epoch
        state.exit_balance_to_consume = per_epoch_churn

    # Exit fits in the current earliest epoch.
    if exit_balance < state.exit_balance_to_consume:
        state.exit_balance_to_consume -= exit_balance
    else: # Exit doesn't fit in the current earliest epoch.
        balance_to_process = exit_balance - state.exit_balance_to_consume
        additional_epochs, remainder = divmod(balance_to_process, per_epoch_churn)
        state.earliest_exit_epoch += additional_epochs
        state.exit_balance_to_consume = per_epoch_churn - remainder
    return state.earliest_exit_epoch
```

#### Modified `initiate_validator_exit`
**Note:** the function `initiate_validator_exit` is modified to use the new churn mechanism. 

```python
def initiate_validator_exit(state: BeaconState, index: ValidatorIndex) -> None:
    """
    Initiate the exit of the validator with index ``index``.
    """
    # Return if validator already initiated exit
    validator = state.validators[index]
    if validator.exit_epoch != FAR_FUTURE_EPOCH:
        return

    # Compute exit queue epoch
    exit_queue_epoch = compute_exit_epoch_and_update_churn(state, state.balances[index])

    # Set validator exit epoch and withdrawable epoch
    validator.exit_epoch = exit_queue_epoch
    validator.withdrawable_epoch = Epoch(validator.exit_epoch + MIN_VALIDATOR_WITHDRAWABILITY_DELAY)
```

#### Modified `slash_validator`
**Note:** The function `slash_validator` is modified to use the new flag system.

```python
def slash_validator(state: BeaconState,
                    slashed_index: ValidatorIndex,
                    whistleblower_index: ValidatorIndex=None) -> None:
    """
    Slash the validator with index ``slashed_index``.
    """
    epoch = get_current_epoch(state)
    initiate_validator_exit(state, slashed_index)
    validator = state.validators[slashed_index]
    validator.slashed = add_flag(validator.slashed, SLASHED_ATTESTER_FLAG_INDEX)
    validator.withdrawable_epoch = max(validator.withdrawable_epoch, Epoch(epoch + EPOCHS_PER_SLASHINGS_VECTOR))
    state.slashings[epoch % EPOCHS_PER_SLASHINGS_VECTOR] += validator.effective_balance
    decrease_balance(state, slashed_index, validator.effective_balance // MIN_SLASHING_PENALTY_QUOTIENT)

    # Apply proposer and whistleblower rewards
    proposer_index = get_beacon_proposer_index(state)
    if whistleblower_index is None:
        whistleblower_index = proposer_index
    whistleblower_reward = Gwei(validator.effective_balance // WHISTLEBLOWER_REWARD_QUOTIENT)
    proposer_reward = Gwei(whistleblower_reward // PROPOSER_REWARD_QUOTIENT)
    increase_balance(state, proposer_index, proposer_reward)
    increase_balance(state, whistleblower_index, Gwei(whistleblower_reward - proposer_reward))
```

## Genesis 

### Modified  `initialize_beacon_statre_from_eth1`

```python
def initialize_beacon_state_from_eth1(eth1_block_hash: Hash32,
                                      eth1_timestamp: uint64,
                                      deposits: Sequence[Deposit]) -> BeaconState:
    fork = Fork(
        previous_version=GENESIS_FORK_VERSION,
        current_version=GENESIS_FORK_VERSION,
        epoch=GENESIS_EPOCH,
    )
    state = BeaconState(
        genesis_time=eth1_timestamp + GENESIS_DELAY,
        fork=fork,
        eth1_data=Eth1Data(block_hash=eth1_block_hash, deposit_count=uint64(len(deposits))),
        latest_block_header=BeaconBlockHeader(body_root=hash_tree_root(BeaconBlockBody())),
        randao_mixes=[eth1_block_hash] * EPOCHS_PER_HISTORICAL_VECTOR,  # Seed RANDAO with Eth1 entropy
    )

    # Process deposits
    leaves = list(map(lambda deposit: deposit.data, deposits))
    for index, deposit in enumerate(deposits):
        deposit_data_list = List[DepositData, 2**DEPOSIT_CONTRACT_TREE_DEPTH](*leaves[:index + 1])
        state.eth1_data.deposit_root = hash_tree_root(deposit_data_list)
        process_deposit(state, deposit)

    # Process activations
    for index, validator in enumerate(state.validators):
        balance = state.balances[index]
        validator.effective_balance = min(balance - balance % EFFECTIVE_BALANCE_INCREMENT, MAX_EFFECTIVE_BALANCE)
        if validator.effective_balance >= MIN_ACTIVATION_BALANCE:
            validator.activation_eligibility_epoch = GENESIS_EPOCH
            validator.activation_epoch = GENESIS_EPOCH

    # Set genesis validators root for domain separation and chain versioning
    state.genesis_validators_root = hash_tree_root(state.validators)

    return state
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
    process_registry_updates(state) # [Modified in ePBS]
    process_slashings(state)
    process_eth1_data_reset(state)
    process_pending_balance_deposits(state)  # [New in ePBS]
    process_effective_balance_updates(state) # [Modified in ePBS]
    process_slashings_reset(state) # [Modified in ePBS]
    process_randao_mixes_reset(state)
    process_historical_summaries_update(state)
    process_participation_flag_updates(state)
    process_sync_committee_updates(state)
    process_builder_updates(state) # [New in ePBS]
```

#### Helper functions

##### Modified `process_registry_updates`

```python
def process_registry_updates(state: BeaconState) -> None:
    # Process activation eligibility and ejections
    for index, validator in enumerate(state.validators):
        if is_eligible_for_activation_queue(validator):
            validator.activation_eligibility_epoch = get_current_epoch(state) + 1

        if (
            is_active_validator(validator, get_current_epoch(state))
            and validator.effective_balance <= EJECTION_BALANCE
        ):
            initiate_validator_exit(state, ValidatorIndex(index))

    # Activate all eligible validators
    activation_epoch = compute_activation_exit_epoch(get_current_epoch(state))
    for validator in state.validators:
        if is_eligible_for_activation(state, validator):
            validator.activation_epoch = activation_epoch
```

##### `process_pending_balance_deposits`

```python
def process_pending_balance_deposits(state: BeaconState) -> None:
    state.deposit_balance_to_consume += get_validator_churn_limit(state)
    next_pending_deposit_index = 0
    for pending_balance_deposit in state.pending_balance_deposits:
        if state.deposit_balance_to_consume < pending_balance_deposit.amount:
            break

        state.deposit_balance_to_consume -= pending_balance_deposit.amount
        increase_balance(state, pending_balance_deposit.index, pending_balance_deposit.amount)
        next_pending_deposit_index += 1

    state.pending_balance_deposits = state.pending_balance_deposits[next_pending_deposit_index:]
```

##### Modified `process_effective_balance_updates`

```python
def process_effective_balance_updates(state: BeaconState) -> None:
    # Update effective balances with hysteresis
    for index, validator in enumerate(state.validators):
        balance = state.balances[index]
        HYSTERESIS_INCREMENT = uint64(EFFECTIVE_BALANCE_INCREMENT // HYSTERESIS_QUOTIENT)
        DOWNWARD_THRESHOLD = HYSTERESIS_INCREMENT * HYSTERESIS_DOWNWARD_MULTIPLIER
        UPWARD_THRESHOLD = HYSTERESIS_INCREMENT * HYSTERESIS_UPWARD_MULTIPLIER
        EFFECTIVE_BALANCE_LIMIT = MAX_EFFECTIVE_BALANCE if is_builder(validator) else MIN_ACTIVATION_BALANCE
        if (
            balance + DOWNWARD_THRESHOLD < validator.effective_balance
            or validator.effective_balance + UPWARD_THRESHOLD < balance
        ):
            validator.effective_balance = min(balance - balance % EFFECTIVE_BALANCE_INCREMENT, EFFECTIVE_BALANCE_LIMIT)
```

##### Modified `process_slashings`
**Note:** The only modification is to use the new flag mechanism

```python
def process_slashings(state: BeaconState) -> None:
    epoch = get_current_epoch(state)
    total_balance = get_total_active_balance(state)
    adjusted_total_slashing_balance = min(sum(state.slashings) * PROPORTIONAL_SLASHING_MULTIPLIER, total_balance)
    for index, validator in enumerate(state.validators):
        if is_slashed_attester(validator) and epoch + EPOCHS_PER_SLASHINGS_VECTOR // 2 == validator.withdrawable_epoch:
            increment = EFFECTIVE_BALANCE_INCREMENT  # Factored out from penalty numerator to avoid uint64 overflow
            penalty_numerator = validator.effective_balance // increment * adjusted_total_slashing_balance
            penalty = penalty_numerator // total_balance * increment
            decrease_balance(state, ValidatorIndex(index), penalty)
```

##### Modified `get_unslashed_attesting_indices`
**Note:** The function `get_unslashed_attesting_indices` is modified to return only the attester slashing validators.

```python
def get_unslashed_participating_indices(state: BeaconState, flag_index: int, epoch: Epoch) -> Set[ValidatorIndex]:
    """
    Return the set of validator indices that are both active and unslashed for the given ``flag_index`` and ``epoch``.
    """
    assert epoch in (get_previous_epoch(state), get_current_epoch(state))
    if epoch == get_current_epoch(state):
        epoch_participation = state.current_epoch_participation
    else:
        epoch_participation = state.previous_epoch_participation
    active_validator_indices = get_active_validator_indices(state, epoch)
    participating_indices = [i for i in active_validator_indices if has_flag(epoch_participation[i], flag_index)]
    return set(filter(lambda index: not is_slashed_attester(state.validators[index]), participating_indices))
```

### Execution engine

#### Request data

##### New `NewInclusionListRequest`

```python
@dataclass
class NewInclusionListRequest(object):
    inclusion_list: List[Transaction, MAX_TRANSACTIONS_PER_INCLUSION_LIST]
    summary: List[InclusionListSummaryEntry, MAX_TRANSACTIONS_PER_INCLUSION_LIST]
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
    process_block_header(state, block) # [Modified in ePBS]
    process_withdrawals(state) # [Modified in ePBS]
    process_execution_payload_header(state, block) # [Modified in ePBS, removed process_execution_payload]
    process_randao(state, block.body)
    process_eth1_data(state, block.body)
    process_operations(state, block.body)  # [Modified in ePBS]
    process_sync_aggregate(state, block.body.sync_aggregate)
```

#### Modified `process_block_header`
**Note:** the only modification is in the `slashed` verification. 

```python
def process_block_header(state: BeaconState, block: BeaconBlock) -> None:
    # Verify that the slots match
    assert block.slot == state.slot
    # Verify that the block is newer than latest block header
    assert block.slot > state.latest_block_header.slot
    # Verify that proposer index is the correct index
    assert block.proposer_index == get_beacon_proposer_index(state)
    # Verify that the parent matches
    assert block.parent_root == hash_tree_root(state.latest_block_header)
    # Cache current block as the new latest block
    state.latest_block_header = BeaconBlockHeader(
        slot=block.slot,
        proposer_index=block.proposer_index,
        parent_root=block.parent_root,
        state_root=Bytes32(),  # Overwritten in the next process_slot call
        body_root=hash_tree_root(block.body),
    )

    # Verify proposer is not slashed
    proposer = state.validators[block.proposer_index]
    assert proposer.slashed == uint8(0)
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

    for_ops(body.proposer_slashings, process_proposer_slashing) # [Modified in ePBS]
    for_ops(body.attester_slashings, process_attester_slashing) # [Modified in ePBS]
    for_ops(body.attestations, process_attestation)
    for_ops(body.deposits, process_deposit)
    for_ops(body.voluntary_exits, process_voluntary_exit)
    for_ops(body.bls_to_execution_changes, process_bls_to_execution_change)
    for_ops(body.payload_attestations, process_payload_attestation) # [New in ePBS]
    for_ops(body.execution_payload_withdraw_requests, process_execution_layer_withdraw_request) # [New in ePBS]
```

##### Modified Proposer slashings

```python
def process_proposer_slashing(state: BeaconState, proposer_slashing: ProposerSlashing) -> None:
    header_1 = proposer_slashing.signed_header_1.message
    header_2 = proposer_slashing.signed_header_2.message

    # Verify header slots match
    assert header_1.slot == header_2.slot
    # Verify header proposer indices match
    assert header_1.proposer_index == header_2.proposer_index
    # Verify the headers are different
    assert header_1 != header_2
    # Verify the proposer is slashable
    proposer = state.validators[header_1.proposer_index]
    assert proposer.activation_epoch <= get_current_epoch(state) and not is_slashed_proposer(proposer)
    # Verify signatures
    for signed_header in (proposer_slashing.signed_header_1, proposer_slashing.signed_header_2):
        domain = get_domain(state, DOMAIN_BEACON_PROPOSER, compute_epoch_at_slot(signed_header.message.slot))
        signing_root = compute_signing_root(signed_header.message, domain)
        assert bls.Verify(proposer.pubkey, signing_root, signed_header.signature)

    # Apply penalty
    penalty = PROPOSER_EQUIVOCATION_PENALTY_FACTOR * EFFECTIVE_BALANCE_INCREMENT
    decrease_balance(state, header_1.proposer_index, penalty)
    initiate_validator_exit(state, header_1.proposer_index)
    proposer.slashed = add_flag(proposer.slashed, SLASHED_PROPOSER_FLAG_INDEX)

    # Apply proposer and whistleblower rewards
    proposer_reward = Gwei((penalty // WHISTLEBLOWER_REWARD_QUOTIENT) * PROPOSER_WEIGHT // WEIGHT_DENOMINATOR)
    increase_balance(state, get_beacon_proposer_index(state), proposer_reward)
```

##### Modified Attester slashings
**Note:** The only modification is the use of `is_attester_slashable_validator`

```python
def process_attester_slashing(state: BeaconState, attester_slashing: AttesterSlashing) -> None:
    attestation_1 = attester_slashing.attestation_1
    attestation_2 = attester_slashing.attestation_2
    assert is_slashable_attestation_data(attestation_1.data, attestation_2.data)
    assert is_valid_indexed_attestation(state, attestation_1)
    assert is_valid_indexed_attestation(state, attestation_2)

    slashed_any = False
    indices = set(attestation_1.attesting_indices).intersection(attestation_2.attesting_indices)
    for index in sorted(indices):
        if is_attester_slashable_validator(state.validators[index], get_current_epoch(state)):
            slash_validator(state, index)
            slashed_any = True
    assert slashed_any
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

##### Modified `get_validator_from_deposit`
**Note:** The function `get_validator_from_deposit` is modified to take only a pubkey and withdrawal credentials and sets the effective balance to zero

```python
def get_validator_from_deposit(pubkey: BLSPubkey, withdrawal_credentials: Bytes32) -> Validator:
    return Validator(
        pubkey=pubkey,
        withdrawal_credentials=withdrawal_credentials,
        activation_eligibility_epoch=FAR_FUTURE_EPOCH,
        activation_epoch=FAR_FUTURE_EPOCH,
        exit_epoch=FAR_FUTURE_EPOCH,
        withdrawable_epoch=FAR_FUTURE_EPOCH,
        effective_balance=0,
    )
```

##### Modified `apply_deposit`

```python
def apply_deposit(state: BeaconState,
                  pubkey: BLSPubkey,
                  withdrawal_credentials: Bytes32,
                  amount: uint64,
                  signature: BLSSignature) -> None:
    validator_pubkeys = [v.pubkey for v in state.validators]
    if pubkey not in validator_pubkeys:
        # Verify the deposit signature (proof of possession) which is not checked by the deposit contract
        deposit_message = DepositMessage(
            pubkey=pubkey,
            withdrawal_credentials=withdrawal_credentials,
            amount=amount,
        )
        domain = compute_domain(DOMAIN_DEPOSIT)  # Fork-agnostic domain since deposits are valid across forks
        signing_root = compute_signing_root(deposit_message, domain)
        if bls.Verify(pubkey, signing_root, signature):
            index = len(state.validators)
            state.validators.append(get_validator_from_deposit(pubkey, withdrawal_credentials))
            state.balances.append(0)
            state.previous_epoch_participation.append(ParticipationFlags(0b0000_0000))
            state.current_epoch_participation.append(ParticipationFlags(0b0000_0000))
            state.inactivity_scores.append(uint64(0))
    else:
        index = ValidatorIndex(validator_pubkeys.index(pubkey))
    state.pending_balance_deposits.append(PendingBalanceDeposit(index=index, amount=amount))
```

##### Payload Attestations

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
    latest_payload_timestamp = state.latest_execution_payload_header.timestamp
    present_timestamp = compute_timestamp_at_slot(state, data.slot)
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

##### Execution Layer Withdraw Requests

```python
def process_execution_layer_withdraw_request(
        state: BeaconState,
        execution_layer_withdraw_request: ExecutionLayerWithdrawRequest
    ) -> None:
    validator_pubkeys = [v.pubkey for v in state.validators]
    validator_index = ValidatorIndex(validator_pubkeys.index(execution_layer_withdraw_request.validator_pubkey))
    validator = state.validators[validator_index]

    # Same conditions as in EIP7002 https://github.com/ethereum/consensus-specs/pull/3349/files#diff-7a6e2ba480d22d8bd035bd88ca91358456caf9d7c2d48a74e1e900fe63d5c4f8R223
    # Verify withdrawal credentials
    assert validator.withdrawal_credentials[:1] == ETH1_ADDRESS_WITHDRAWAL_PREFIX
    assert validator.withdrawal_credentials[12:] == execution_layer_withdraw_request.source_address
    assert is_active_validator(validator, get_current_epoch(state))
    # Verify exit has not been initiated, and slashed
    assert validator.exit_epoch == FAR_FUTURE_EPOCH:
    # Verify the validator has been active long enough
    assert get_current_epoch(state) >= validator.activation_epoch + config.SHARD_COMMITTEE_PERIOD

    pending_balance_to_withdraw = sum(item.amount for item in state.pending_partial_withdrawals if item.index == validator_index)

    available_balance = state.balances[validator_index] - MIN_ACTIVATION_BALANCE - pending_balance_to_withdraw
    assert available_balance >= execution_layer_withdraw_request.balance

    exit_queue_epoch = compute_exit_epoch_and_update_churn(state, available_balance)
    withdrawable_epoch = Epoch(exit_queue_epoch + MIN_VALIDATOR_WITHDRAWABILITY_DELAY)

    state.pending_partial_withdrawals.append(PartialWithdrawal(
        index=validator_index,
        amount=available_balance,
        withdrawable_epoch=withdrawable_epoch,
    ))
```

#### Modified `process_withdrawals`
**Note:** TODO: This is modified to take only the State as parameter as they are deterministic.

```python
def process_withdrawals(state: BeaconState) -> None:
    ## return early if the parent block was empty
     state.signed_execution_payload_header_envelope.message.header != state.latest_execution_payload_header:
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

#### New `verify_execution_payload_header_envelope_signature`

```python
def verify_execution_payload_header_envelope_signature(state: BeaconState, 
                                           signed_header_envelope: SignedExecutionPayloadHeaderEnvelope) -> bool:
    # Check the signature
    builder = state.validators[signed_header_envelope.message.builder_index]
    signing_root = compute_signing_root(signed_header_envelope.message, get_domain(state, DOMAIN_BEACON_BUILDER))
    return bls.Verify(builder.pubkey, signing_root, signed_header_envelope.signature)
```

#### New `process_execution_payload_header`

```python
def process_execution_payload_header(state: BeaconState, block: BeaconBlock) -> None:
    signed_header_envelope = block.body.signed_execution_payload_header_envelope
    assert verify_execution_payload_header_envelope_signature(state, signed_header_envelope)
    # Check that the builder has funds to cover the bid and schedule the funds for transfer
    envelope = signed_header_envelope.message
    builder_index = envelope.builder_index
    amount = envelope.value
    assert state.balances[builder_index] >= amount: 
    decrease_balance(state, builder_index, amount)
    state.pending_balance_deposits.append(PendingBalanceDeposit(index=block.proposer_index, amount=amount))
    # Verify the withdrawals_root against the state cached ones
    assert header.withdrawals_root == state.last_withdrawals_root
    # Verify consistency of the parent hash with respect to the previous execution payload header
    assert header.parent_hash == state.latest_execution_payload_header.block_hash
    # Verify prev_randao
    assert header.prev_randao == get_randao_mix(state, get_current_epoch(state))
    # Verify timestamp
    assert header.timestamp == compute_timestamp_at_slot(state, state.slot)
    # Cache the inclusion list proposer if the parent block was full
    if is_parent_block_full(state):
        state.latest_inclusion_list_proposer = block.proposer_index
    # Cache execution payload header envelope
    state.signed_execution_payload_header_envelope = signed_header_envelope
```

#### New `verify_execution_payload_signature`

```python
def verify_execution_envelope_signature(state: BeaconState, signed_envelope: SignedExecutionPayloadEnvelope) -> bool:
    builder = state.validators[signed_envelope.message.builder_index]
    signing_root = compute_signing_root(signed_envelope.message, get_domain(state, DOMAIN_BEACON_BUILDER))
    return bls.Verify(builder.pubkey, signing_root, signed_envelope.signature)
```

#### New `verify_inclusion_list_summary_signature`

```python
def verify_inclusion_list_summary_signature(state: BeaconState, signed_summary: SignedInclusionListSummary) -> bool:
    # TODO: do we need a new domain?
    summary = signed_summary.message
    signing_root = compute_signing_root(summary, get_domain(state, DOMAIN_BEACON_PROPOSER))
    proposer = state.validators[message.proposer_index]
    return bls.Verify(proposer.pubkey, signing_root, signed_summary.signature)
```

#### Modified `process_execution_payload`
*Note*: `process_execution_payload` is now an independent check in state transition. It is called when importing a signed execution payload proposed by the builder of the current slot.

```python
def process_execution_payload(state: BeaconState, signed_envelope: SignedExecutionPayloadEnvelope, execution_engine: ExecutionEngine) -> None:
    # Verify signature [New in ePBS]
    assert verify_execution_envelope_signature(state, signed_envelope)
    envelope = signed_envelope.message
    payload = envelope.payload
    # Verify inclusion list proposer
    proposer_index = envelope.inclusion_list_proposer_index
    assert proposer_index == state.previous_inclusion_list_proposer
    # Verify inclusion list summary signature
    signed_summary = SignedInclusionListSummary(
        message=InclusionListSummary(
            proposer_index=proposer_index
            summary=payload.inclusion_list_summary)
        signature=envelope.inclusion_list_signature)
    assert verify_inclusion_list_summary_signature(state, signed_summary)
    # Verify consistency with the beacon block
    assert envelope.beacon_block_root == hash_tree_root(state.latest_block_header)
    # Verify consistency with the committed header
    hash = hash_tree_root(payload)
    committed_envelope = state.signed_execution_payload_header_envelope.message
    previous_hash = hash_tree_root(committed_envelope.payload)
    assert hash == previous_hash
    # Verify consistency with the envelope
    assert envelope.builder_index == committed_envelope.builder_index
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
    state.latest_execution_payload_header = committed_envelope.header
    state.previous_inclusion_list_proposer = state.latest_inclusion_list_proposer
    # Verify the state root
    assert envelope.state_root == hash_tree_root(state)
```
