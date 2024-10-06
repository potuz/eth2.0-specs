# Engine API -- ePBS

Engine API changes introduced in the ePBS fork.

## Table of contents

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Structures](#structures)
  - [ExecutionPayloadV4](#executionpayloadv4)
  - [PayloadAttributesV3](#payloadattributesv3)
  - [InclusionListV1](#inclusionlistv1)
  - [InclusionListStatusV1](#inclusionliststatusv1)
- [Methods](#methods)
  - [engine_newInclusionListV1](#engine_newinclusionlistv1)
    - [Request](#request)
    - [Response](#response)
    - [Specification](#specification)
  - [engine_newPayloadV4](#engine_newpayloadv4)
    - [Request](#request-1)
    - [Response](#response-1)
    - [Specification](#specification-1)
  - [engine_forkchoiceUpdatedV3](#engine_forkchoiceupdatedv3)
    - [Request](#request-2)
    - [Response](#response-2)
    - [Specification](#specification-2)
  - [engine_getPayloadV3](#engine_getpayloadv3)
    - [Request](#request-3)
    - [Response](#response-3)
    - [Specification](#specification-3)
  - [`engine_getInclusionListV1`](#engine_getinclusionlistv1)
    - [Request](#request-4)
    - [Response](#response-4)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Structures

### ExecutionPayloadV4

This structure has the syntax of [`ExecutionPayloadV3`](./cancun.md#executionpayloadv3) and appends the new field `inclusionListSummary`

- `parentHash`: `DATA`, 32 Bytes
- `feeRecipient`:  `DATA`, 20 Bytes
- `stateRoot`: `DATA`, 32 Bytes
- `receiptsRoot`: `DATA`, 32 Bytes
- `logsBloom`: `DATA`, 256 Bytes
- `prevRandao`: `DATA`, 32 Bytes
- `blockNumber`: `QUANTITY`, 64 Bits
- `gasLimit`: `QUANTITY`, 64 Bits
- `gasUsed`: `QUANTITY`, 64 Bits
- `timestamp`: `QUANTITY`, 64 Bits
- `extraData`: `DATA`, 0 to 32 Bytes
- `baseFeePerGas`: `QUANTITY`, 256 Bits
- `blockHash`: `DATA`, 32 Bytes
- `transactions`: `Array of DATA` - Array of transaction objects, each object is a byte list (`DATA`) representing `TransactionType || TransactionPayload` or `LegacyTransaction` as defined in [EIP-2718](https://eips.ethereum.org/EIPS/eip-2718)
- `withdrawals`: `Array of WithdrawalV1` - Array of withdrawals, each object is an `OBJECT` containing the fields of a `WithdrawalV1` structure.
- `blobGasUsed`: `QUANTITY`, 64 Bits
- `excessBlobGas`: `QUANTITY`, 64 Bits
- `inclusionListSummary`: `Array of (DATA, 20 Bytes)` - The summary of an inclusion list signed by a previous proposer.

### PayloadAttributesV3

This structure has the syntax of [`PayloadAttributesV2`](./shanghai.md#payloadattributesv2) and appends the fields `inclusionListParentHash` and `inclusionListProposerIndex`. 

- `timestamp`: `QUANTITY`, 64 Bits - value for the `timestamp` field of the new payload
- `prevRandao`: `DATA`, 32 Bytes - value for the `prevRandao` field of the new payload
- `suggestedFeeRecipient`: `DATA`, 20 Bytes - suggested value for the `feeRecipient` field of the new payload
- `withdrawals`: `Array of WithdrawalV1` - Array of withdrawals, each object is an `OBJECT` containing the fields of a `WithdrawalV1` structure.
- `parentBeaconBlockRoot`: `DATA`, 32 Bytes - Root of the parent beacon block.
- `inclusionListParentHash`: `DATA`, 32 Bytes - Hash of the parent block of the required inclusion list.
- `inclusionListProposer`: 64 Bits - Validator index of the proposer of the inclusion list. 

### InclusionListV1

[New in ePBS]

This structure contains the full list of transactions and the summary broadcast by a proposer of an inclusion list.

- `transactions`: `Array of DATA` - Array of transaction objects, each object is a byte list (`DATA`) representing `TransactionType || TransactionPayload` or `LegacyTransaction` as defined in [EIP-2718](https://eips.ethereum.org/EIPS/eip-2718)
- `summary`: `Array of DATA` - Array of addresses, each object is a byte list (`DATA`, 20 Bytes) representing the "from" address from the transactions in the `transactions` list. 
- `parentHash`: `DATA`, 32 Bytes.
- `proposerIndex` : `QUANTITY`, 64 Bits.

### InclusionListStatusV1

[New in ePBS]

This structure contains the result of processing an inclusion list. The fields are encoded as follows:

- `status`: `enum`- `"VALID" | "INVALID" | "SYNCING" | "ACCEPTED"`
- `validationError`: `String|null` - a message providing additional details on the validation error if the inclusion list is classified as `INVALID`. 

## Methods

### engine_newInclusionListV1

[New in ePBS]

#### Request

* method: `engine_newInclusionListV1`
* params:
  1. `inclusion_list`: [`InclusionListV1`](#InclusionListV1).

#### Response

- result: [`InclusionListStatusV1`](#InclusionListStatusV1).
- error: code and message set in case an exception happens while processing the payload. 

#### Specification

### engine_newPayloadV4

#### Request

* method: `engine_newPayloadV3`
* params:
  1. `executionPayload`: [`ExecutionPayloadV3`](#ExecutionPayloadV3).
  2. `expectedBlobVersionedHashes`: `Array of DATA`, 32 Bytes - Array of expected blob versioned hashes to validate.
  3. `parentBeaconBlockRoot`: `DATA`, 32 Bytes - Root of the parent beacon block.

#### Response

Refer to the response for [`engine_newPayloadV2`](./shanghai.md#engine_newpayloadv2).

#### Specification

This method follows the same specification as [`engine_newPayloadV2`](./shanghai.md#engine_newpayloadv2) with the addition of the following:

1. Client software **MUST** check that provided set of parameters and their fields strictly matches the expected one and return `-32602: Invalid params` error if this check fails. Any field having `null` value **MUST** be considered as not provided.

2. Client software **MUST** return `-38005: Unsupported fork` error if the `timestamp` of the payload does not fall within the time frame of the Cancun fork.

3. Given the expected array of blob versioned hashes client software **MUST** run its validation by taking the following steps:
    1. Obtain the actual array by concatenating blob versioned hashes lists (`tx.blob_versioned_hashes`) of each [blob transaction](https://eips.ethereum.org/EIPS/eip-4844#new-transaction-type) included in the payload, respecting the order of inclusion. If the payload has no blob transactions the expected array **MUST** be `[]`.
    2. Return `{status: INVALID, latestValidHash: null, validationError: errorMessage | null}` if the expected and the actual arrays don't match.

    This validation **MUST** be instantly run in all cases even during active sync process.

### engine_forkchoiceUpdatedV3

#### Request

* method: `engine_forkchoiceUpdatedV3`
* params:
  1. `forkchoiceState`: [`ForkchoiceStateV1`](./paris.md#ForkchoiceStateV1).
  2. `payloadAttributes`: `Object|null` - Instance of [`PayloadAttributesV3`](#payloadattributesv3) or `null`.
* timeout: 8s

#### Response

Refer to the response for [`engine_forkchoiceUpdatedV2`](./shanghai.md#engine_forkchoiceupdatedv2).

#### Specification

This method follows the same specification as [`engine_forkchoiceUpdatedV2`](./shanghai.md#engine_forkchoiceupdatedv2) with the following changes to the processing flow:

1. Client software **MUST** verify that `forkchoiceState` matches the [`ForkchoiceStateV1`](./paris.md#ForkchoiceStateV1) structure and return `-32602: Invalid params` on failure.

2. Extend point (7) of the `engine_forkchoiceUpdatedV1` [specification](./paris.md#specification-1) by defining the following sequence of checks that **MUST** be run over `payloadAttributes`:

    1. `payloadAttributes` matches the [`PayloadAttributesV3`](#payloadattributesv3) structure, return `-38003: Invalid payload attributes` on failure.

    2. `payloadAttributes.timestamp` falls within the time frame of the Cancun fork, return `-38005: Unsupported fork` on failure.

    3. `payloadAttributes.timestamp` is greater than `timestamp` of a block referenced by `forkchoiceState.headBlockHash`, return `-38003: Invalid payload attributes` on failure.

    4. If any of the above checks fails, the `forkchoiceState` update **MUST NOT** be rolled back.

### engine_getPayloadV3

The response of this method is extended with [`BlobsBundleV1`](#blobsbundlev1) containing the blobs, their respective KZG commitments
and proofs corresponding to the `versioned_hashes` included in the blob transactions of the execution payload.

#### Request

* method: `engine_getPayloadV3`
* params:
  1. `payloadId`: `DATA`, 8 Bytes - Identifier of the payload build process
* timeout: 1s

#### Response

* result: `object`
  - `executionPayload`: [`ExecutionPayloadV3`](#ExecutionPayloadV3)
  - `blockValue` : `QUANTITY`, 256 Bits - The expected value to be received by the `feeRecipient` in wei
  - `blobsBundle`: [`BlobsBundleV1`](#BlobsBundleV1) - Bundle with data corresponding to blob transactions included into `executionPayload`
  - `shouldOverrideBuilder` : `BOOLEAN` - Suggestion from the execution layer to use this `executionPayload` instead of an externally provided one
* error: code and message set in case an exception happens while getting the payload.

#### Specification

Refer to the specification for [`engine_getPayloadV2`](./shanghai.md#engine_getpayloadv2) with addition of the following:

1. Client software **MUST** return `-38005: Unsupported fork` error if the `timestamp` of the built payload does not fall within the time frame of the Cancun fork.

2. The call **MUST** return `blobsBundle` with empty `blobs`, `commitments` and `proofs` if the payload doesn't contain any blob transactions.

3. The call **MUST** return `commitments` matching the versioned hashes of the transactions list of the execution payload, in the same order,
   i.e. `assert verify_kzg_commitments_against_transactions(payload.transactions, blobsBundle.commitments)` (see EIP-4844 consensus-specs).

4. The call **MUST** return `blobs` and `proofs` that match the `commitments` list, i.e. `assert len(blobsBundle.commitments) == len(blobsBundle.blobs) == len(blobsBundle.proofs)` and `assert verify_blob_kzg_proof_batch(blobsBundle.blobs, blobsBundle.commitments, blobsBundle.proofs)`.

5. Client software **MAY** use any heuristics to decide whether to set `shouldOverrideBuilder` flag or not. If client software does not implement any heuristic this flag **SHOULD** be set to `false`.

### `engine_getInclusionListV1`

#### Request

* method: `engine_getInclusionListV1`
* params:
    1. `parentHash`: `DATA`, 32 Bytes - hash of the block which the returning inclusion list bases on
* timeout: 1s

#### Response

* result: [`InclusionListV1`](#inclusionlistv1)
* error: code and message set in case an exception happens while getting the inclusion list.