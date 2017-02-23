# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .statement import *


def register():
    Pool.register(
        AccountAccountSelection,
        StatementMoveLine,
        Account,
        AccountSelection,
        module='analytic_bank_statement', type_='model')
