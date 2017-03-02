# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pyson import PYSONEncoder
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.model import ModelView, ModelSQL, fields
import copy

__all__ = ['AccountAccountSelection', 'StatementMoveLine', 'Account',
    'AccountSelection']
__metaclass__ = PoolMeta


class AccountAccountSelection(ModelSQL):
    'Analytic Account - Analytic Account Selection'
    __name__ = 'analytic_account.account-analytic_account.account.selection'
    _table = 'analytic_account_account_selection'
    selection = fields.Many2One('analytic_account.account.selection',
            'Selection', ondelete='CASCADE', select=True)
    account = fields.Many2One('analytic_account.account', 'Account',
            ondelete='RESTRICT', select=True)


class Account:
    __name__ = 'analytic_account.account'

    @classmethod
    def convert_view(cls, tree):
        res = tree.xpath('//field[@name=\'analytic_accounts\']')
        if not res:
            return
        element_accounts = res[0]
        root_accounts = cls.search([
                ('parent', '=', None),
                ])
        if not root_accounts:
            element_accounts.getparent().getparent().remove(
                    element_accounts.getparent())
            return
        for account in root_accounts:
            newelement = copy.copy(element_accounts)
            newelement.tag = 'label'
            newelement.set('name', 'analytic_account_' + str(account.id))
            element_accounts.addprevious(newelement)
            newelement = copy.copy(element_accounts)
            newelement.set('name', 'analytic_account_' + str(account.id))
            element_accounts.addprevious(newelement)
        parent = element_accounts.getparent()
        parent.remove(element_accounts)

    @classmethod
    def analytic_accounts_fields_get(cls, field, fields_names=None,
            states=None, required_states=None):
        res = {}
        if fields_names is None:
            fields_names = []
        if states is None:
            states = {}

        encoder = PYSONEncoder()

        root_accounts = cls.search([
                ('parent', '=', None),
                ('company', '=', Transaction().context.get('company', -1)),
                ])
        for account in root_accounts:
            name = 'analytic_account_' + str(account.id)
            if name in fields_names or not fields_names:
                res[name] = field.copy()
                field_states = states.copy()
                if account.mandatory:
                    if required_states:
                        field_states['required'] = required_states
                    else:
                        field_states['required'] = True
                res[name]['states'] = encoder.encode(field_states)
                res[name]['string'] = account.name
                res[name]['relation'] = cls.__name__
                res[name]['domain'] = PYSONEncoder().encode([
                    ('root', '=', account.id),
                    ('type', '=', 'normal'),
                    ('company', '=', account.company.id)])
        return res


class AccountSelection(ModelSQL, ModelView):
    'Analytic Account Selection'
    __name__ = 'analytic_account.account.selection'

    accounts = fields.Many2Many(
            'analytic_account.account-analytic_account.account.selection',
            'selection', 'account', 'Accounts')

    @classmethod
    def __setup__(cls):
        super(AccountSelection, cls).__setup__()
        cls._error_messages.update({
                'root_account': ('Can not have many accounts with the same '
                    'root or a missing mandatory root account on "%s".'),
                })

    @classmethod
    def validate(cls, selections):
        super(AccountSelection, cls).validate(selections)
        cls.check_root(selections)

    @classmethod
    def check_root(cls, selections):
        "Check Root"
        Account = Pool().get('analytic_account.account')

        root_accounts = Account.search([
            ('parent', '=', None),
            ])

        for selection in selections:
            roots = []
            for account in selection.accounts:
                if account.root.id in roots:
                    cls.raise_user_error('root_account', (account.rec_name,))
                roots.append(account.root.id)
            if Transaction().user:  # Root can by pass
                for account in root_accounts:
                    if account.mandatory:
                        if account.id not in roots:
                            cls.raise_user_error('root_account',
                                (account.rec_name,))


class StatementMoveLine:
    __name__ = 'account.bank.statement.move.line'
    analytic_accounts = fields.Many2One('analytic_account.account.selection',
        'Analytic Accounts')

    @classmethod
    def _view_look_dom_arch(cls, tree, type, field_children=None):
        AnalyticAccount = Pool().get('analytic_account.account')
        convert_view = True
        if type == 'tree':
            # AnalyticAccount.convert_view(tree) doesn't suport well tree views
            root_accounts = AnalyticAccount.search([
                    ('parent', '=', None),
                    ])
            if not root_accounts:
                convert_view = False
        if convert_view:
            AnalyticAccount.convert_view(tree)
        return super(StatementMoveLine, cls)._view_look_dom_arch(tree, type,
            field_children=field_children)

    @classmethod
    def fields_get(cls, fields_names=None):
        AnalyticAccount = Pool().get('analytic_account.account')

        fields = super(StatementMoveLine, cls).fields_get(fields_names)

        analytic_accounts_field = super(StatementMoveLine, cls).fields_get(
                ['analytic_accounts'])['analytic_accounts']

        fields.update(AnalyticAccount.analytic_accounts_fields_get(
                analytic_accounts_field, fields_names))
        return fields

    @classmethod
    def default_get(cls, fields, with_rec_name=True):
        fields = [x for x in fields if not x.startswith('analytic_account_')]
        return super(StatementMoveLine, cls).default_get(fields,
            with_rec_name=with_rec_name)

    @classmethod
    def read(cls, ids, fields_names=None):
        if fields_names:
            fields_names2 = [x for x in fields_names
                    if not x.startswith('analytic_account_')]
        else:
            fields_names2 = fields_names

        res = super(StatementMoveLine, cls).read(ids,
            fields_names=fields_names2)

        if not fields_names:
            fields_names = cls._fields.keys()

        root_ids = []
        for field in fields_names:
            if field.startswith('analytic_account_') and '.' not in field:
                root_ids.append(int(field[len('analytic_account_'):]))
        if root_ids:
            id2record = {}
            for record in res:
                id2record[record['id']] = record
            lines = cls.browse(ids)
            for line in lines:
                for root_id in root_ids:
                    id2record[line.id]['analytic_account_'
                        + str(root_id)] = None
                if not line.analytic_accounts:
                    continue
                for account in line.analytic_accounts.accounts:
                    if account.root.id in root_ids:
                        id2record[line.id]['analytic_account_'
                            + str(account.root.id)] = account.id
                        for field in fields_names:
                            if field.startswith('analytic_account_'
                                    + str(account.root.id) + '.'):
                                ham, field2 = field.split('.', 1)
                                id2record[line.id][field] = account[field2]
        return res

    @classmethod
    def create(cls, vlist):
        Selection = Pool().get('analytic_account.account.selection')
        vlist = [x.copy() for x in vlist]
        for vals in vlist:
            selection_vals = {}
            for field in vals.keys():
                if field.startswith('analytic_account_'):
                    if vals[field]:
                        selection_vals.setdefault('accounts', [])
                        selection_vals['accounts'].append(('add',
                                [vals[field]]))
                    del vals[field]
            if vals.get('analytic_accounts'):
                Selection.write([Selection(vals['analytic_accounts'])],
                    selection_vals)
            elif selection_vals:
                selection, = Selection.create([selection_vals])
                vals['analytic_accounts'] = selection.id
        return super(StatementMoveLine, cls).create(vlist)

    @classmethod
    def write(cls, *args):
        Selection = Pool().get('analytic_account.account.selection')
        actions = iter(args)
        args = []
        for lines, values in zip(actions, actions):
            values = values.copy()
            selection_vals = {}
            for field, value in values.items():
                if field.startswith('analytic_account_'):
                    root_id = int(field[len('analytic_account_'):])
                    selection_vals[root_id] = value
                    del values[field]
            if selection_vals:
                for line in lines:
                    accounts = []
                    if not line.analytic_accounts:
                        # Create missing selection
                        selection, = Selection.create([{}])
                        cls.write([line], {
                                'analytic_accounts': selection.id,
                                })
                    for account in line.analytic_accounts.accounts:
                        if account.root.id in selection_vals:
                            value = selection_vals[account.root.id]
                            if value:
                                accounts.append(value)
                        else:
                            accounts.append(account.id)
                    for account_id in selection_vals.values():
                        if account_id \
                                and account_id not in accounts:
                            accounts.append(account_id)
                    to_remove = list(
                        set((a.id for a in line.analytic_accounts.accounts))
                        - set(accounts))
                    Selection.write([line.analytic_accounts], {
                            'accounts': [
                                ('remove', to_remove),
                                ('add', accounts),
                                ],
                            })
            args.extend((lines, values))
        super(StatementMoveLine, cls).write(*args)

    @classmethod
    def delete(cls, lines):
        Selection = Pool().get('analytic_account.account.selection')

        selection_ids = []
        for line in lines:
            if line.analytic_accounts:
                selection_ids.append(line.analytic_accounts.id)

        super(StatementMoveLine, cls).delete(lines)
        Selection.delete(Selection.browse(selection_ids))

    @classmethod
    def copy(cls, lines, default=None):
        Selection = Pool().get('analytic_account.account.selection')

        new_lines = super(StatementMoveLine, cls).copy(lines, default=default)

        for line in new_lines:
            if line.analytic_accounts:
                selection, = Selection.copy([line.analytic_accounts])
                cls.write([line], {
                        'analytic_accounts': selection.id,
                        })
        return new_lines

    def _get_move_lines(self):
        pool = Pool()
        AnalyticLine = pool.get('analytic_account.line')

        move_lines = super(StatementMoveLine, self)._get_move_lines()
        if (move_lines and self.analytic_accounts
                and self.analytic_accounts.accounts):
            for move_line in move_lines:
                if move_line.account != self.account:
                    continue
                move_line.analytic_lines = []
                for account in self.analytic_accounts.accounts:
                    analytic_line = AnalyticLine()
                    analytic_line.name = (self.description if self.description
                        else self.line.description)
                    analytic_line.debit = move_line.debit
                    analytic_line.credit = move_line.credit
                    analytic_line.account = account
                    analytic_line.journal = self.line.journal.journal
                    analytic_line.date = self.date
                    analytic_line.reference = (self.invoice.reference
                        if self.invoice else None)
                    analytic_line.party = self.party

                    list(move_line.analytic_lines).append(analytic_line)
        return move_lines
