# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.modules.analytic_account import AnalyticMixin
from trytond.pool import Pool, PoolMeta

__all__ = ['StatementMoveLine', 'AnalyticAccountEntry']
__metaclass__ = PoolMeta


class StatementMoveLine(AnalyticMixin):
    __name__ = 'account.bank.statement.move.line'

    def _get_move_lines(self):
        pool = Pool()
        AnalyticLine = pool.get('analytic_account.line')

        move_lines = super(StatementMoveLine, self)._get_move_lines()
        if move_lines and self.analytic_accounts:
            for analytic_account in self.analytic_accounts:
                if analytic_account.account:
                    account = analytic_account.account
                    for move_line in move_lines:
                        if move_line.account != self.account:
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


class AnalyticAccountEntry:
    __metaclass__ = PoolMeta
    __name__ = 'analytic.account.entry'

    @classmethod
    def _get_origin(cls):
        origins = super(AnalyticAccountEntry, cls)._get_origin()
        return origins + ['account.bank.statement.move.line']

    @classmethod
    def search_company(cls, name, clause):
        return [('origin.line.company',) + tuple(clause[1:]) +
                tuple(('account.bank.statement.move.line',))]
