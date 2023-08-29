<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [ePBS design notes](#epbs-design-notes)
  - [Inclusion lists](#inclusion-lists)
  - [Builders](#builders)
  - [Builder Payments](#builder-payments)
  - [Withdrawals](#withdrawals)
  - [Blobs](#blobs)
  - [PTC Rewards](#ptc-rewards)
  - [PTC Attestations](#ptc-attestations)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# ePBS design notes

## Inclusion lists

ePBS introduces forward inclusion lists for proposers to guarantee censor resistanship of the network. We follow the design described in [this post](https://ethresear.ch/t/no-free-lunch-a-new-inclusion-list-design/16389).

- Proposer for slot N submits a signed block and in parallel broadcasts pairs of `summaries` and `transactions` to be included at the beginning of slot N+1. `transactions` are just list of transactions that this proposer wants included at the most at the beginning of N+1. `Summaries` are lists consisting on addresses sending those transactions and their gas limits. The summaries are signed, the transactions aren't. An honest proposer is allowed to send many of these pairs that aren't committed to its beacon block so no double proposing slashing is involved.
- Validators for slot N will consider the block for validation only if they have seen at least one pair (summary, transactions). They will consider the block invalid if those transactions are not executable at the start of slot N and if they don't have at least 12.5% higher `maxFeePerGas` than the current slot's `maxFeePerGas`. 
- The builder for slot N reveals its payload together with a signed summary of the proposer of slot N-1. The payload is considered only valid if the following applies
    - Let k >= 0 be the minimum such that tx[0],...,tx[k-1], the first `k` transactions of the payload of slot N, satisfy some entry in the summary and `tx[k]` does not satisfy any entry. 
    - There exist transactions in the payload for N-1 that satisfy all the remaining entries in the summary. 
    - The payload is executable, that is, it's valid from the execution layer perspective. 

**Note:** in the event that the payload for the canonical block in slot N is not revealed, then the summaries and transactions list for slot N-1 remains valid, the honest proposer for slot N+1 is not allowed to submit a new IL and any such message will be ignored. The builder for N+1 still has to satisfy the summary of N-1. If there are k slots in a row that are missing payloads, the next full slot will still need to satisfy the inclusion list for N-1. 


## Builders

There is a new entity `Builder` that is a glorified validator (they are simply validators with a different withdrawal prefix `0x0b`) required to have a higher stake and required to sign when producing execution payloads. 

- Builders are also validators (otherwise their staked capital depreciates).
- We onboard builders by simply turning validators into builders if they achieve the necessary minimum balance (this way we avoid two forks to onboard builders and keep the same deposit flow, avoid builders to skip the entry churn), we change their withdrawal prefix to be distinguished from normal validators.
- We need to include several changes from the [MaxEB PR](https://github.com/michaelneuder/consensus-specs/pull/3) in order to account with builders having an increased balance that would otherwise depreciate. 

## Builder Payments

Payments are processed unconditionally when processing the signed execution payload header. There are cases to study for possible same-slot unbundling even by an equivocation. Same slot unbundling can happen if the proposer equivocates, and propagates his equivocation after seeing the reveal of the builder which happens at 8 seconds. The next proposer has to build on full which can only happen by being dishonest. Honest validators will vote for the previous block not letting the attack succeed. The honest builder does not lose his bid as the block is reorged. 
 
## Withdrawals

Withdrawals are deterministic on the beacon state, so on a consensus layer block processing, they are immediately processed, then later when the payload appears we verify that the withdrawals in the payload agree with the already fulfilled withdrawals in the CL.  

So when importing the CL block for slot N, we process the expected withdrawals at that slot. We save the list of paid withdrawals to the beacon state. When the payload for slot N appears, we check that the withdrawals correspond to the saved withdrawals. If the payload does not appear, the saved withdrawals remain, so any future payload has to include those.

## Blobs

- KZG Commitments are now sent on the Execution Payload envelope broadcasted by the EL and the EL block can only be valid if the data is available. 
- Blobs themselves may be broadcasted by the builder below as soon as it sees the beacon block if he sees it's safe. 

## PTC Rewards
- PTC members are obtained as the first members from each beacon slot committee that are not builders.
- attesters are rewarded as a full attestation when they get the right payload presence: that is, if they vote for full (resp. empty) and the payload is included (resp. not included) then they get their participation bits (target, source and head timely) set. Otherwise they get a penalty as a missed attestation. 
- Attestations to the CL block from these members are just ignored. 

## PTC Attestations

There are two ways to import PTC attestations. CL blocks contain aggregates, called `PayloadAttestation` in the spec. And committee members broadcast unaggregated `PayloadAttestationMessage`s. The latter are only imported over the wire for the current slot, and the former are only imported on blocks for the previous slot. 


