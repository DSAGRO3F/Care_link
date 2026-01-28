(env) odb_admin_1@admin-odbs-MacBook-Air CareLink % tree -I '__pycache__|*.pyc|env|.git|*.egg-info'
.
├── __init__.py
├── alembic
│   ├── README
│   ├── alembic_migration.md
│   ├── env.py
│   ├── script.py.mako
│   └── versions
│       ├── 2025_01_12_add_rls_policies.py
│       ├── 2025_01_13_normalize_permissions.py
│       ├── 2025_01_22_1200_add_evaluation_sessions.py
│       ├── 2026_01_05_1002_initial_schema_v4_1_with_multitenant.py
│       ├── 2026_01_12_1005_add_multitenant_support.py
│       └── alembic_migration.md
├── alembic.ini
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── docs
│   │   │   ├── API_DOCUMENTATION.md
│   │   │   └── RLS.md
│   │   └── v1
│   │       ├── __init__.py
│   │       ├── auth
│   │       │   ├── __init__.py
│   │       │   ├── routes.py
│   │       │   ├── schemas.py
│   │       │   └── services.py
│   │       ├── careplan
│   │       │   ├── __init__.py
│   │       │   ├── routes.py
│   │       │   ├── schemas.py
│   │       │   └── services.py
│   │       ├── catalog
│   │       │   ├── __init__.py
│   │       │   ├── routes.py
│   │       │   ├── schemas.py
│   │       │   └── services.py
│   │       ├── coordination
│   │       │   ├── __init__.py
│   │       │   ├── routes.py
│   │       │   ├── schemas.py
│   │       │   └── services.py
│   │       ├── dependencies.py
│   │       ├── organization
│   │       │   ├── __init__.py
│   │       │   ├── routes.py
│   │       │   ├── schemas.py
│   │       │   └── services.py
│   │       ├── patient
│   │       │   ├── __init__.py
│   │       │   ├── routes.py
│   │       │   ├── schemas.py
│   │       │   └── services.py
│   │       ├── platform
│   │       │   ├── __init__.py
│   │       │   ├── routes.py
│   │       │   ├── schemas.py
│   │       │   ├── services.py
│   │       │   └── super_admin_security.py
│   │       ├── router.py
│   │       ├── tenants
│   │       │   ├── __init__.py
│   │       │   ├── routes.py
│   │       │   ├── schemas.py
│   │       │   ├── subscription_routes.py
│   │       │   └── usage_routes.py
│   │       └── user
│   │           ├── __init__.py
│   │           ├── routes.py
│   │           ├── schemas.py
│   │           ├── services.py
│   │           └── tenant_users_security.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── auth
│   │   │   ├── __init__.py
│   │   │   ├── psc.py
│   │   │   └── user_auth.py
│   │   ├── config
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── docs
│   │   │   ├── doc_dependencies.md
│   │   │   └── doc_pro_sante_connect.md
│   │   ├── security
│   │   │   ├── __init__.py
│   │   │   ├── encryption.py
│   │   │   ├── hashing.py
│   │   │   └── jwt.py
│   │   └── session
│   │       ├── __init__.py
│   │       ├── redis_client.py
│   │       ├── session_manager.py
│   │       └── tenant_context.py
│   ├── database
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── base_class.py
│   │   ├── doc_db.md
│   │   ├── init_db.py
│   │   ├── session.py
│   │   └── session_rls.py
│   ├── main.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── careplan
│   │   │   ├── __init__.py
│   │   │   ├── care_plan.py
│   │   │   └── care_plan_service.py
│   │   ├── catalog
│   │   │   ├── __init__.py
│   │   │   ├── entity_service.py
│   │   │   └── service_template.py
│   │   ├── coordination
│   │   │   ├── __init__.py
│   │   │   ├── coordination_entry.py
│   │   │   └── scheduled_intervention.py
│   │   ├── docs
│   │   │   └── carelink_schema_v4.1.dbml
│   │   ├── enums.py
│   │   ├── mixins.py
│   │   ├── organization
│   │   │   ├── __init__.py
│   │   │   └── entity.py
│   │   ├── patient
│   │   │   ├── __init__.py
│   │   │   ├── evaluation_session.py
│   │   │   ├── patient.py
│   │   │   ├── patient_access.py
│   │   │   ├── patient_document.py
│   │   │   ├── patient_evaluation.py
│   │   │   └── patient_vitals.py
│   │   ├── platform
│   │   │   ├── __init__.py
│   │   │   ├── platform_audit_log.py
│   │   │   └── super_admin.py
│   │   ├── reference
│   │   │   ├── __init__.py
│   │   │   └── country.py
│   │   ├── tenants
│   │   │   ├── __init__.py
│   │   │   ├── subscription.py
│   │   │   ├── subscription_usage.py
│   │   │   └── tenant.py
│   │   ├── types.py
│   │   └── user
│   │       ├── __init__.py
│   │       ├── permission.py
│   │       ├── profession.py
│   │       ├── role.py
│   │       ├── role_permission.py
│   │       ├── user.py
│   │       ├── user_associations.py
│   │       ├── user_availability.py
│   │       └── user_tenant_assignment.py
│   └── services
│       ├── __init__.py
│       ├── aggir
│       │   ├── AGGIR_README.md
│       │   ├── Guide-grille-AGGIR.pdf
│       │   ├── __init__.py
│       │   ├── calculator.py
│       │   ├── parser.py
│       │   └── test_aggir.py
│       ├── schemas
│       │   ├── __init__.py
│       │   └── json_schemas
│       │       ├── __init__.py
│       │       ├── aggir_only_v1.json
│       │       ├── evaluation_v1.json
│       │       └── evaluation_v2.json
│       └── validation
│           ├── __init__.py
│           └── schema_validator.py
├── arborescence.txt
├── assets
│   ├── carelink_logo.jpg
│   └── carelink_logo_hd.jpg
├── backend
├── docs
│   ├── DELOIN_ALAIN_23_09_2025.json
│   ├── Questions_structuration_UI.md
│   └── carelink_backend_specifications_v4_4.md
├── frontend
├── keys
│   ├── jwt_private_key.pem
│   └── jwt_public_key.pem
├── pyproject.toml
├── pytest.ini 
├── requirements-dev.txt
├── requirements.in
├── requirements.txt
├── scripts
│   ├── __init__.py
│   ├── generate_keys.py
│   ├── init_database.py
│   ├── seed_test_data.py
│   └── verify_rls.sql
├── tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api
│   │   ├── __init__.py
│   │   ├── test_careplan.py
│   │   ├── test_catalog.py
│   │   ├── test_coordination.py
│   │   ├── test_organization.py
│   │   ├── test_patient.py
│   │   ├── test_tenants.py
│   │   └── test_user.py
│   ├── test_database
│   │   ├── __init__.py
│   │   └── test_init_db.py
│   ├── test_models
│   │   ├── __init__.py
│   │   ├── test_availability.py
│   │   ├── test_base_models.py
│   │   ├── test_careplan.py
│   │   ├── test_catalog.py
│   │   ├── test_coordination.py
│   │   ├── test_patient.py
│   │   ├── test_scheduled_intervention.py
│   │   ├── test_tenant.py
│   │   └── test_user.py
│   └── test_rls.py
└── tree.md

49 directories, 180 files
(env) odb_admin_1@admin-odbs-MacBook-Air CareLink % 


























