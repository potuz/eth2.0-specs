# EIP-7732 Light Client -- Full Node

**Notice**: This document is a work-in-progress for researchers and implementers.

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Helpers](#helpers)
  - [Modified `LightClientBlockContents`](#modified-lightclientblockcontents)
  - [Modified `block_contents_to_light_client_header`](#modified-block_contents_to_light_client_header)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

Execution payload data is updated to account for the EIP-7732 upgrade.

## Helpers

### Modified `LightClientBlockContents`

```python
@dataclass
class LightClientBlockContents(object):
    block: SignedBeaconBlock = SignedBeaconBlock()
    state: BeaconState = BeaconState()  # `block.state_root`

    # `state.latest_execution_payload_root` (from EIP-7732 onward)
    execution_payload: ExecutionPayload = ExecutionPayload()
```

### Modified `block_contents_to_light_client_header`

```python
def block_contents_to_light_client_header(contents: LightClientBlockContents) -> LightClientHeader:
    beacon_header = BeaconBlockHeader(
        slot=contents.block.message.slot,
        proposer_index=contents.block.message.proposer_index,
        parent_root=contents.block.message.parent_root,
        state_root=contents.block.message.state_root,
        body_root=hash_tree_root(contents.block.message.body),
    )

    epoch = compute_epoch_at_slot(contents.block.message.slot)
    if epoch < CAPELLA_FORK_EPOCH:
        # Light client sync protocol only collects execution data from Capella onward
        return LightClientHeader(beacon=beacon_header)

    # [New in EIP-7732]
    if epoch >= EIP7732_FORK_EPOCH:
        payload = contents.execution_payload
        execution_branch = ExecutionBranch(
            compute_merkle_proof(contents.state, EXECUTION_PAYLOAD_GINDEX_EIP7732))
        epoch = compute_epoch_at_timestamp(payload.timestamp, contents.state.genesis_time)
    else:
        payload = contents.block.message.body.execution_payload
        execution_branch = ExecutionBranch(normalize_merkle_branch(
            compute_merkle_proof(contents.block.message.body, EXECUTION_PAYLOAD_GINDEX),
            EXECUTION_PAYLOAD_GINDEX_EIP7732,
        ))

    # [Modified in EIP-7732]
    if payload == ExecutionPayload():
        # `state.latest_execution_payload_root` is initialized based on empty header,
        # i.e., `transactions_root` etc are set to zero instead of `htr([])`
        execution_header = LightClientExecutionHeader()
    else:
        execution_header = LightClientExecutionHeader(
            parent_hash=payload.parent_hash,
            fee_recipient=payload.fee_recipient,
            state_root=payload.state_root,
            receipts_root=payload.receipts_root,
            logs_bloom=payload.logs_bloom,
            prev_randao=payload.prev_randao,
            block_number=payload.block_number,
            gas_limit=payload.gas_limit,
            gas_used=payload.gas_used,
            timestamp=payload.timestamp,
            extra_data=payload.extra_data,
            base_fee_per_gas=payload.base_fee_per_gas,
            block_hash=payload.block_hash,
            transactions_root=hash_tree_root(payload.transactions),
        )
        if epoch >= CAPELLA_FORK_EPOCH:
            execution_header.withdrawals_root = hash_tree_root(payload.withdrawals)
        if epoch >= DENEB_FORK_EPOCH:
            execution_header.blob_gas_used = payload.blob_gas_used
            execution_header.excess_blob_gas = payload.excess_blob_gas
        if epoch >= ELECTRA_FORK_EPOCH:
            execution_header.deposit_requests_root = hash_tree_root(payload.deposit_requests)
            execution_header.withdrawal_requests_root = hash_tree_root(payload.withdrawal_requests)
            execution_header.consolidation_requests_root = hash_tree_root(payload.consolidation_requests)

    return LightClientHeader(
        beacon=beacon_header,
        execution=execution_header,
        execution_branch=execution_branch,
    )
```
