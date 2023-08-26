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

Withdrawals cannot be fulfilled at the same time in the CL and the EL now: if they are included in the Execution payload for slot N, the consensus block for the same slot may have invalidated the validator balances. The new mechanism is as follows
- Proposer for block N includes the withdrawals in his CL block and they are immediately processed in the CL
- The execution payload for N mints ETH in the EL for the already burnt ETH in the CL during slot N-1. 
- If the slot N-1 was empty, the proposer for N does not advance withdrawals and does not include any new withdrawals, so that each EL block mints a maximum of `MAX_WITHDRAWALS_PER_PAYLOAD` withdrawals. 
- There is a new engine endpoint that notifies the EL of the next withdrawals that need to be included. The EL needs to verify the validity that the execution payload includes those withdrawals in the next blockhash.

### Examples

(N-2, Full) -- (N-1: Full, withdrawals 0--15) -- (N: Empty, withdrawals 16--31) -- (N+1, does not send withdrawals, Full: excecutes withdrawals 0--15 since it is a child of the blockhash from N-1, thus grandchild of the blockhash of N-2) -- (N+2, withdrawals 32--47, Full: excecutes withdrawals 16--31) 

(N-2, Full) - (N-1: Full withdrawals 0--15) -- (N: Empty, withdrawals 16--31) -- (N+1: Empty, no withdrawals) -- (N+2: no withdrawals, Full: executes withdrawals 0--15). 
