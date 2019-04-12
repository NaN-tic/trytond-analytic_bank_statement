================================
Analytic Bank Statement Scenario
================================

Imports::

    >>> import datetime
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> today = datetime.date.today()
    >>> now = datetime.datetime.now()

Install account_bank_statement::

    >>> config = activate_modules('analytic_bank_statement')

Create company::

    >>> _ = create_company()
    >>> company = get_company()
    >>> party = company.party

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> payable = accounts['payable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> cash = accounts['cash']
    >>> cash.bank_reconcile = True
    >>> cash.reconcile = True
    >>> cash.save()

Create account for bank transactions::

    >>> Account = Model.get('account.account')
    >>> bank_transactions, = Account.copy([cash.id], {
    ...         'bank_reconcile': False,
    ...         'reconcile': False,
    ...         }, config.context)
    >>> bank_transactions = Account(bank_transactions)

Create analytic accounts::

    >>> AnalyticAccount = Model.get('analytic_account.account')
    >>> root = AnalyticAccount(type='root', name='Root')
    >>> root.save()
    >>> bank_commissions_analytic_account = AnalyticAccount(root=root,
    ...     parent=root, name='Bank Commissions')
    >>> bank_commissions_analytic_account.save()
    >>> project1_analytic_account = AnalyticAccount(root=root,
    ...     parent=root, name='Project 1')
    >>> project1_analytic_account.save()
    >>> project2_analytic_account = AnalyticAccount(root=root,
    ...     parent=root, name='Project 2')
    >>> project2_analytic_account.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create journals::

    >>> Sequence = Model.get('ir.sequence')
    >>> sequence = Sequence(name='Bank', code='account.journal',
    ...     company=company)
    >>> sequence.save()
    >>> AccountJournal = Model.get('account.journal')
    >>> account_journal = AccountJournal(name='Statement',
    ...     type='cash',
    ...     sequence=sequence)
    >>> account_journal.save()
    >>> StatementJournal = Model.get('account.bank.statement.journal')
    >>> statement_journal = StatementJournal(name='Test',
    ...     journal=account_journal, account=cash)
    >>> statement_journal.save()

Create bank statement::

    >>> BankStatement = Model.get('account.bank.statement')
    >>> statement = BankStatement(journal=statement_journal, date=now)

Create bank statement line::

    >>> statement_line = statement.lines.new()
    >>> statement_line.date = now
    >>> statement_line.description = 'Bank Transaction'
    >>> statement_line.amount = Decimal('-80.0')
    >>> statement.save()
    >>> statement.reload()

Confirm bank statement::

    >>> BankStatement.confirm([statement.id], config.context)
    >>> statement.reload()
    >>> statement.state
    'confirmed'

Add transaction lines to bank statement line::

    >>> statement_line, = statement.lines
    >>> st_move_line = statement_line.lines.new()
    >>> st_move_line.amount
    Decimal('-80.00')
    >>> st_move_line.date == today
    True
    >>> st_move_line.amount = Decimal('-0.42')
    >>> st_move_line.account = expense
    >>> st_move_line.description = 'Bank Commission'
    >>> st_move_line.analytic_accounts[0].account = (
    ...     bank_commissions_analytic_account)
    >>> st_move_line = statement_line.lines.new()
    >>> st_move_line.amount
    Decimal('-79.58')
    >>> st_move_line.date == today
    True
    >>> st_move_line.account = bank_transactions
    >>> st_move_line.description = 'Bank Transaction'
    >>> statement_line.save()
    >>> statement_line.reload()

Check bank commission line has analytic accounts::

    >>> transaction_line, commission_line = sorted(statement_line.lines,
    ...     key=lambda l: l.amount)
    >>> commission_line.amount
    Decimal('-0.42')
    >>> len(commission_line.analytic_accounts)
    1

Post statement line::

    >>> statement_line.click('post')
    >>> statement_line.reload()
    >>> transaction_line.reload()
    >>> commission_line.reload()
    >>> statement_line.company_amount
    Decimal('-80.00')

Test analytic lines in expected move lines::

    >>> all(not ml.analytic_lines for ml in transaction_line.move.lines)
    True
    >>> cash_move_line, = [ml for ml in commission_line.move.lines
    ...     if ml.account == cash]
    >>> not cash_move_line.analytic_lines
    True
    >>> expense_move_line, = [ml for ml in commission_line.move.lines
    ...     if ml.account.type.expense == True]
    >>> len(expense_move_line.analytic_lines)
    1
    >>> (expense_move_line.analytic_lines[0].account
    ...     == bank_commissions_analytic_account)
    True
    >>> expense_move_line.analytic_lines[0].debit
    Decimal('0.42')

Create bank journal configured to generate analytics in bank move lines::

    >>> statement_journal2 = StatementJournal(name='Test',
    ...     journal=account_journal, analytics_on_bank_moves=True, account=cash)
    >>> statement_journal2.save()

Create second bank statement::

    >>> statement2 = BankStatement(journal=statement_journal2, date=now)
    >>> statement_line = statement2.lines.new()
    >>> statement_line.date = now
    >>> statement_line.description = 'Received Bank Transaction'
    >>> statement_line.amount = Decimal('300.0')
    >>> statement2.save()
    >>> statement2.reload()

Confirm second bank statement::

    >>> BankStatement.confirm([statement2.id], config.context)
    >>> statement2.reload()
    >>> statement2.state
    'confirmed'

Add transaction lines to second bank statement line::

    >>> statement_line2, = statement2.lines
    >>> st_move_line = statement_line2.lines.new()
    >>> st_move_line.amount
    Decimal('300.00')
    >>> st_move_line.date == today
    True
    >>> st_move_line.amount = Decimal('100.00')
    >>> st_move_line.account = revenue
    >>> st_move_line.description = 'Revenue for project 1'
    >>> st_move_line.analytic_accounts[0].account = project1_analytic_account
    >>> st_move_line = statement_line2.lines.new()
    >>> st_move_line.amount
    Decimal('200.00')
    >>> st_move_line.date == today
    True
    >>> st_move_line.account = revenue
    >>> st_move_line.description = 'Revenue for project 2'
    >>> st_move_line.analytic_accounts[0].account = project2_analytic_account
    >>> statement_line2.save()
    >>> statement_line2.reload()

Post second bank statement line::

    >>> statement_line2.click('post')
    >>> statement_line2.reload()
    >>> statement_line2.company_amount
    Decimal('300.00')

Test analytic lines also in bank accounts move lines and their amounts::

    >>> all(len(ml.analytic_lines) == 1 for stl in statement_line2.lines
    ...     for ml in stl.move.lines)
    True
    >>> desc2st_line = {stl.description: stl for stl in statement_line2.lines}
    >>> all(ml.analytic_lines[0].account == project1_analytic_account
    ...     for ml in desc2st_line['Revenue for project 1'].move.lines)
    True
    >>> all((ml.analytic_lines[0].credit == Decimal('100.00')
    ...         if ml.account == revenue else
    ...         ml.analytic_lines[0].debit == Decimal('100.00'))
    ...     for ml in desc2st_line['Revenue for project 1'].move.lines)
    True
    >>> all(ml.analytic_lines[0].account == project2_analytic_account
    ...     for ml in desc2st_line['Revenue for project 2'].move.lines)
    True
    >>> all((ml.analytic_lines[0].credit == Decimal('200.00')
    ...         if ml.account == revenue else
    ...         ml.analytic_lines[0].debit == Decimal('200.00'))
    ...     for ml in desc2st_line['Revenue for project 2'].move.lines)
    True
