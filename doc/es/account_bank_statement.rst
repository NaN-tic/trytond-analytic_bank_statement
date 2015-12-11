#:before:account_bank_statement/account_bank_statement:bullet_list:concile#

.. TODO: Cambiar la herencia

Si la cuenta contable seleccionada en la |transaction_lines| tiene analítica obligatoria, o la tiene opcional y queremos incluir el importe del apunte en la analítica, rellenaremos los campos de la jerarquía correspondiente. Al contabilizar la línea del extracto y crearse el asiento, también se crearán los apuntes analíticos correspondientes.

.. |transaction_lines| field:: account.bank.statement.line/lines
