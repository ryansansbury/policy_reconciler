"""The fictional bank every document belongs to.

Every name here is invented. BANK_NAME is the one place the bank's name lives, so a name change is one edit.
"""

BANK_NAME = "Larkhaven Bank"
SHORT_NAME = "Larkhaven"

# The footprint: four states, about 120 branches.
STATES = ("TX", "OK", "KS", "CO")
STATE_NAMES = {"TX": "Texas", "OK": "Oklahoma", "KS": "Kansas", "CO": "Colorado"}
BRANCHES = {"TX": 52, "OK": 28, "KS": 22, "CO": 18}

# Business lines. Rules apply to one or more of them.
LINES = ("consumer", "small_business", "commercial")
LINE_NAMES = {"consumer": "consumer", "small_business": "small business", "commercial": "commercial"}

DEPARTMENTS = (
    "Deposit Operations",
    "Retail Banking Operations",
    "Treasury Services",
    "Branch Network",
    "Card Services",
    "Customer Experience",
    "Records Management",
    "Lending",
    "Compliance",
)

# The fixed role list. Extraction must map every role it finds to one of these ids.
ROLES = {
    "teller": "teller",
    "head_teller": "head teller",
    "personal_banker": "personal banker",
    "branch_manager": "branch manager",
    "regional_manager": "regional manager",
    "operations_manager": "operations manager",
    "operations_specialist": "operations specialist",
    "wire_specialist": "wire specialist",
    "card_services_specialist": "card services specialist",
    "compliance_officer": "compliance officer",
    "records_custodian": "records custodian",
    "lending_officer": "lending officer",
    "customer_care_representative": "customer care representative",
}

# Synthetic people who own documents. None of them is a real person.
OWNERS = (
    "Alma Reyes", "Corey Lindqvist", "Priya Natarajan", "Tomas Herrera", "Wendell Okafor",
    "Grace Tamura", "Hollis Brandt", "Imani Castellano", "Lucia Ferrante", "Mitchell Avery",
    "Odette Larkin", "Rafael Sandoval", "Sienna Holloway", "Victor Amundsen", "Yvette Chandler",
)

# The two synthetic experts who label the evaluation items.
EXPERTS = {
    "operations": {"name": "Dana Whitfield", "title": "Operations lead"},
    "compliance": {"name": "Marisol Ortega", "title": "Compliance officer"},
}

# The day the library is current as of. Every effective date is on or before it.
AS_OF = "2026-10-01"
