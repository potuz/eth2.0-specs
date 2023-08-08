# ePBS design notes

## Inclusion lists

ePBS introduces forward inclusion lists for proposers to guarantee censor resistanship of the network. They are implemented as follows

- Proposer for slot N submits a signed block that includes some transactions to be included at the beginning of slot N+1. 
- Validators for slot N will consider the block invalid if those transactions are not executable at the start of slot N (this makes it impossible to put transactions that are only valid at slot N+1 for example, but still the proposer can protect from unbundling/replaying by binding the transaction to only be valid up to N+1 for example, because the block for N has already been committed by the builder). 
- The IL is put in the `BeaconState`. 
- The builder for slot N reveals its payload. This payload also contains a `beacon_state_root`.  Validators for this slot will remove from the IL any transaction that was already executed during slot N (for example the builder may have independently included this transaction) or that became invalid because of other transactions from the same sender that appeared during N. They also check that the resulting `BeaconState` has the same `beacon_state_root` committed to by the builder. The upshot of this step is that the IL in the beacon state contains transactions that are guaranteed to be valid and executable during the beginning of N+1. 
- The proposer for N+1 produces a block with its own IL for N+2. The builder for N+1 reveals its payload, and validators deem it invalid if the first transactions do not agree with the corresponding IL exactly. 

**Note:** in the event that the payload for the canonical block in slot N is not revealed, then the IL for slot N remains valid, the proposer for slot N+1 is not allowed to include a new IL.  

There are some concerns about proposers using IL for data availability, since the CL will have to keep the blocks somewhere to reconstruct the beacon state. There is a nice design by @vbuterin that instead of committing the IL to state, allows the txs to go on a sidecar together with a signed summary. The builder then needs to include the signed summary and a block that satisfies it. This design trades complexity for safety under the free DA issue of the above.


