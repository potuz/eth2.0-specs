# ePBS -- Honest Validator

This document represents the changes and additions to the Honest validator guide included in the ePBS fork. 

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Protocols](#protocols)
  - [`ExecutionEngine`](#executionengine)
    - [`get_execution_inclusion_list`](#get_execution_inclusion_list)
- [Validator assignment](#validator-assignment)
  - [Lookahead](#lookahead)
- [Beacon chain responsibilities](#beacon-chain-responsibilities)
  - [Block proposal](#block-proposal)
    - [Inclusion lists generation](#inclusion-lists-generation)
    - [Constructing the new `signed_execution_payload_header_envelope` field in  `BeaconBlockBody`](#constructing-the-new-signed_execution_payload_header_envelope-field-in--beaconblockbody)
    - [Constructing the new `payload_attestations` field in  `BeaconBlockBody`](#constructing-the-new-payload_attestations-field-in--beaconblockbody)
    - [Blobs sidecars](#blobs-sidecars)
  - [Payload timeliness attestation](#payload-timeliness-attestation)
    - [Constructing a payload attestation](#constructing-a-payload-attestation)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Protocols

### `ExecutionEngine`

#### `get_execution_inclusion_list`

*Note*: `get_execution_inclusion_list` function is added to the `ExecutionEngine` protocol for use as a validator.

```python
class GetInclusionListResponse(container)
    summary: List[ExecutionAddress, MAX_TRANSACTIONS_PER_INCLUSION_LIST]
    transactions: List[Transaction, MAX_TRANSACTIONS_PER_INCLUSION_LIST]
```

```python
def get_execution_inclusion_list(self: ExecutionEngine, parent_block_hash: Root) -> GetInclusionListResponse:
    """
    Return ``GetInclusionListResponse`` object.
    """
    ...
```

Given the `parent_block_hash`, `get_execution_inclusion_list` returns `GetInclusionListResponse` with the most recent version of the inclusion list based on the parent block hash.

The body of this function is implementation dependent. The Engine API may be used to implement it with an external execution engine. This function returns a `GetInclusionListResponse` object that has to have the following properties
- The `transactions` list consists of a list of transactions that can be executed based on the current execution state parametrized by the `parent_block_hash`. This includes validations that each of the "from" addresses has enough funds to cover the maximum gas specified in the transactions at the specified `base_fee_per_gas` and any possible increase for the next block because of EIP-1559. It also includes checks for nonce correctness. 
- The total gas limit of all transactions in the list is less or equal than `MAX_GAS_PER_INCLUSION_LIST`. 
- The `summary` consists of the "from" addresses from the `transactions` list. In particular, these lists have the same length. 

## Validator assignment

A validator can get PTC assignments for a given slot using the following helper via `get_ptc_assignment(state, epoch, validator_index)` where `epoch <= next_epoch`.

A validator can use the following function to see if they are supposed to submit payload attestation message during a slot across an epoch.
PTC committee selection is only stable within the context of the current and next epoch.

```python
def get_ptc_assignment(state: BeaconState,
                             epoch: Epoch,
                             validator_index: ValidatorIndex
                             ) -> Optional[Slot]:
    """
    Return the ptc committee assignment in the ``slot`` for ``validator_index``.
    ``assignment`` returned is a tuple of the following form:
        * ``assignment[0]`` is the list of validators in the ptc
        * ``assignment[1]`` is the slot at which the ptc is assigned
    Return None if no assignment.
    """
    next_epoch = Epoch(get_current_epoch(state) + 1)
    assert epoch <= next_epoch

    start_slot = compute_start_slot_at_epoch(epoch)
    for slot in range(start_slot, start_slot + SLOTS_PER_EPOCH):
            if validator_index in get_ptc(state, Slot(slot)):
                return Slot(slot)
    return None
```

### Lookahead

[New in ePBS]

`get_ptc_assignment` should be called at the start of each epoch to get the assignment for the next epoch (`current_epoch + 1`).
A validator should plan for future assignments by noting their assigned ptc committee
slot and planning to participate in the ptc committee subnet.

## Beacon chain responsibilities

All validator responsibilities remain unchanged other than the following:

- Proposers are required to broadcast `InclusionList` objects in addition to the `SignedBeaconBlock` objects. 
- Proposers are no longer required to broadcast `BlobSidecar` objects, as this becomes a builder's duty. 
- Some validators are selected per slot to become PTC members, these validators must broadcat `PayloadAttestationMessage` objects


### Block proposal

Validators are still expected to propose `SignedBeaconBlock` at the beginning of any slot during which `is_proposer(state, validator_index)` returns `true`. The mechanism to prepare this beacon block and related sidecars differs from previous forks as follows

#### Inclusion lists generation
ePBS introduces forward inclusion lists. The proposer must construct and broadcast an `InclusionList` object alongside `SignedBeaconBlock`.

To obtain an inclusion list, a block proposer building a block on top of a `state` must take the following actions:

1. If `is_parent_block_full(state)` returns `False`, the proposer should not broadcast an inclusion list. Any inclusion list for this state will be ignored by validators. 

2. Retrieve inclusion list from execution layer by calling `get_execution_inclusion_list`.

3. Call `build_inclusion_list` to build `InclusionList`.

```python
def get_inclusion_list_summary_signature(state: BeaconState, inclusion_list_summary: InclusionListSummary, privkey: int) -> BLSSignature:
    domain = get_domain(state, DOMAIN_BEACON_PROPOSER, compute_epoch_at_slot(state.slot))
    signing_root = compute_signing_root(inclusion_list_summary, domain)
    return bls.Sign(privkey, signing_root)
```

```python
def build_inclusion_list(state: BeaconState, inclusion_list_response: GetInclusionListResponse, block_slot: Slot, parent_block_hash: Hash32, index: ValidatorIndex, privkey: int) -> InclusionList:
    summary = InclusionListSummary(proposer_index=index, slot=block_slot, summary=inclusion_list_response.summary)
    signature = get_inclusion_list_summary_signature(state, summary, privkey)
    signed_summary = SignedInclusionListSummary(message=summary, signature=signature)
    return InclusionList(signed_summary=signed_inclusion_list_summary, parent_block_hash=parent_block_hash, transactions=inclusion_list_response.transactions)
```

#### Constructing the new `signed_execution_payload_header_envelope` field in  `BeaconBlockBody`

To obtain `signed_execution_payload_header`, a block proposer building a block on top of a `state` must take the following actions:
* Listen to the `execution_payload_header` gossip global topic and save an accepted `signed_execution_payload_header` from a builder. Proposer MAY obtain these signed messages by other off-protocol means. 
* The `signed_execution_payload_header` must satisfy the verification conditions found in `process_execution_payload_header`, that is 
    - The header signature must be valid
    - The builder balance can cover the header value
    - The header slot is for the proposal block slot
    - The header parent block hash equals the state's `latest_block_hash`. 
* Select one bid and set `body.signed_execution_payload_header = signed_execution_payload_header`

#### Constructing the new `payload_attestations` field in  `BeaconBlockBody`

Up to `MAX_PAYLOAD_ATTESTATIONS`, aggregate payload attestations can be included in the block. The validator will have to 
* Listen to the `payload_attestation_message` gossip global topic 
* The payload attestations added must satisfy the verification conditions found in payload attestation gossip validation and payload attestation processing. This means
    - The `data.beacon_block_root` corresponds to `block.parent_root`.
    - The slot of the parent block is exactly one slot before the proposing slot. 
    - The signature of the payload attestation data message verifies correctly. 
* The proposer needs to aggregate all payload attestations with the same data into a given `PayloadAttestation` object. For this it needs to fill the `aggregation_bits` field by using the relative position of the validator indices with respect to the PTC that is obtained from `get_ptc(state, block_slot - 1)`. 
* Proposer should only include payload attestations that are consistent with the current block they are proposing. That is, if the previous block had a payload, they should only include attestations with `payload_status = PAYLOAD_PRESENT`. Proposers are penalized for attestations that are not-consistent with their view. 

#### Blobs sidecars
The blbos sidecars are no longer broadcast by the validator, and thus their construction is not necessary. This deprecates the corresponding sections from the honest validator guide in the Deneb fork, moving them, albeit with some modifications, to the [honest Builder guide](./builder.md)

### Payload timeliness attestation

Some validators are selected to submit payload timeliness attestation. Validators should call `get_ptc_assignment` at the beginning of an epoch to be prepared to submit their PTC attestations during the next epoch. 

A validator should create and broadcast the `payload_attestation_message` to the global execution attestation subnet at `SECONDS_PER_SLOT * 3 / INTERVALS_PER_SLOT` seconds after the start of `slot`

#### Constructing a payload attestation

If a validator is in the payload attestation committee (i.e. `is_assigned_to_payload_committee()` below returns True), 
then the validator should prepare a `PayloadAttestationMessage` for the current slot,
according to the logic in `get_payload_attestation_message` at `SECONDS_PER_SLOT * 3 / INTERVALS_PER_SLOT` interval, and broadcast it to the global `payload_attestation_message` pubsub topic.

the validator creates `payload_attestation_message` as follows:
* If the validator has not seen any beacon block for the assigned slot, do not submit a payload attestation. It will be ignored anyway. 
* Set `data.beacon_block_root` be the HTR of the beacon block seen for the assigned slot
* Set `data.slot` to be the assigned slot. 
* Set `data.payload_status` as follows
    - If a valid `SignedExecutionPayloadEnvelope` has been seen referencing the block `data.beacon_block_root` and the envelope has `payload_withheld = False`,  set to `PAYLOAD_PRESENT`.
    - If a valid `SignedExecutionPayloadEnvelope` has been seen referencing the block `data.beacon_block_root` and the envelope has `payload_withheld = True`,  set to `PAYLOAD_WITHHELD`.
    - If no valid `SignedExecutionPayloadEnvelope` has been seen referencing the block `data.beacon_block_root` set to `PAYLOAD_ABSENT`.
* Set `payload_attestation_message.validator_index = validator_index` where `validator_index` is the validator chosen to submit. The private key mapping to `state.validators[validator_index].pubkey` is used to sign the payload timeliness attestation.
* Sign the `payload_attestation_message.data` using the helper `get_payload_attestation_message_signature`.

Notice that the attester only signs the `PayloadAttestationData` and not the `validator_index` field in the message. Proposers need to aggregate these attestations as described above. 

```python
def get_payload_attestation_message_signature(state: BeaconState, attestation: PayloadAttestationMessage, privkey: int) -> BLSSignature:
    domain = get_domain(state, DOMAIN_PTC_ATTESTER, compute_epoch_at_slot(attestation.data.slot))
    signing_root = compute_signing_root(attestation.data, domain)
    return bls.Sign(privkey, signing_root)
```
