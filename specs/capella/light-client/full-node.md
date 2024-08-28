# Capella Light Client -- Full Node

**Notice**: This document is a work-in-progress for researchers and implementers.

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Helpers](#helpers)
  - [Modified `block_contents_to_light_client_header`](#modified-block_contents_to_light_client_header)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

This upgrade adds information about the execution payload to light client data as part of the Capella upgrade.

## Helpers

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

    payload = contents.block.message.body.execution_payload
    execution_branch = ExecutionBranch(
        compute_merkle_proof(contents.block.message.body, EXECUTION_PAYLOAD_GINDEX))

    execution_header = ExecutionPayloadHeader(
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
        withdrawals_root=hash_tree_root(payload.withdrawals),
    )

    return LightClientHeader(
        beacon=beacon_header,
        execution=execution_header,
        execution_branch=execution_branch,
    )
```
