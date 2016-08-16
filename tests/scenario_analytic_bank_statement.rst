================================
Analytic Bank Statement Scenario
================================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()
    >>> now = datetime.datetime.now()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install account_bank_statement::

    >>> Module = Model.get('ir.module')
    >>> account_bank_module, = Module.find(
    ...     [('name', '=', 'analytic_bank_statement')])
    >>> Module.install([account_bank_module.id], config.context)
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()
    >>> party = company.party

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

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
    ...     credit_account=cash,
    ...     debit_account=cash,
    ...     sequence=sequence)
    >>> account_journal.save()
    >>> StatementJournal = Model.get('account.bank.statement.journal')
    >>> statement_journal = StatementJournal(name='Test',
    ...     journal=account_journal)
    >>> statement_journal.save()

Create bank statement::

    >>> BankStatement = Model.get('account.bank.statement')
    >>> statement = BankStatement(journal=statement_journal, date=now)

Create bank statement line::

    >>> StatementLine = Model.get('account.bank.statement.line')
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
    u'confirmed'

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
    >>> commission_line.analytic_accounts != None
    ...     and commission_line.analytic_accounts.accounts != None
    True

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
    ...     if ml.account.kind == 'expense']
    >>> len(expense_move_line.analytic_lines)
    1
    >>> (expense_move_line.analytic_lines[0].account
    ...     == bank_commissions_analytic_account)
    True
    >>> expense_move_line.analytic_lines[0].debit
    Decimal('0.42')
