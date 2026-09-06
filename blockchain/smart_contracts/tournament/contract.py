"""
AlgoRacers — Session 14: Tournament Smart Contract Generator
Module: blockchain/smart_contracts/tournament/contract.py
=========================================================
Generates AVM-compliant TEAL programs and ARC-4 ABI specifications
for the AlgoRacers On-Chain Tournament Registry.
"""

APPROVAL_TEAL_TEMPLATE = """#pragma version 8
// AlgoRacers On-Chain Tournament Registry
// Global State:
//   "creator" -> bytes (32-byte address)
//   "status" -> bytes ("OPEN", "CLOSED", "FINALIZED")
//   "max_players" -> int (e.g. 8)
//   "participants" -> int (count)
//   "circuit_id" -> bytes (e.g. "nova_circuit")
//   "winner" -> int (ASA ID)
//   "result_hash" -> bytes (SHA256 hex string)

// 1. Check Application ID on Creation
txn ApplicationID
bz handle_create

// 2. Handle Application Calls by ABI Method / Args
txn OnCompletion
int NoOp
==
bnz handle_noop

int 0
return

// Handle Application Creation
handle_create:
    byte "creator"
    txn Sender
    app_global_put

    byte "status"
    byte "OPEN"
    app_global_put

    byte "participants"
    int 0
    app_global_put

    byte "winner"
    int 0
    app_global_put

    byte "result_hash"
    byte ""
    app_global_put

    // Read initial circuit_id and max_players from Args if provided
    txn NumAppArgs
    int 2
    >=
    bz default_creation_args
    byte "circuit_id"
    txna ApplicationArgs 0
    app_global_put
    byte "max_players"
    txna ApplicationArgs 1
    btoi
    app_global_put
    b finish_create

default_creation_args:
    byte "circuit_id"
    byte "nova_circuit"
    app_global_put
    byte "max_players"
    int 8
    app_global_put

finish_create:
    int 1
    return

// Handle NoOp Application Calls
handle_noop:
    // Route by first argument (Action Name or Method Selector)
    txna ApplicationArgs 0
    byte "register"
    ==
    bnz handle_register

    txna ApplicationArgs 0
    byte "close_registration"
    ==
    bnz handle_close

    txna ApplicationArgs 0
    byte "finalize"
    ==
    bnz handle_finalize

    int 0
    return

// ABI Method: register(asset_id)
handle_register:
    // 1. Assert status == "OPEN"
    byte "status"
    app_global_get
    byte "OPEN"
    ==
    assert

    // 2. Assert participants < max_players
    byte "participants"
    app_global_get
    byte "max_players"
    app_global_get
    <
    assert

    // 3. Assert asset_id argument exists
    txn NumAppArgs
    int 2
    >=
    assert

    // 4. Record participant in Box: key = Sender address (32 bytes)
    // Box Key: txn Sender
    txn Sender
    txna ApplicationArgs 1 // asset_id bytes
    box_put

    // 5. Increment participant count
    byte "participants"
    byte "participants"
    app_global_get
    int 1
    +
    app_global_put

    int 1
    return

// ABI Method: close_registration()
handle_close:
    // 1. Assert Sender == creator (Organizer Authorization)
    txn Sender
    byte "creator"
    app_global_get
    ==
    assert

    // 2. Assert status == "OPEN"
    byte "status"
    app_global_get
    byte "OPEN"
    ==
    assert

    // 3. Set status = "CLOSED"
    byte "status"
    byte "CLOSED"
    app_global_put

    int 1
    return

// ABI Method: finalize(winner_asset_id, result_hash)
handle_finalize:
    // 1. Assert Sender == creator (Organizer Authorization)
    txn Sender
    byte "creator"
    app_global_get
    ==
    assert

    // 2. Assert status == "CLOSED"
    byte "status"
    app_global_get
    byte "CLOSED"
    ==
    assert

    // 3. Assert Arguments: winner_asset_id (arg 1), result_hash (arg 2)
    txn NumAppArgs
    int 3
    >=
    assert

    // 4. Store winner ASA ID
    byte "winner"
    txna ApplicationArgs 1
    btoi
    app_global_put

    // 5. Store canonical result hash
    byte "result_hash"
    txna ApplicationArgs 2
    app_global_put

    // 6. Set status = "FINALIZED"
    byte "status"
    byte "FINALIZED"
    app_global_put

    int 1
    return
"""

CLEAR_TEAL_TEMPLATE = """#pragma version 8
int 1
return
"""

def get_tournament_approval_teal() -> str:
    """Returns the AVM version 8 Approval TEAL program string."""
    return APPROVAL_TEAL_TEMPLATE.strip()

def get_tournament_clear_teal() -> str:
    """Returns the AVM version 8 ClearState TEAL program string."""
    return CLEAR_TEAL_TEMPLATE.strip()
