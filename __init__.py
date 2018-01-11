# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool

from . import statement


def register():
    Pool.register(
        statement.BankJournal,
        statement.StatementMoveLine,
        statement.AnalyticAccountEntry,
        module='analytic_bank_statement', type_='model')
