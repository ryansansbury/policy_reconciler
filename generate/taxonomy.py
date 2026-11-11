"""The bank's rules: every topic, every attribute a rule can set, the bank's true values, and the ways a document
phrases each rule.

An attribute is one thing a rule decides, like the branch manager's fee waiver limit. Its canonical values are what
the bank actually intends, scoped to the business lines they apply to. Its alternates are plausible wrong values
the catalog plants. Its templates are phrasing families. Two documents that use the same family read alike, which
makes a planted contradiction easy to pair, and a different family makes it a paraphrase that needs real reading.

Template slots: {v} is the value as text, {line} the business lines a scoped rule covers. Modal attributes carry one
set of templates per modal value instead of a {v} slot. Decoy attributes are real rules that share words and value
types with another attribute, so a careless reader pairs them with the wrong rule.
"""
from generate.values import make

DEPOSIT_LINES = ("consumer", "small_business")
ALL_LINES = ("consumer", "small_business", "commercial")

TOPICS = {
    "acct_open": {"name": "Account opening and identity checks", "short": "Account Opening", "dept": "Deposit Operations"},
    "fees": {"name": "Fee waivers and refunds", "short": "Fees", "dept": "Retail Banking Operations"},
    "overdraft": {"name": "Overdrafts", "short": "Overdrafts", "dept": "Deposit Operations"},
    "wires": {"name": "Wire transfers", "short": "Wires", "dept": "Treasury Services"},
    "cash": {"name": "Cash handling and large-cash review", "short": "Cash Handling", "dept": "Branch Network"},
    "holds": {"name": "Check holds and funds availability", "short": "Funds Availability", "dept": "Deposit Operations"},
    "disputes": {"name": "Debit card disputes", "short": "Card Disputes", "dept": "Card Services"},
    "complaints": {"name": "Complaints", "short": "Complaints", "dept": "Customer Experience"},
    "dormant": {"name": "Dormant accounts", "short": "Dormant Accounts", "dept": "Deposit Operations"},
    "records": {"name": "Records retention", "short": "Records", "dept": "Records Management"},
    "branch_ops": {"name": "Branch opening and closing", "short": "Branch Operations", "dept": "Branch Network"},
    "lending": {"name": "Lending exceptions", "short": "Lending Exceptions", "dept": "Lending"},
}

TOPIC_CODES = {"acct_open": "AOP", "fees": "FEE", "overdraft": "ODR", "wires": "WIR", "cash": "CSH", "holds": "HLD",
               "disputes": "DSP", "complaints": "CMP", "dormant": "DRM", "records": "REC", "branch_ops": "BOP",
               "lending": "LND"}


def A(topic, attr, label, vtype, canonical, alts, templates, lines=DEPOSIT_LINES, actor=None, question=None,
      decoy_of=None, scoped=False):
    """One attribute. canonical is [(lines, value)], alts are wrong values the catalog can plant."""
    return {"topic": topic, "id": attr, "label": label, "type": vtype, "canonical": canonical, "alts": alts,
            "templates": templates, "lines": lines, "actor": actor, "question": question, "decoy_of": decoy_of,
            "scoped": scoped}


def M(n):
    return make("money", n)


def D(n, unit="days"):
    return make("duration", n, unit)


ATTRIBUTES = [
    # Account opening
    A("acct_open", "ao_id_count", "Forms of identification per signer", "count",
      [(DEPOSIT_LINES, make("count", 2))], [make("count", 1), make("count", 3)],
      {"a": "Collect {v} forms of identification from each signer before opening the account.",
       "b": "Every signer must present {v} separate identification documents before the account is opened.",
       "c": "Do not open an account until you have verified {v} forms of identification for each signer."},
      question="How many forms of identification does each signer need to open an account?"),
    A("acct_open", "ao_min_deposit", "Minimum opening deposit for consumer checking", "money",
      [(("consumer",), M(25))], [M(50), M(100)],
      {"a": "The minimum opening deposit for a consumer checking account is {v}.",
       "b": "A consumer checking account needs at least {v} to open.",
       "words": "Customers must deposit at least {v} to open a consumer checking account."},
      lines=("consumer",), question="What is the minimum deposit to open a consumer checking account?"),
    A("acct_open", "ao_exception_approver", "Approver for identification exceptions", "role",
      [(DEPOSIT_LINES, make("role", "branch_manager"))],
      [make("role", "regional_manager"), make("role", "operations_specialist")],
      {"a": "Any exception to the identification requirements must be approved by the {v}.",
       "b": "Only the {v} can approve an exception to the identification requirements."},
      question="Who can approve an exception to the identification requirements?"),
    A("acct_open", "ao_new_account_window", "How long an account counts as new", "duration",
      [(DEPOSIT_LINES, D(30))], [D(60), D(90)],
      {"a": "An account is treated as a new account for the first {v} after it opens.",
       "b": "Accounts open fewer than {v} are new accounts for hold and limit purposes."},
      question="How long is an account considered a new account?"),

    # Fees
    A("fees", "fee_waiver_bm", "Branch manager fee waiver limit", "money",
      [(DEPOSIT_LINES, M(50))], [M(25), M(75), M(100)],
      {"a": "Branch managers may waive service fees up to {v} per account in a calendar year.",
       "b": "The most a branch manager can waive for one account in a calendar year is {v}.",
       "inverse": "Fee waivers above {v} for one account in a calendar year require approval from the regional manager.",
       "words": "A branch manager may waive up to {v} in fees for a single account each year."},
      actor="branch_manager", question="How much can a branch manager waive in fees for one account in a year?"),
    A("fees", "fee_waiver_pb", "Personal banker fee waiver limit", "money",
      [(DEPOSIT_LINES, M(25))], [M(15), M(50)],
      {"a": "Personal bankers may waive service fees up to {v} per account in a calendar year.",
       "b": "A personal banker can waive no more than {v} for one account in a calendar year.",
       "inverse": "Personal bankers need branch manager approval for any fee waiver over {v}."},
      actor="personal_banker", question="How much can a personal banker waive in fees?"),
    A("fees", "fee_waivers_per_year", "Fee waivers per account per year", "count",
      [(DEPOSIT_LINES, make("count", 2))], [make("count", 3), make("count", 1)],
      {"a": "Each account may receive no more than {v} fee waivers in a calendar year.",
       "b": "Limit fee waivers to {v} per account in each calendar year."},
      question="How many fee waivers can one account get in a year?"),
    A("fees", "fee_refund_window", "Fee refund request window", "duration",
      [(DEPOSIT_LINES, D(60))], [D(30), D(90)],
      {"a": "Customers may request a fee refund within {v} of the statement date.",
       "b": "Fee refund requests are accepted for {v} after the statement date."},
      question="How long do customers have to request a fee refund?"),
    A("fees", "atm_fee", "Non-network ATM fee", "money",
      [(DEPOSIT_LINES, M(3))], [M(2), M(4)],
      {"a": "Withdrawals at ATMs outside the network are charged {v} each.",
       "b": "The bank charges {v} for each withdrawal at an ATM outside its network."},
      decoy_of="od_fee"),

    # Overdrafts
    A("overdraft", "od_fee", "Overdraft fee per item", "money",
      [(DEPOSIT_LINES, M(30))], [M(32), M(35), M(29)],
      {"a": "The overdraft fee is {v} per item.",
       "b": "Each item paid into overdraft is charged {v}.",
       "c": "An overdraft fee of {v} applies to each item the bank pays when the balance is not enough to cover it."},
      question="What is the overdraft fee?"),
    A("overdraft", "od_daily_cap", "Overdraft fees per account per day", "count",
      [(DEPOSIT_LINES, make("count", 3))], [make("count", 4), make("count", 5)],
      {"a": "No more than {v} overdraft fees are charged to an account in one business day.",
       "b": "Overdraft fees are capped at {v} per account per business day."},
      question="How many overdraft fees can an account be charged in one day?"),
    A("overdraft", "od_de_minimis", "Overdraft amount with no fee", "money",
      [(DEPOSIT_LINES, M(10))], [M(5), M(25)],
      {"a": "No overdraft fee is charged when the account is overdrawn by {v} or less at the end of the day.",
       "b": "Accounts overdrawn by no more than {v} at the end of the day are not charged an overdraft fee."},
      question="How much can an account be overdrawn without a fee?"),
    A("overdraft", "od_chargeoff", "Days overdrawn before charge-off", "duration",
      [(DEPOSIT_LINES, D(45))], [D(60), D(30)],
      {"a": "Accounts that remain overdrawn for {v} are referred for charge-off.",
       "b": "Refer an account for charge-off once it has been negative for {v}."},
      question="When is an overdrawn account referred for charge-off?"),

    # Wires
    A("wires", "wire_cutoff", "Outgoing wire cutoff", "time",
      [(DEPOSIT_LINES, make("time", 15 * 60)), (("commercial",), make("time", 16 * 60))],
      [make("time", 14 * 60), make("time", 15 * 60 + 30), make("time", 16 * 60)],
      {"a": "The cutoff for outgoing {line} wires is {v} Central time.",
       "b": "Outgoing {line} wire requests received after {v} Central are processed the next business day.",
       "c": "Submit outgoing {line} wires by {v} Central for same-day processing."},
      lines=ALL_LINES, scoped=True, question="What is the cutoff for outgoing consumer wires?"),
    A("wires", "wire_callback", "Callback threshold for outgoing wires", "money",
      [(ALL_LINES, M(10000))], [M(5000), M(25000)],
      {"a": "Outgoing wires of {v} or more require a callback to the customer at a number already on file.",
       "b": "Call the customer back at a phone number already on file before releasing any outgoing wire of {v} or more.",
       "inverse": "Callback verification is not required for outgoing wires under {v}."},
      lines=ALL_LINES, question="Which outgoing wires need a callback?"),
    A("wires", "wire_second_approval", "Second approval threshold for outgoing wires", "money",
      [(ALL_LINES, M(50000))], [M(25000), M(100000)],
      {"a": "Outgoing wires over {v} need a second approval from an operations manager.",
       "b": "An operations manager must give a second approval for any outgoing wire above {v}."},
      lines=ALL_LINES, actor="operations_manager", question="Which outgoing wires need a second approval?"),
    A("wires", "wire_callback_role", "Who completes wire callbacks", "role",
      [(ALL_LINES, make("role", "wire_specialist"))], [make("role", "branch_manager"), make("role", "teller")],
      {"a": "Callbacks are completed by a {v}, never by the employee who took the request.",
       "b": "Only a {v} may complete the callback for an outgoing wire."},
      lines=ALL_LINES, question="Who completes the callback for an outgoing wire?"),
    A("wires", "incoming_wire_posting", "Same-day posting time for incoming wires", "time",
      [(ALL_LINES, make("time", 16 * 60 + 30))], [make("time", 17 * 60)],
      {"a": "Incoming wires received by {v} Central are posted to the customer's account the same day.",
       "b": "Post incoming wires the same day when they arrive by {v} Central."},
      lines=ALL_LINES, decoy_of="wire_cutoff"),

    # Cash
    A("cash", "cash_drawer_limit", "Teller drawer cash limit", "money",
      [(ALL_LINES, M(15000))], [M(10000), M(20000)],
      {"a": "A teller drawer may not hold more than {v} at any time.",
       "b": "Sell excess cash to the vault whenever a teller drawer goes above {v}."},
      lines=ALL_LINES, actor="teller", question="How much cash can a teller drawer hold?"),
    A("cash", "cash_review_threshold", "Large-cash review threshold", "money",
      [(ALL_LINES, M(7500))], [M(5000), M(9000)],
      {"a": "Cash transactions of {v} or more go to the large-cash review queue the same day.",
       "b": "Log any cash deposit or withdrawal of {v} or more for large-cash review.",
       "inverse": "Cash transactions under {v} do not need large-cash review."},
      lines=ALL_LINES, question="Which cash transactions go to large-cash review?"),
    A("cash", "cash_vault_dual", "Dual control for the vault", "modal",
      [(ALL_LINES, make("modal", "must"))], [make("modal", "may")],
      {"must": {"a": "The vault must be opened under dual control, with two employees present.",
                "b": "Two employees must be present whenever the vault is opened."},
       "may": {"a": "A single employee may open the vault when a second employee is not available.",
               "b": "When no second employee is on site, one employee may open the vault alone."}},
      lines=ALL_LINES, question="Can one employee open the vault alone?"),
    A("cash", "atm_daily_limit", "Daily ATM withdrawal limit", "money",
      [(DEPOSIT_LINES, M(800))], [M(1000)],
      {"a": "The daily ATM withdrawal limit for consumer debit cards is {v}.",
       "b": "Consumer debit cards can withdraw up to {v} a day at ATMs."},
      decoy_of="cash_drawer_limit"),

    # Holds
    A("holds", "hold_standard", "Standard check hold", "duration",
      [(DEPOSIT_LINES, D(2, "business_days"))], [D(1, "business_days"), D(3, "business_days")],
      {"a": "Funds from deposited checks are available within {v} unless a longer hold applies.",
       "b": "Place a standard hold of {v} on deposited checks that don't qualify for next-day availability."},
      question="How long is the standard hold on a deposited check?"),
    A("holds", "hold_large_threshold", "Large deposit threshold for extended holds", "money",
      [(DEPOSIT_LINES, M(6000))], [M(5000), M(7500)],
      {"a": "An extended hold may be placed on the part of a day's check deposits above {v}.",
       "b": "Check deposits over {v} in one day are eligible for an extended hold on the amount over that figure."},
      question="When can a large check deposit get an extended hold?"),
    A("holds", "hold_new_account", "Longest check hold on a new account", "duration",
      [(DEPOSIT_LINES, D(7, "business_days"))], [D(5, "business_days"), D(9, "business_days")],
      {"a": "Checks deposited to a new account may be held for up to {v}.",
       "b": "New accounts can have check holds of as long as {v}."},
      question="How long can checks deposited to a new account be held?"),
    A("holds", "card_auth_hold", "Debit card authorization hold", "duration",
      [(DEPOSIT_LINES, D(3, "business_days"))], [D(5, "business_days")],
      {"a": "Debit card authorization holds drop off within {v} if the merchant does not settle the charge.",
       "b": "An authorization hold that the merchant never settles releases within {v}."},
      decoy_of="hold_standard"),

    # Disputes
    A("disputes", "dispute_window", "Debit card dispute window", "duration",
      [(DEPOSIT_LINES, D(60))], [D(90), D(30)],
      {"a": "Customers have {v} from the statement date to dispute a debit card transaction.",
       "b": "Accept debit card disputes filed within {v} of the statement that first showed the charge."},
      question="How long do customers have to dispute a debit card transaction?"),
    A("disputes", "dispute_provisional_credit", "Provisional credit deadline for disputes", "duration",
      [(DEPOSIT_LINES, D(10, "business_days"))], [D(5, "business_days"), D(15, "business_days")],
      {"a": "Provisional credit is issued within {v} of receiving a completed dispute.",
       "b": "Credit the customer provisionally no later than {v} after the dispute form is complete."},
      question="When does a customer get provisional credit on a dispute?"),
    A("disputes", "dispute_review_threshold", "Dispute amount that needs card services review", "money",
      [(DEPOSIT_LINES, M(500))], [M(250), M(1000)],
      {"a": "Disputes over {v} are reviewed by a card services specialist before credit is issued.",
       "b": "Send any dispute above {v} to card services for review before issuing credit."},
      actor="card_services_specialist", question="Which disputes need card services review?"),
    A("disputes", "card_replacement", "Replacement debit card delivery", "duration",
      [(DEPOSIT_LINES, D(7, "business_days"))], [D(10, "business_days")],
      {"a": "Replacement debit cards arrive within {v} of the request.",
       "b": "Tell customers a replacement card will arrive within {v}."},
      decoy_of="dispute_provisional_credit"),

    # Complaints
    A("complaints", "complaint_ack", "Complaint acknowledgment deadline", "duration",
      [(ALL_LINES, D(2, "business_days"))], [D(1, "business_days"), D(3, "business_days")],
      {"a": "Acknowledge every written complaint within {v}.",
       "b": "Send the customer an acknowledgment no later than {v} after a written complaint arrives."},
      lines=ALL_LINES, question="How quickly is a written complaint acknowledged?"),
    A("complaints", "complaint_resolve", "Complaint resolution deadline", "duration",
      [(ALL_LINES, D(15, "business_days"))], [D(10, "business_days"), D(30, "business_days")],
      {"a": "Resolve complaints within {v} of receipt, or tell the customer when to expect a resolution.",
       "b": "Complaints should be closed within {v} of the day they arrive."},
      lines=ALL_LINES, question="How long does the bank have to resolve a complaint?"),
    A("complaints", "complaint_escalation_role", "Escalation for unfair treatment complaints", "role",
      [(ALL_LINES, make("role", "regional_manager"))],
      [make("role", "branch_manager"), make("role", "compliance_officer")],
      {"a": "Complaints that allege unfair treatment are escalated to the {v} the same day.",
       "b": "Escalate any complaint alleging unfair treatment to the {v} on the day it is received."},
      lines=ALL_LINES, question="Who handles a complaint that alleges unfair treatment?"),
    A("complaints", "survey_send", "Customer survey timing", "duration",
      [(ALL_LINES, D(5, "business_days"))], [D(3, "business_days")],
      {"a": "Customer surveys go out within {v} of a branch visit.",
       "b": "Send the visit survey within {v} after the customer's branch visit."},
      lines=ALL_LINES, decoy_of="complaint_ack"),

    # Dormant accounts
    A("dormant", "dormant_inactivity", "Inactivity before an account is dormant", "duration",
      [(DEPOSIT_LINES, D(12, "months"))], [D(18, "months"), D(24, "months")],
      {"a": "An account with no customer-initiated activity for {v} is classified as dormant.",
       "b": "Classify accounts as dormant after {v} without customer-initiated activity."},
      question="When does an account become dormant?"),
    A("dormant", "dormant_notice", "Notice before dormancy", "duration",
      [(DEPOSIT_LINES, D(30))], [D(45), D(60)],
      {"a": "Mail the customer a notice at least {v} before the account is classified as dormant.",
       "b": "Customers receive written notice {v} before their account becomes dormant."},
      question="How much notice does a customer get before dormancy?"),
    A("dormant", "dormant_fee", "Monthly dormant account fee", "money",
      [(DEPOSIT_LINES, M(5))], [M(3), M(10)],
      {"a": "Dormant accounts are charged a maintenance fee of {v} per month.",
       "b": "The monthly fee for a dormant account is {v}."},
      question="What is the monthly fee on a dormant account?"),
    A("dormant", "dormant_statement", "Statement frequency for dormant accounts", "duration",
      [(DEPOSIT_LINES, D(12, "months"))], [D(6, "months")],
      {"a": "Dormant accounts receive a statement every {v}.",
       "b": "Send dormant accounts one statement every {v}."},
      decoy_of="dormant_inactivity"),

    # Records
    A("records", "records_retention", "Retention for closed account records", "duration",
      [(ALL_LINES, D(7, "years"))], [D(5, "years"), D(10, "years")],
      {"a": "Account records are kept for {v} after the account closes.",
       "b": "Retain closed account records for {v} from the closing date."},
      lines=ALL_LINES, question="How long are closed account records kept?"),
    A("records", "records_destroy_role", "Approver for records destruction", "role",
      [(ALL_LINES, make("role", "records_custodian"))],
      [make("role", "branch_manager"), make("role", "operations_specialist")],
      {"a": "Records may be destroyed only with written approval from the {v}.",
       "b": "The {v} must approve the destruction of any records in writing."},
      lines=ALL_LINES, question="Who approves the destruction of records?"),
    A("records", "legal_hold", "Records under a legal hold", "modal",
      [(ALL_LINES, make("modal", "must_not"))], [],
      {"must_not": {"a": "Records under a legal hold must not be destroyed until Compliance releases the hold in writing.",
                    "b": "Never destroy a record that is under a legal hold."}},
      lines=ALL_LINES, decoy_of="hold_standard"),

    # Branch operations
    A("branch_ops", "branch_open_dual", "Dual control at branch opening", "modal",
      [(ALL_LINES, make("modal", "must"))], [make("modal", "may")],
      {"must": {"a": "Two employees must be present to open the branch each morning.",
                "b": "The branch is opened by two employees together, never by one."},
       "may": {"a": "One employee may open the branch when the second opener is running late, as long as the alarm log is noted.",
               "b": "A single opener may unlock the branch if the second opener is delayed."}},
      lines=ALL_LINES, question="How many employees must be present to open the branch?"),
    A("branch_ops", "combo_change", "Vault combination change interval", "duration",
      [(ALL_LINES, D(6, "months"))], [D(12, "months"), D(3, "months")],
      {"a": "Vault combinations are changed every {v} and whenever an employee who knows the combination leaves.",
       "b": "Change the vault combination at least every {v}."},
      lines=ALL_LINES, question="How often is the vault combination changed?"),

    # Lending
    A("lending", "lend_rate_bm", "Branch manager rate exception limit", "percent",
      [(ALL_LINES, make("percent", 25))], [make("percent", 50), make("percent", 15)],
      {"a": "Branch managers may approve rate exceptions of up to {v}.",
       "b": "A branch manager can lower a loan rate by no more than {v} as an exception.",
       "inverse": "Rate exceptions larger than {v} need approval above the branch manager."},
      lines=ALL_LINES, actor="branch_manager", question="How large a rate exception can a branch manager approve?"),
    A("lending", "lend_rate_rm", "Regional manager rate exception limit", "percent",
      [(ALL_LINES, make("percent", 50))], [make("percent", 75), make("percent", 100)],
      {"a": "Regional managers may approve rate exceptions of up to {v}.",
       "b": "A regional manager can approve a rate exception as large as {v}."},
      lines=ALL_LINES, actor="regional_manager", question="How large a rate exception can a regional manager approve?"),
    A("lending", "lend_exception_doc", "Documenting pricing exceptions", "modal",
      [(ALL_LINES, make("modal", "must"))], [make("modal", "may")],
      {"must": {"a": "Every pricing exception must be documented in the loan file with the reason and the approver.",
                "b": "Record the reason and the approver for every pricing exception in the loan file."},
       "may": {"a": "Document pricing exceptions in the loan file when time allows.",
               "b": "Pricing exceptions may be documented in the loan file after closing if time is short."}},
      lines=ALL_LINES, question="Do pricing exceptions have to be documented?"),
]

BY_ID = {a["id"]: a for a in ATTRIBUTES}
RULES = [a for a in ATTRIBUTES if not a["decoy_of"]]
DECOYS = [a for a in ATTRIBUTES if a["decoy_of"]]


def line_phrase(lines):
    """How a document names the business lines a scoped rule covers."""
    from generate.bank import LINE_NAMES
    names = [LINE_NAMES[x] for x in lines]
    if len(names) == 1:
        return names[0]
    return " and ".join(names) if len(names) == 2 else ", ".join(names[:-1]) + ", and " + names[-1]
