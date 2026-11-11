"""The words around the rules: document titles, section headings and the procedural steps that carry no rule.

Real policy libraries are mostly steps and context, with a rule here and there. These lists give every document
that texture, so a reader has to find the rules instead of having them handed over.
"""

POLICIES = {
    "acct_open": ["Deposit Account Opening Policy", "Customer Identification Policy"],
    "fees": ["Service Fee Waiver Policy", "Fee Refund Policy"],
    "overdraft": ["Overdraft Policy"],
    "wires": ["Wire Transfer Policy", "Commercial Wire Services Policy"],
    "cash": ["Cash Handling Policy", "Large-Cash Review Policy"],
    "holds": ["Funds Availability Policy"],
    "disputes": ["Debit Card Dispute Policy"],
    "complaints": ["Complaint Management Policy"],
    "dormant": ["Dormant Account Policy"],
    "records": ["Records Retention Policy"],
    "branch_ops": ["Branch Security and Opening Policy"],
    "lending": ["Loan Pricing Exception Policy"],
}

PROCEDURES = {
    "acct_open": ["Opening a Consumer Checking Account", "Opening a Savings Account", "Opening a Small Business Account",
                  "Verifying Customer Identification", "Adding a Signer to an Existing Account",
                  "Handling Identification Exceptions", "Opening an Account for a Minor with a Custodian"],
    "fees": ["Processing a Fee Waiver Request", "Reversing a Service Fee", "Handling Fee Refund Requests",
             "Reviewing Waiver Activity Each Month", "Documenting Fee Waivers in Account Notes",
             "Explaining Fees to a New Customer"],
    "overdraft": ["Reviewing Overdrawn Accounts Each Morning", "Assessing and Reversing Overdraft Fees",
                  "Referring Accounts for Charge-Off", "Talking with Customers About Overdrafts",
                  "Closing an Overdrawn Account", "Handling Overdraft Fee Disputes"],
    "wires": ["Processing Outgoing Consumer Wires", "Processing Outgoing Commercial Wires",
              "Completing Wire Callback Verification", "Handling Incoming Wires",
              "Wire Cutoffs on Holidays and Weekends", "Recalling or Cancelling a Wire",
              "Second Approval for Large Wires"],
    "cash": ["Balancing a Teller Drawer", "Selling Excess Cash to the Vault", "Opening and Closing the Vault",
             "Logging Transactions for Large-Cash Review", "Handling a Cash Shortage or Overage",
             "Ordering Cash Shipments", "Counting Cash Under Dual Control"],
    "holds": ["Placing a Hold on a Deposited Check", "Extending a Hold on a Large Deposit",
              "Holds on New Accounts", "Releasing a Hold Early", "Explaining Holds to Customers",
              "Holds on Mobile Deposits"],
    "disputes": ["Taking a Debit Card Dispute", "Issuing Provisional Credit", "Investigating a Dispute",
                 "Reversing Provisional Credit", "Blocking and Replacing a Compromised Card",
                 "Large Dispute Review"],
    "complaints": ["Logging a Customer Complaint", "Acknowledging a Written Complaint",
                   "Resolving and Closing a Complaint", "Escalating a Sensitive Complaint",
                   "Reviewing Complaint Trends Each Quarter", "Responding to a Complaint by Phone"],
    "dormant": ["Identifying Dormant Accounts", "Sending Dormancy Notices", "Reactivating a Dormant Account",
                "Charging Dormant Account Fees", "Reviewing Dormant Accounts Each Quarter",
                "Handling Mail Returned on a Dormant Account"],
    "records": ["Retaining Closed Account Records", "Approving Records Destruction", "Placing Records on Legal Hold",
                "Releasing a Legal Hold", "Shipping Records to Offsite Storage", "Retrieving Archived Records"],
    "branch_ops": ["Opening the Branch Each Morning", "Closing the Branch Each Evening",
                   "Changing Vault Combinations", "Testing the Alarm System", "Handling a Late Opener",
                   "After-Hours Branch Access"],
    "lending": ["Requesting a Rate Exception", "Approving a Rate Exception", "Documenting Pricing Exceptions",
                "Reviewing Exception Reports Each Month", "Fee Exceptions on Consumer Loans",
                "Escalating Exceptions Above Branch Authority"],
}

JOB_AIDS = {
    "acct_open": ["New Account Quick Reference", "Identification Checklist", "Account Opening Desk Card"],
    "fees": ["Fee Waiver Quick Reference", "Fee Schedule at a Glance", "Waiver Authority Card"],
    "overdraft": ["Overdraft Quick Reference", "Overdraft Fee Desk Card"],
    "wires": ["Wire Desk Quick Reference", "Callback Checklist", "Wire Cutoff Card"],
    "cash": ["Teller Cash Limits Card", "Vault Opening Checklist", "Large-Cash Review Quick Reference"],
    "holds": ["Hold Calendar Quick Reference", "Check Hold Desk Card", "Hold Notice Checklist"],
    "disputes": ["Dispute Intake Checklist", "Dispute Timelines Card", "Card Services Quick Reference"],
    "complaints": ["Complaint Handling Card", "Complaint Escalation Checklist"],
    "dormant": ["Dormant Account Quick Reference", "Dormancy Notice Checklist"],
    "records": ["Records Retention Schedule Card", "Destruction Approval Checklist"],
    "branch_ops": ["Opening Checklist", "Closing Checklist", "Vault Security Card"],
    "lending": ["Rate Exception Authority Card", "Exception Documentation Checklist"],
}

FAQS = {
    "acct_open": ["Account Opening FAQ", "Identification Questions from the Branches"],
    "fees": ["Fee Waiver FAQ", "Fee Refund Questions"],
    "overdraft": ["Overdraft FAQ", "Overdraft Fee Questions from Customers"],
    "wires": ["Wire Transfer FAQ", "Wire Cutoff Questions"],
    "cash": ["Cash Handling FAQ", "Large-Cash Review Questions"],
    "holds": ["Funds Availability FAQ", "Check Hold Questions from Customers"],
    "disputes": ["Debit Card Dispute FAQ", "Provisional Credit Questions"],
    "complaints": ["Complaint Handling FAQ", "Complaint Escalation Questions"],
    "dormant": ["Dormant Account FAQ", "Reactivation Questions"],
    "records": ["Records Retention FAQ", "Legal Hold Questions"],
    "branch_ops": ["Branch Opening FAQ"],
    "lending": ["Rate Exception FAQ", "Pricing Exception Questions"],
}

ADDENDA = {"TX": "Texas Branch Addendum", "OK": "Oklahoma Branch Addendum", "KS": "Kansas Branch Addendum",
           "CO": "Colorado Branch Addendum"}

STEPS = {
    "acct_open": [
        "Confirm the type of account the customer wants and explain its features.",
        "Enter the customer's name and address exactly as they appear on the identification.",
        "Scan each identification document into the account record.",
        "Ask whether the customer wants a debit card ordered with the account.",
        "Review the account agreement with the customer and have each signer sign it.",
        "Run the customer through the identity verification screen before funding the account.",
        "Give the customer a copy of the fee schedule and the funds availability notice.",
        "Record the opening deposit and confirm it posted to the new account.",
    ],
    "fees": [
        "Look up the fee in the account history and confirm the date it posted.",
        "Ask the customer why they are requesting the waiver and note the reason.",
        "Check the account's waiver history for the current calendar year.",
        "Enter the waiver using the fee reversal screen and select the matching reason code.",
        "Tell the customer the waiver will appear on their next statement.",
        "Review recurring waiver requests with the branch manager at the monthly meeting.",
        "Do not promise a waiver before checking whether it is within your authority.",
    ],
    "overdraft": [
        "Review the overdrawn accounts report at the start of each business day.",
        "Contact customers whose accounts have been overdrawn for more than three days.",
        "Explain the overdraft fee and the options for avoiding future fees.",
        "Offer to link a savings account for overdraft protection transfers.",
        "Note every customer contact in the account record.",
        "Reverse a fee only when the reversal is within your authority.",
    ],
    "wires": [
        "Confirm the beneficiary's name, account number and bank routing number with the customer.",
        "Have the customer sign the wire request form in the branch.",
        "Check the account balance before sending the wire to operations.",
        "Never accept wire instructions sent by email without verifying them by phone.",
        "Enter the wire in the wire system and attach the signed request form.",
        "Give the customer the wire confirmation number once the wire is released.",
        "Check the holiday calendar before promising a same-day wire.",
    ],
    "cash": [
        "Count the cash in your drawer at the start and end of every shift.",
        "Keep your drawer locked whenever you step away from the teller line.",
        "Use the counterfeit detection pen on bills of fifty dollars or more.",
        "Record every vault transfer in the vault log with both employees' initials.",
        "Report any shortage or overage to the head teller before you leave for the day.",
        "Store bait bills in the bottom of the drawer as security trained you.",
    ],
    "holds": [
        "Tell the customer when the held funds will be available before they leave.",
        "Print the hold notice and give it to the customer with their receipt.",
        "Enter the hold reason code that matches the situation.",
        "Release a hold early only with your manager's approval.",
        "Mail the hold notice when the deposit was made by mail or at an ATM.",
    ],
    "disputes": [
        "Have the customer review their recent transactions and identify each charge they dispute.",
        "Block the card right away if the customer believes it was lost or stolen.",
        "Help the customer complete the dispute form and sign it.",
        "Send the completed form to card services the same day.",
        "Tell the customer how they will be notified of the outcome.",
        "Order a replacement card when the original card is blocked.",
    ],
    "complaints": [
        "Thank the customer for raising the issue and listen without interrupting.",
        "Log the complaint in the complaint system, even when it is resolved on the spot.",
        "Ask what outcome the customer is hoping for.",
        "Attach any letters or emails the customer sent to the complaint record.",
        "Tell the customer who will contact them next and when.",
        "Review complaint trends with your team each quarter.",
    ],
    "dormant": [
        "Run the dormancy report on the first business day of each month.",
        "Confirm the customer's mailing address before sending a notice.",
        "Reactivate an account when the customer makes a deposit or withdrawal in person.",
        "Verify the customer's identity before reactivating a dormant account.",
        "Note returned mail on the account so the next notice uses an updated address.",
    ],
    "records": [
        "Box closed account records by closing month and label each box with the destruction date.",
        "Ship boxes to offsite storage using the approved courier.",
        "Log every box sent offsite in the records inventory.",
        "Shred destroyed records with the approved vendor and keep the certificate of destruction.",
        "Check the legal hold list before preparing any records for destruction.",
    ],
    "branch_ops": [
        "Approach the branch together and check the exterior for signs of forced entry.",
        "Disarm the alarm within the entry delay and reset it if you trip a zone.",
        "Signal the all-clear to the second opener only after walking the branch.",
        "Lock the doors and set the alarm after the last customer leaves.",
        "Log the opening and closing times in the branch log.",
        "Report any alarm fault to security before opening for business.",
    ],
    "lending": [
        "Enter the requested rate and the reason for the exception in the pricing worksheet.",
        "Confirm the borrower's credit grade before requesting an exception.",
        "Attach the competitor offer when the exception matches a competing rate.",
        "Send the exception request to the approver through the loan system.",
        "Tell the borrower the approved rate only after the approval is recorded.",
    ],
}

GENERIC = [
    "Verify the customer's identity before discussing any account details.",
    "Document the request and its outcome in the account notes.",
    "Ask your manager when a situation is not covered here.",
    "Use plain language and avoid internal codes when explaining the outcome to the customer.",
    "Keep customer documents out of public view at your workstation.",
    "Follow up with the customer if the request cannot be completed the same day.",
    "Escalate to your manager if the customer is upset or the request is unusual.",
]

POLICY_PURPOSE = "This policy sets {bank}'s requirements for {topic}."
POLICY_SCOPE_ALL = "It applies to every branch and department and to all business lines."
POLICY_SCOPE_LINES = "It applies to every branch for {lines} accounts."
POLICY_EXCEPTIONS = "Exceptions to this policy need written approval from the {dept} manager and are reviewed each quarter."
POLICY_RESPONSIBILITIES = "Branch managers make sure their teams follow this policy, and {dept} answers questions about it."
POLICY_REVIEW = "{dept} reviews this policy at least once a year."
PROCEDURE_PURPOSE = "This procedure covers {task}, step by step, for every branch it applies to."
PROCEDURE_BEFORE = "Make sure you have completed the training for this task and have access to the systems it uses."
ADDENDUM_PURPOSE = "This addendum lists requirements that apply only to branches in {state}. Where it differs from a bank-wide document, it controls for {state} branches."
