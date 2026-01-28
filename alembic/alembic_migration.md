(env) odb_admin_1@Mac CareLink % alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade ea35c5fec585 -> bc766f9f008c, add_geolocation_and_capacity_fields
Traceback (most recent call last):
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
    ~~~~~~~~~~~~~~~~~~~~~~~^
        cursor, str_statement, effective_parameters, context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
psycopg2.errors.DuplicateTable: relation "uq_user_role" already exists


The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/opt/anaconda3/envs/env/bin/alembic", line 8, in <module>
    sys.exit(main())
             ~~~~^^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/config.py", line 1033, in main
    CommandLine(prog=prog).main(argv=argv)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/config.py", line 1023, in main
    self.run_cmd(cfg, options)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/config.py", line 957, in run_cmd
    fn(
    ~~^
        config,
        ^^^^^^^
        *[getattr(options, k, None) for k in positional],
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        **{k: getattr(options, k, None) for k in kwarg},
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/command.py", line 483, in upgrade
    script.run_env()
    ~~~~~~~~~~~~~~^^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/script/base.py", line 545, in run_env
    util.load_python_file(self.dir, "env.py")
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/util/pyfiles.py", line 116, in load_python_file
    module = load_module_py(module_id, path)
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/util/pyfiles.py", line 136, in load_module_py
    spec.loader.exec_module(module)  # type: ignore
    ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "<frozen importlib._bootstrap_external>", line 1027, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/Users/odb_admin_1/CareLink/alembic/env.py", line 124, in <module>
    run_migrations_online()
    ~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/odb_admin_1/CareLink/alembic/env.py", line 103, in run_migrations_online
    context.run_migrations()
    ~~~~~~~~~~~~~~~~~~~~~~^^
  File "<string>", line 8, in run_migrations
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/runtime/environment.py", line 946, in run_migrations
    self.get_context().run_migrations(**kw)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/runtime/migration.py", line 627, in run_migrations
    step.migration_fn(**kw)
    ~~~~~~~~~~~~~~~~~^^^^^^
  File "/Users/odb_admin_1/CareLink/alembic/versions/2025_12_17_1353_add_geolocation_and_capacity_fields.py", line 125, in upgrade
    op.create_unique_constraint('uq_user_role', 'user_roles', ['user_id', 'role_id'])
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 8, in create_unique_constraint
  File "<string>", line 3, in create_unique_constraint
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/operations/ops.py", line 498, in create_unique_constraint
    return operations.invoke(op)
           ~~~~~~~~~~~~~~~~~^^^^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/operations/base.py", line 454, in invoke
    return fn(self, operation)
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/operations/toimpl.py", line 202, in create_constraint
    operations.impl.add_constraint(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        operation.to_constraint(operations.migration_context)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/ddl/impl.py", line 404, in add_constraint
    self._exec(schema.AddConstraint(const))
    ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/alembic/ddl/impl.py", line 246, in _exec
    return conn.execute(construct, params)
           ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 1419, in execute
    return meth(
        self,
        distilled_parameters,
        execution_options or NO_OPTIONS,
    )
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/sql/ddl.py", line 187, in _execute_on_connection
    return connection._execute_ddl(
           ~~~~~~~~~~~~~~~~~~~~~~~^
        self, distilled_params, execution_options
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 1530, in _execute_ddl
    ret = self._execute_context(
        dialect,
    ...<4 lines>...
        compiled,
    )
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ~~~~~~~~~~~~~~~~~~~~~~~~~^
        dialect, context, statement, parameters
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        e, str_statement, effective_parameters, cursor, context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
    ~~~~~~~~~~~~~~~~~~~~~~~^
        cursor, str_statement, effective_parameters, context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/anaconda3/envs/env/lib/python3.13/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateTable) relation "uq_user_role" already exists
                                                                                                                                                                                                                                                                                                                            
[SQL: ALTER TABLE user_roles ADD CONSTRAINT uq_user_role UNIQUE (user_id, role_id)]                                                                                                                                                                                                                                         
(Background on this error at: https://sqlalche.me/e/20/f405)                                                                                                                                                                                                                                                                
(env) odb_admin_1@Mac CareLink % 