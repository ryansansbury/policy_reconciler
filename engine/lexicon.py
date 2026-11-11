"""The bank's rule vocabulary: what each rule is about, the words that signal it and the value type it sets.

Every attribute lists cue groups. A clause matches an attribute when every group has at least one of its phrases in
the clause and the clause holds a value of the attribute's type. Phrases are domain words a policy analyst would
pick, never a copy of any one document's sentence. When two attributes match, the one with more cue groups wins,
and a tie or a missing actor leaves the clause uncertain, which sends it to the AI extractor.
"""

L = {
    # Account opening
    "ao_id_count": {"topic": "acct_open", "type": "count", "cues": [["identification"]]},
    "ao_min_deposit": {"topic": "acct_open", "type": "money", "cues": [["opening deposit", "to open"], ["checking"]]},
    "ao_exception_approver": {"topic": "acct_open", "type": "role", "cues": [["exception"], ["identification"]]},
    "ao_new_account_window": {"topic": "acct_open", "type": "duration", "cues": [["new account", "counts as new"]]},
    # Fees
    "fee_waiver_bm": {"topic": "fees", "type": "money", "cues": [["waive", "waiver"]], "actor": "branch_manager"},
    "fee_waiver_pb": {"topic": "fees", "type": "money", "cues": [["waive", "waiver"]], "actor": "personal_banker"},
    "fee_waivers_per_year": {"topic": "fees", "type": "count", "cues": [["waivers"], ["year"]]},
    "fee_refund_window": {"topic": "fees", "type": "duration", "cues": [["refund"]]},
    "atm_fee": {"topic": "fees", "type": "money", "cues": [["atm"], ["outside"], ["network"]]},
    # Overdrafts
    "od_fee": {"topic": "overdraft", "type": "money", "cues": [["overdraft"], ["item"]]},
    "od_daily_cap": {"topic": "overdraft", "type": "count", "cues": [["overdraft fees"], ["business day", "per day"]]},
    "od_de_minimis": {"topic": "overdraft", "type": "money", "cues": [["overdrawn by", "no fee"]]},
    "od_chargeoff": {"topic": "overdraft", "type": "duration", "cues": [["charge-off"]]},
    # Wires
    "wire_cutoff": {"topic": "wires", "type": "time", "cues": [["outgoing"], ["wire"]], "scoped": True},
    "wire_callback": {"topic": "wires", "type": "money", "cues": [["callback", "call the customer back"], ["wire"]]},
    "wire_second_approval": {"topic": "wires", "type": "money", "cues": [["second approval"]]},
    "wire_callback_role": {"topic": "wires", "type": "role", "cues": [["callback"]]},
    "incoming_wire_posting": {"topic": "wires", "type": "time", "cues": [["incoming"], ["wire"]]},
    # Cash
    "cash_drawer_limit": {"topic": "cash", "type": "money", "cues": [["drawer"]]},
    "cash_review_threshold": {"topic": "cash", "type": "money", "cues": [["large-cash review"]]},
    "cash_vault_dual": {"topic": "cash", "type": "modal",
                        "cues": [["vault"], ["dual control", "two employees", "single employee", "one employee"]]},
    "atm_daily_limit": {"topic": "cash", "type": "money", "cues": [["atm"], ["limit", "a day", "daily"]],
                        "not": ["network"]},
    # Holds
    "hold_standard": {"topic": "holds", "type": "duration", "cues": [["deposited checks", "check hold"], ["hold", "available"]],
                      "not": ["new account"]},
    "hold_large_threshold": {"topic": "holds", "type": "money", "cues": [["extended hold"]]},
    "hold_new_account": {"topic": "holds", "type": "duration", "cues": [["new account"], ["hold", "held"], ["check"]]},
    "card_auth_hold": {"topic": "holds", "type": "duration", "cues": [["authorization hold"]]},
    # Disputes
    "dispute_window": {"topic": "disputes", "type": "duration", "cues": [["dispute"], ["statement", "window"]]},
    "dispute_provisional_credit": {"topic": "disputes", "type": "duration", "cues": [["provisional"]]},
    "dispute_review_threshold": {"topic": "disputes", "type": "money", "cues": [["dispute"], ["review", "card services"]]},
    "card_replacement": {"topic": "disputes", "type": "duration", "cues": [["replacement"]]},
    # Complaints
    "complaint_ack": {"topic": "complaints", "type": "duration", "cues": [["acknowledge", "acknowledgment"]]},
    "complaint_resolve": {"topic": "complaints", "type": "duration", "cues": [["complaint"], ["resolve", "closed", "resolution"]]},
    "complaint_escalation_role": {"topic": "complaints", "type": "role", "cues": [["escalate", "escalation"]]},
    "survey_send": {"topic": "complaints", "type": "duration", "cues": [["survey"]]},
    # Dormant accounts
    "dormant_inactivity": {"topic": "dormant", "type": "duration", "cues": [["dormant"], ["activity"]]},
    "dormant_notice": {"topic": "dormant", "type": "duration", "cues": [["notice"], ["dorman"]]},
    "dormant_fee": {"topic": "dormant", "type": "money", "cues": [["dormant"], ["fee"]]},
    "dormant_statement": {"topic": "dormant", "type": "duration", "cues": [["dormant"], ["statement"]]},
    # Records
    "records_retention": {"topic": "records", "type": "duration", "cues": [["record"], ["kept", "retain", "retention"]]},
    "records_destroy_role": {"topic": "records", "type": "role", "cues": [["destroy", "destruction"]],
                             "not": ["legal hold"]},
    "legal_hold": {"topic": "records", "type": "modal", "cues": [["legal hold"]]},
    # Branch operations
    "branch_open_dual": {"topic": "branch_ops", "type": "modal",
                         "cues": [["open the branch", "opened by", "opener", "unlock the branch", "branch opening"]]},
    "combo_change": {"topic": "branch_ops", "type": "duration", "cues": [["combination"]]},
    # Lending
    "lend_rate_bm": {"topic": "lending", "type": "percent", "cues": [["rate exception", "loan rate"]],
                     "actor": "branch_manager"},
    "lend_rate_rm": {"topic": "lending", "type": "percent", "cues": [["rate exception"]], "actor": "regional_manager"},
    "lend_exception_doc": {"topic": "lending", "type": "modal", "cues": [["pricing exception"], ["document", "record"]]},
}

LABELS = {
    "ao_id_count": "Forms of identification per signer", "ao_min_deposit": "Minimum opening deposit",
    "ao_exception_approver": "Approver for identification exceptions", "ao_new_account_window": "New account period",
    "fee_waiver_bm": "Branch manager fee waiver limit", "fee_waiver_pb": "Personal banker fee waiver limit",
    "fee_waivers_per_year": "Fee waivers per account per year", "fee_refund_window": "Fee refund window",
    "atm_fee": "Non-network ATM fee", "od_fee": "Overdraft fee per item", "od_daily_cap": "Overdraft fees per day",
    "od_de_minimis": "Overdraft amount with no fee", "od_chargeoff": "Days overdrawn before charge-off",
    "wire_cutoff": "Outgoing wire cutoff", "wire_callback": "Wire callback threshold",
    "wire_second_approval": "Wire second approval threshold", "wire_callback_role": "Who completes wire callbacks",
    "incoming_wire_posting": "Incoming wire posting time", "cash_drawer_limit": "Teller drawer limit",
    "cash_review_threshold": "Large-cash review threshold", "cash_vault_dual": "Dual control for the vault",
    "atm_daily_limit": "Daily ATM withdrawal limit", "hold_standard": "Standard check hold",
    "hold_large_threshold": "Large deposit hold threshold", "hold_new_account": "New account check hold",
    "card_auth_hold": "Card authorization hold", "dispute_window": "Card dispute window",
    "dispute_provisional_credit": "Provisional credit deadline", "dispute_review_threshold": "Dispute review threshold",
    "card_replacement": "Replacement card delivery", "complaint_ack": "Complaint acknowledgment deadline",
    "complaint_resolve": "Complaint resolution deadline", "complaint_escalation_role": "Unfair treatment escalation",
    "survey_send": "Survey timing", "dormant_inactivity": "Inactivity before dormancy",
    "dormant_notice": "Notice before dormancy", "dormant_fee": "Dormant account fee",
    "dormant_statement": "Dormant account statements", "records_retention": "Closed account record retention",
    "records_destroy_role": "Records destruction approver", "legal_hold": "Legal hold",
    "branch_open_dual": "Dual control at opening", "combo_change": "Vault combination change interval",
    "lend_rate_bm": "Branch manager rate exception limit", "lend_rate_rm": "Regional manager rate exception limit",
    "lend_exception_doc": "Documenting pricing exceptions",
}

EXCEPTION_MARKERS = (", or ", " unless ", " except ", "or longer")
