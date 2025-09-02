Application provides a summary page with current portfolio Summary:
Fund | Latest NAV |  Units | Invested ₹ | Current ₹ | Realized P/L | Unrealized P/L | Avg Purchase NAV | % Return | % Portfolio | XIRR | Min NAV | Max NAV 
It provides a flexibility to store the transactions in GCS (Google cloud storage) in CSV format and as documents in Google Firestore.
Backend storage can be switched between GCS and Firestore and is protected by admin credentials.
It provides an option to upload CSV file with transactions and is protected by admin credentials.
It utilizes Flask session-based authentication.
Application also displays the list of transactions with pagination.
modularized.
...
