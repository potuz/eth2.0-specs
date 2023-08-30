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
  - [Forkchoice changes](#forkchoice-changes)

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

## Forkchoice changes

There are significant design decisions to make due to the fact that a slot can have 3 different statuses:

1. The CL block is not included (therefore no payload can be included). This is a *skipped* slot. 
2. The CL block is included and the payload is not revealed. This is an *empty* slot. 
3. The CL block and the payload are both included. This is a *full* slot. 

Consider the following fork
```mermaid
graph RL
A[N-1, Full]
B[N, Empty] --> A
C[N, Full] --> A
D[N+1, Full] --> B
```

In this fork the proposer of `N+1` is attempting to reorg the payload of `N` that was seen by the majority of the PTC. Suppose that honest validators see that the PTC has voted `N` to be full. Then because of proposer boost, the CL block of `N+1` will have 40% of the committee to start with. Assuming perfect participation, honest validators should see a weight of `100` for `(N, Full)` and a weight of `40` for `N+1` (notice that they attest before seeing the payload). They should choose to vote for `(N, Full)` instead of `N+1`. The question is how do we account for all of this? A few initial comments are in line
- CL attestation do not mention full or empty they simply have a beacon block root. Honest validators will have already set their PTC vote during `N` that `N` was full. 
- The only changes to the view of `N` as empty/full could come only when importing `N+1`, a beacon block that contains PTC Messages attesting for the payload of `N`. However, if honest validators have already achieved the threshold for `full`, they will consider the block full. 
- This is one design decision: instead of having a hard threshold on the PTC (50% in the current spec) we could have a relative one, say for example a simple majority of the counted votes. This has some minor engineering problems (like keeping track of who voted in forkchoice more than simply if they voted for present or not), but this can easily be changed if there are some liveness concerns. 
- The honest builder for `N+1` would not submit a bid here, since honest builders would have seen `N` as full also, they would only build on top of the blockhash included in `N`. 
- The honest PTC members for `N+1` will vote for `N, Full` they will be rewarded but they will not change the forkchoice view that `N` was already full. 
- PTC members voting for a previous blockroot cannot change the forkchoice view of the payload status either way. 

So the questions is what changes do we need to make to our current weight accounting so that we have `(N, Full)` and `(N+1, Full)` as viable for head above, but not `(N, Empty)`?. Moreover, we want `(N, Full)` to be the winner in the above situation. Before dwelling in the justification, let me say right away that a proposer for `N+2` would call `get_head` and would get `N.root`. And then he will call `is_payload_present(N.root)` and he will get `True` so he will propose based on `(N, Full)` reorging back the dishonest (malinformed) proposer of `N+1`. The implementation of `is_payload_present` is trivial so the only question is how to do LMD counting so that `N` beats `N+1` in the head computation. 

There are several notions that can be changed when we have *empty* or *full* slots. 
- Checkpoints:
    - we can consider checkpoints to be of the form `(Epoch, Root, bool)` where the `bool` is to indicate if the Beacon block was full or not.
    - Another option is to consider checkpoints to be of the form `(Epoch, Root)` exactly as we do today, but only consider the last *full* block before or equal to the `Epoch` start.
Both have advantages and disadvantages, the second one allows for different contending states to be the first state of an epoch, but it keeps all implementations exactly as they are today.
    - A third approach, which seems the best so far, is to keep `(Epoch, Root)` and let head of the chain determine if it is *Full* or *Empty* as described below.
- Ancestry computations, as in `get_ancestor`.
    - We can change the signature of this function to be of the form `get_ancestor(Store, Root, slot) -> (Root, bool)` So that it returns the beacon block root and weather or not it is based on *Full* or *Empty*. 
    - Otherwise we can simply return the last *Full* block in the line of ancestry. Again there are advantages and disadvantages. In this last case, it would be very hard to know if two given blocks with a given payload status are in the same chain or not. 


The proposal I am considering at this moment is the following:
- Keep checkpoints as `(Epoch, Root) ` and allow different start of epoch blocks. 
- An honest validator, when requesting the state at a given block root, will use its canonical state. That is computed as follows. In the example above, when requesting the state with block root `N`, if a call to `get_head` returned `N+1` then the validator would return the `store.block_states[N.root]` which corresponds to `N, Empty`. If instead returned `N` then it would return the state `store.execution_payload_states[N.root]` which corresponds to `N, Full`. 
- Thus, when requesting the *justified state* for example, it will use the state that actually corresponds to its canonical chain and he needs to track only `Epoch, Root` for checkpoints, with minimal code changes. 
- For LMD accounting, the proposal is to keep weights exactly as today with one exception: direct votes for `N` are *only* counted in the chains supporting `N, Full` or `N, Empty` according to the PTC vote. So, in the fork above, any honest validator that voted for `N` during slot `N` will be counted in the chain for `N, Full`, but not in the chain of `N+1, Full`. Honest validators during `N+1` will also vote for `N`, and also counting their votes in for `N, Full` and not the attacker's `N+1`. Suppose the chain advances with two more bad blocks as follows
```mermaid
graph RL
A[N-1, Full]
B[N, Empty] --> A
C[N, Full] --> A
D[N+1, Full] --> B
G[N+1, Empty] --> B
E[N+2, Full] --> D
F[N+3, Full] --> G
F ~~~ E
```
In this case all the attesters for `N+1` will be counted depending on the PTC members that voted for `(N+1, Full)`. Assuming honest PTC members, they would have voted for `N` during `N+1` so any CL attesters for `N+1` would be voting for `N+1, Empty` thus only counting for the head in `(N+3, Full)`. 
