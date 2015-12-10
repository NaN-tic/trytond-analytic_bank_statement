================================
Analytic Bank Statement Scenario
================================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()
    >>> now = datetime.datetime.now()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install account_bank_statement::

    >>> Module = Model.get('ir.module.module')
    >>> account_bank_module, = Module.find(
    ...     [('name', '=', 'analytic_bank_statement')])
    >>> Module.install([account_bank_module.id], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='US Dollar', symbol=u'$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[]',
    ...         mon_decimal_point='.')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name=str(today.year))
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_seq = Sequence(name=str(today.year), code='account.move',
    ...     company=company)
    >>> post_move_seq.save()
    >>> fiscalyear.post_move_sequence = post_move_seq
    >>> invoice_seq = SequenceStrict(name=str(today.year),
    ...     code='account.invoice', company=company)
    >>> invoice_seq.save()
    >>> fiscalyear.out_invoice_sequence = invoice_seq
    >>> fiscalyear.in_invoice_sequence = invoice_seq
    >>> fiscalyear.out_credit_note_sequence = invoice_seq
    >>> fiscalyear.in_credit_note_sequence = invoice_seq
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> account_tax, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('company', '=', company.id),
    ...         ('name', '=', 'Main Tax'),
    ...         ])
    >>> cash, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('company', '=', company.id),
    ...         ('name', '=', 'Main Cash'),
    ...         ])
    >>> cash.bank_reconcile = True
    >>> cash.reconcile = True
    >>> cash.save()
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')

Create account for bank transactions::

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
    Decimal('-80.0')
    >>> st_move_line.date == today
    True
    >>> st_move_line.amount = Decimal('-0.42')
    >>> st_move_line.account = expense
    >>> st_move_line.description = 'Bank Commission'
    >>> setattr(st_move_line, 'analytic_account_%d' % root.id,
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
    Decimal('-80.0')

Test analytic lines in expected move lines::

    >>> all(not ml.analytic_lines for ml in transaction_line.move.lines)
    True
    >>> cash_move_line, = [ml for ml in commission_line.move.lines
    ...     if ml.account == cash]
    >>> not cash_move_line.analytic_lines
    True
    >>> expense_move_line, = [ml for ml in commission_line.move.lines
    ...     if ml.account == expense]
    >>> len(expense_move_line.analytic_lines)
    1
    >>> (expense_move_line.analytic_lines[0].account
    ...     == bank_commissions_analytic_account)
    True
    >>> expense_move_line.analytic_lines[0].debit
    Decimal('0.42')
