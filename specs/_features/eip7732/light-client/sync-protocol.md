# EIP-7732 Light Client -- Sync Protocol

**Notice**: This document is a work-in-progress for researchers and implementers.

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Custom types](#custom-types)
- [Constants](#constants)
  - [Frozen constants](#frozen-constants)
  - [New constants](#new-constants)
- [Containers](#containers)
  - [`LightClientExecutionHeader`](#lightclientexecutionheader)
  - [Modified `LightClientHeader`](#modified-lightclientheader)
- [Helper functions](#helper-functions)
  - [`compute_slot_at_timestamp`](#compute_slot_at_timestamp)
  - [`compute_epoch_at_timestamp`](#compute_epoch_at_timestamp)
  - [Modified `get_lc_execution_root`](#modified-get_lc_execution_root)
  - [Modified `is_valid_light_client_header`](#modified-is_valid_light_client_header)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

This upgrade updates light client data to include the EIP-7732 changes to the [`ExecutionPayload`](../beacon-chain.md) semantics. It extends the [Electra Light Client specifications](../../../electra/light-client/sync-protocol.md). The [fork document](./fork.md) explains how to upgrade existing Electra based deployments to EIP-7732.

Additional documents describes the impact of the upgrade on certain roles:
- [Full node](./full-node.md)
- [Networking](./p2p-interface.md)

## Custom types

| Name | SSZ equivalent | Description |
| - | - | - |
| `ExecutionBranch` | `Vector[Bytes32, floorlog2(EXECUTION_PAYLOAD_GINDEX_EIP7732)]` | Merkle branch of `latest_execution_payload_root` within `BeaconState` |

## Constants

### Frozen constants

Existing `GeneralizedIndex` constants are frozen at their [Capella](../../../capella/light-client/sync-protocol.md#constants) values.

| Name | Value |
| - | - |
| `EXECUTION_PAYLOAD_GINDEX` | `get_generalized_index(capella.BeaconBlockBody, 'execution_payload')` (= 25) |

### New constants

| Name | Value |
| - | - |
| `EXECUTION_PAYLOAD_GINDEX_EIP7732` | `get_generalized_index(BeaconState, 'latest_execution_payload_root')` (= 101) |

## Containers

### `LightClientExecutionHeader`

**Notice**: EIP-7732 changes semantics of `ExecutionPayloadHeader` to refer to a bid instead of data that has been included on chain. This type restores the original semantics of `ExecutionPayloadHeader` as in [Electra](../../../electra/beacon-chain.md#executionpayloadheader), while using a new name to avoid name conflicts.

```python
class LightClientExecutionHeader(Container):
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
    block_hash: Hash32
    transactions_root: Root
    withdrawals_root: Root
    blob_gas_used: uint64
    excess_blob_gas: uint64
    deposit_requests_root: Root
    withdrawal_requests_root: Root
    consolidation_requests_root: Root
```

### Modified `LightClientHeader`

```python
class LightClientHeader(Container):
    # Beacon block header
    beacon: BeaconBlockHeader
    # Execution header corresponding to `beacon.state_root` (from EIP-7732 onward)
    # or `beacon.body_root` (from Capella onward)
    execution: LightClientExecutionHeader
    execution_branch: ExecutionBranch
```

## Helper functions

### `compute_slot_at_timestamp`

```python
def compute_slot_at_timestamp(timestamp: uint64, genesis_time: uint64) -> Slot:
    seconds_since_genesis = max(timestamp, genesis_time) - genesis_time
    return Slot(seconds_since_genesis // SECONDS_PER_SLOT)
```

### `compute_epoch_at_timestamp`

```python
def compute_epoch_at_timestamp(timestamp: uint64, genesis_time: uint64) -> Epoch:
    return compute_epoch_at_slot(compute_slot_at_timestamp(genesis_time, timestamp))
```

### Modified `get_lc_execution_root`

```python
def get_lc_execution_root(header: LightClientHeader, genesis_time: uint64) -> Root:
    epoch = compute_epoch_at_slot(header.beacon.slot)
    if epoch < CAPELLA_FORK_EPOCH:
        return Root()

    # [New in EIP-7732]
    if epoch >= EIP7732_FORK_EPOCH:
        if header.execution == LightClientExecutionHeader():
            return hash_tree_root(electra.ExecutionPayload())
        epoch = compute_epoch_at_timestamp(header.execution.timestamp, genesis_time)

    # [New in EIP-7732]
    if epoch >= EIP7732_FORK_EPOCH:
        return hash_tree_root(header.execution)

    # [Modified in EIP-7732]
    if epoch >= ELECTRA_FORK_EPOCH:
        return hash_tree_root(electra.ExecutionPayloadHeader(
            parent_hash=header.execution.parent_hash,
            fee_recipient=header.execution.fee_recipient,
            state_root=header.execution.state_root,
            receipts_root=header.execution.receipts_root,
            logs_bloom=header.execution.logs_bloom,
            prev_randao=header.execution.prev_randao,
            block_number=header.execution.block_number,
            gas_limit=header.execution.gas_limit,
            gas_used=header.execution.gas_used,
            timestamp=header.execution.timestamp,
            extra_data=header.execution.extra_data,
            base_fee_per_gas=header.execution.base_fee_per_gas,
            block_hash=header.execution.block_hash,
            transactions_root=header.execution.transactions_root,
            withdrawals_root=header.execution.withdrawals_root,
            blob_gas_used=header.execution.blob_gas_used,
            excess_blob_gas=header.execution.excess_blob_gas,
            deposit_requests_root=header.execution.deposit_requests_root,
            withdrawal_requests_root=header.execution.withdrawal_requests_root,
            consolidation_requests_root=header.execution.consolidation_requests_root,
        ))

    if epoch >= DENEB_FORK_EPOCH:
        return hash_tree_root(deneb.ExecutionPayloadHeader(
            parent_hash=header.execution.parent_hash,
            fee_recipient=header.execution.fee_recipient,
            state_root=header.execution.state_root,
            receipts_root=header.execution.receipts_root,
            logs_bloom=header.execution.logs_bloom,
            prev_randao=header.execution.prev_randao,
            block_number=header.execution.block_number,
            gas_limit=header.execution.gas_limit,
            gas_used=header.execution.gas_used,
            timestamp=header.execution.timestamp,
            extra_data=header.execution.extra_data,
            base_fee_per_gas=header.execution.base_fee_per_gas,
            block_hash=header.execution.block_hash,
            transactions_root=header.execution.transactions_root,
            withdrawals_root=header.execution.withdrawals_root,
            blob_gas_used=header.execution.blob_gas_used,
            excess_blob_gas=header.execution.excess_blob_gas,
        ))

    # [Modified in EIP-7732]
    if epoch >= CAPELLA_FORK_EPOCH:
        return hash_tree_root(capella.ExecutionPayloadHeader(
            parent_hash=header.execution.parent_hash,
            fee_recipient=header.execution.fee_recipient,
            state_root=header.execution.state_root,
            receipts_root=header.execution.receipts_root,
            logs_bloom=header.execution.logs_bloom,
            prev_randao=header.execution.prev_randao,
            block_number=header.execution.block_number,
            gas_limit=header.execution.gas_limit,
            gas_used=header.execution.gas_used,
            timestamp=header.execution.timestamp,
            extra_data=header.execution.extra_data,
            base_fee_per_gas=header.execution.base_fee_per_gas,
            block_hash=header.execution.block_hash,
            transactions_root=header.execution.transactions_root,
            withdrawals_root=header.execution.withdrawals_root,
        ))

    # [New in EIP-7732]
    return hash_tree_root(bellatrix.ExecutionPayloadHeader(
        parent_hash=header.execution.parent_hash,
        fee_recipient=header.execution.fee_recipient,
        state_root=header.execution.state_root,
        receipts_root=header.execution.receipts_root,
        logs_bloom=header.execution.logs_bloom,
        prev_randao=header.execution.prev_randao,
        block_number=header.execution.block_number,
        gas_limit=header.execution.gas_limit,
        gas_used=header.execution.gas_used,
        timestamp=header.execution.timestamp,
        extra_data=header.execution.extra_data,
        base_fee_per_gas=header.execution.base_fee_per_gas,
        block_hash=header.execution.block_hash,
        transactions_root=header.execution.transactions_root,
    ))
```

### Modified `is_valid_light_client_header`

```python
def is_valid_light_client_header(header: LightClientHeader, genesis_time: uint64) -> bool:
    epoch = compute_epoch_at_slot(header.beacon.slot)
    if epoch < CAPELLA_FORK_EPOCH:
        return (
            header.execution == LightClientExecutionHeader()
            and header.execution_branch == ExecutionBranch()
        )

    # [New in EIP-7732]
    if epoch >= EIP7732_FORK_EPOCH:
        epoch = compute_epoch_at_timestamp(header.execution.timestamp, genesis_time)
        branch_gindex = EXECUTION_PAYLOAD_GINDEX_EIP7732
        branch_root = header.beacon.state_root
    else:
        branch_gindex = EXECUTION_PAYLOAD_GINDEX
        branch_root = header.beacon.body_root

    if epoch < ELECTRA_FORK_EPOCH:
        if (
            header.execution.deposit_requests_root != Root()
            or header.execution.withdrawal_requests_root != Root()
            or header.execution.consolidation_requests_root != Root()
        ):
            return False

    if epoch < DENEB_FORK_EPOCH:
        if (
            header.execution.blob_gas_used != uint64(0)
            or header.execution.excess_blob_gas != uint64(0)
        ):
            return False

    # [Modified in EIP-7732]
    return is_valid_normalized_merkle_branch(
        leaf=get_lc_execution_root(header, genesis_time),
        branch=header.execution_branch,
        gindex=branch_gindex,
        root=branch_root,
    )
```
