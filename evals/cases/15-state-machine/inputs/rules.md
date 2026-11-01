# Loan rules of the Oakbridge tool library (fictional)

A member asks for a tool, and the loan is **requested**. If the tool is on the shelf, the desk marks it **reserved**; if it
is not, the request is **declined** and nothing more happens.

A reserved tool waits three days. When the member collects it, the loan is **lent**. When three days pass without
collection, the reservation lapses and the loan is **declined** too. A member can ask the desk for three more days, once or
more, and the loan stays reserved.

A lent tool is due back after two weeks. If it is not back by then, the loan is **overdue**. A member who pays the late fee
gets two more weeks, and the loan is lent again. A tool brought back, from lent or from overdue, makes the loan
**returned**, which is final.

We have not decided what happens to a tool that is never brought back. The board discusses it in March.
