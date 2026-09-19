-- Nemo initial PostgreSQL schema v1. One VC, multiple companies.

BEGIN;


CREATE TABLE vc (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (id=1)
)

;


CREATE TABLE companies (
	id VARCHAR NOT NULL, 
	vc_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	settings JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vc_id) REFERENCES vc (id)
)

;


CREATE TABLE actors (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	company_id VARCHAR, 
	token_hash VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (role IN ('vc','company')), 
	CHECK ((role='vc' AND company_id IS NULL) OR (role='company' AND company_id IS NOT NULL)), 
	FOREIGN KEY(company_id) REFERENCES companies (id), 
	UNIQUE (token_hash)
)

;


CREATE TABLE report_requests (
	id VARCHAR NOT NULL, 
	company_id VARCHAR NOT NULL, 
	period_start VARCHAR NOT NULL, 
	period_end VARCHAR NOT NULL, 
	scenario VARCHAR NOT NULL, 
	revision INTEGER NOT NULL, 
	draft JSON NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (company_id, period_start, period_end, scenario), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
)

;


CREATE TABLE documents (
	id VARCHAR NOT NULL, 
	report_id VARCHAR NOT NULL, 
	filename VARCHAR NOT NULL, 
	sha256 VARCHAR NOT NULL, 
	path VARCHAR NOT NULL, 
	uploaded_by VARCHAR, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (report_id, sha256), 
	FOREIGN KEY(report_id) REFERENCES report_requests (id), 
	FOREIGN KEY(uploaded_by) REFERENCES actors (id)
)

;


CREATE TABLE import_batches (
	source_key VARCHAR NOT NULL, 
	sha256 VARCHAR NOT NULL, 
	report_id VARCHAR NOT NULL, 
	PRIMARY KEY (source_key), 
	FOREIGN KEY(report_id) REFERENCES report_requests (id)
)

;


CREATE TABLE messages (
	id VARCHAR NOT NULL, 
	report_id VARCHAR NOT NULL, 
	actor_id VARCHAR, 
	question_id VARCHAR, 
	body TEXT NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(report_id) REFERENCES report_requests (id), 
	FOREIGN KEY(actor_id) REFERENCES actors (id)
)

;


CREATE TABLE questions (
	report_id VARCHAR NOT NULL, 
	question_id VARCHAR NOT NULL, 
	field VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	payload JSON NOT NULL, 
	PRIMARY KEY (report_id, question_id), 
	FOREIGN KEY(report_id) REFERENCES report_requests (id)
)

;


CREATE TABLE report_fields (
	report_id VARCHAR NOT NULL, 
	field VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	payload JSON NOT NULL, 
	PRIMARY KEY (report_id, field), 
	FOREIGN KEY(report_id) REFERENCES report_requests (id)
)

;


CREATE TABLE report_versions (
	id VARCHAR NOT NULL, 
	report_id VARCHAR NOT NULL, 
	version INTEGER NOT NULL, 
	revision INTEGER NOT NULL, 
	snapshot JSON NOT NULL, 
	submitted_by VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (report_id, version), 
	UNIQUE (report_id, revision), 
	FOREIGN KEY(report_id) REFERENCES report_requests (id), 
	FOREIGN KEY(submitted_by) REFERENCES actors (id)
)

;


CREATE TABLE extraction_runs (
	id VARCHAR NOT NULL, 
	report_id VARCHAR NOT NULL, 
	document_id VARCHAR, 
	reader VARCHAR NOT NULL, 
	model VARCHAR, 
	payload JSON NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(report_id) REFERENCES report_requests (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
)

;


CREATE TABLE report_updates (
	id VARCHAR NOT NULL, 
	report_id VARCHAR NOT NULL, 
	version_id VARCHAR NOT NULL, 
	actor_id VARCHAR, 
	kind VARCHAR NOT NULL, 
	body TEXT NOT NULL, 
	document_id VARCHAR, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(report_id) REFERENCES report_requests (id), 
	FOREIGN KEY(version_id) REFERENCES report_versions (id), 
	FOREIGN KEY(actor_id) REFERENCES actors (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
)

;


CREATE TABLE scan_jobs (
	id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	error TEXT, 
	created_at VARCHAR NOT NULL, 
	finished_at VARCHAR, 
	PRIMARY KEY (id), 
	CHECK (status IN ('queued','running','succeeded','failed')), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
)

;


CREATE TABLE field_candidates (
	id VARCHAR NOT NULL, 
	report_id VARCHAR NOT NULL, 
	run_id VARCHAR, 
	field VARCHAR NOT NULL, 
	candidate_key VARCHAR NOT NULL, 
	amount NUMERIC(24, 6), 
	payload JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (report_id, field, candidate_key), 
	FOREIGN KEY(report_id) REFERENCES report_requests (id), 
	FOREIGN KEY(run_id) REFERENCES extraction_runs (id)
)

;

INSERT INTO vc(id,name) VALUES (1,'TGH Ventures — demo');

CREATE FUNCTION nemo_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Submitted versions and updates are immutable'; END $$;

CREATE TRIGGER prevent_mutation BEFORE UPDATE OR DELETE ON report_versions FOR EACH ROW EXECUTE FUNCTION nemo_immutable();

CREATE TRIGGER prevent_mutation BEFORE UPDATE OR DELETE ON report_updates FOR EACH ROW EXECUTE FUNCTION nemo_immutable();

COMMIT;