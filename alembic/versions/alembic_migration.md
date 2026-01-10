(env) odb_admin_1@Mac CareLink % alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> ea35c5fec585, initial_schema
(env) odb_admin_1@Mac CareLink % alembic current
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
ea35c5fec585 (head)
(env) odb_admin_1@Mac CareLink % psql -d carelink_db -c "\d entities"
                                               Table "public.entities"
         Column          |            Type             | Collation | Nullable |               Default                
-------------------------+-----------------------------+-----------+----------+--------------------------------------
 id                      | integer                     |           | not null | nextval('entities_id_seq'::regclass)
 name                    | character varying(255)      |           | not null | 
 entity_type             | entity_type_enum            |           | not null | 
 siren                   | character varying(9)        |           |          | 
 finess_et               | character varying(9)        |           |          | 
 address                 | text                        |           |          | 
 phone                   | character varying(20)       |           |          | 
 email                   | character varying(255)      |           |          | 
 country_id              | integer                     |           | not null | 
 created_at              | timestamp without time zone |           | not null | 
 updated_at              | timestamp without time zone |           |          | 
 status                  | character varying           |           | not null | 
 short_name              | character varying(50)       |           |          | 
 integration_type        | integration_type_enum       |           |          | 
 parent_entity_id        | integer                     |           |          | 
 siret                   | character varying(14)       |           |          | 
:...skipping...
                                               Table "public.entities"
         Column          |            Type             | Collation | Nullable |               Default                
-------------------------+-----------------------------+-----------+----------+--------------------------------------
 id                      | integer                     |           | not null | nextval('entities_id_seq'::regclass)
 name                    | character varying(255)      |           | not null | 
 entity_type             | entity_type_enum            |           | not null | 
 siren                   | character varying(9)        |           |          | 
 finess_et               | character varying(9)        |           |          | 
 address                 | text                        |           |          | 
 phone                   | character varying(20)       |           |          | 
 email                   | character varying(255)      |           |          | 
 country_id              | integer                     |           | not null | 
 created_at              | timestamp without time zone |           | not null | 
 updated_at              | timestamp without time zone |           |          | 
 status                  | character varying           |           | not null | 
 short_name              | character varying(50)       |           |          | 
 integration_type        | integration_type_enum       |           |          | 
 parent_entity_id        | integer                     |           |          | 
 siret                   | character varying(14)       |           |          | 
 finess_ej               | character varying(9)        |           |          | 
 authorized_capacity     | integer                     |           |          | 
 authorization_date      | date                        |           |          | 
 authorization_reference | character varying(100)      |           |          | 
 postal_code             | character varying(10)       |           |          | 
 city                    | character varying(100)      |           |          | 
 website                 | character varying(255)      |           |          | 
Indexes:
    "entities_pkey" PRIMARY KEY, btree (id)
    "uq_entities_finess_et" UNIQUE CONSTRAINT, btree (finess_et)
    "uq_entities_siret" UNIQUE CONSTRAINT, btree (siret)
Foreign-key constraints:
    "entities_country_id_fkey" FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE RESTRICT
    "fk_entities_parent_entity_id" FOREIGN KEY (parent_entity_id) REFERENCES entities(id) ON DELETE SET NULL
Referenced by:
    TABLE "entities" CONSTRAINT "fk_entities_parent_entity_id" FOREIGN KEY (parent_entity_id) REFERENCES entities(id) ON DELETE SET NULL
    TABLE "patients" CONSTRAINT "patients_entity_id_fkey" FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE RESTRICT
    TABLE "user_entities" CONSTRAINT "user_entities_entity_id_fkey" FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE

~
(END)