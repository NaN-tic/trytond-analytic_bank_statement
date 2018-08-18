# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.modules.analytic_account import AnalyticMixin
from trytond.pool import Pool, PoolMeta

__all__ = ['BankJournal', 'StatementMoveLine', 'AnalyticAccountEntry']


class BankJournal(metaclass=PoolMeta):
    __name__ = 'account.bank.statement.journal'
    analytics_on_bank_moves = fields.Boolean('Analytics on Bank Moves',
        help='Generate analytic lines in the move lines on journal accounts '
        'from Bank Statement Move Lines.')


class StatementMoveLine(AnalyticMixin, metaclass=PoolMeta):
    __name__ = 'account.bank.statement.move.line'

    def _get_move_lines(self):
        pool = Pool()
        AnalyticLine = pool.get('analytic_account.line')

        move_lines = super(StatementMoveLine, self)._get_move_lines()

        analytics_on_bank_moves = self.line.statement.journal\
            .analytics_on_bank_moves
        if move_lines and self.analytic_accounts:
            for analytic_account in self.analytic_accounts:
                if analytic_account.account:
                    account = analytic_account.account
                    for move_line in move_lines:
                        if (not analytics_on_bank_moves
                                and move_line.account != self.account):
                            continue
                        analytic_line = AnalyticLine()
                        analytic_line.name = (self.description
                            if self.description
                            else self.line.description)
                        analytic_line.debit = move_line.debit
                        analytic_line.credit = move_line.credit
                        analytic_line.account = account
                        analytic_line.journal = self.line.journal.journal
                        analytic_line.date = self.date
                        analytic_line.reference = (self.invoice.reference
                            if self.invoice else None)
                        analytic_line.party = self.party
                        if not hasattr(move_line, 'analytic_lines'):
                            move_line.analytic_lines = (analytic_line,)
                        else:
                            move_line.analytic_lines += (analytic_line,)

        return move_lines


class AnalyticAccountEntry(metaclass=PoolMeta):
    __name__ = 'analytic.account.entry'

    @classmethod
    def _get_origin(cls):
        origins = super(AnalyticAccountEntry, cls)._get_origin()
        return origins + ['account.bank.statement.move.line']

    @fields.depends('origin')
    def on_change_with_company(self, name=None):
        pool = Pool()
        InvoiceLine = pool.get('account.invoice.line')
        company = super(AnalyticAccountEntry, self).on_change_with_company(
            name=name)
        if isinstance(self.origin, InvoiceLine):
            company = self.origin.company.id
        return company

    @classmethod
    def search_company(cls, name, clause):
        domain = super(AnalyticAccountEntry, cls).search_company(name, clause),
        return ['OR',
            domain,
            (('origin.line.company',) + tuple(clause[1:]) +
                ('account.bank.statement.move.line',)),
            ]
