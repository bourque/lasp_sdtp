CREATE SEQUENCE file_metadata_seq
    INCREMENT BY 1 START WITH 1
    MINVALUE 1 MAXVALUE 999999999999999
    NOCYCLE CACHE 2;

CREATE TABLE file_metadata (
    fileid NUMBER(15) NOT NULL,
    name VARCHAR2(255) NOT NULL,
    checksum VARCHAR2(71) NOT NULL,
    "size" FLOAT NOT NULL,
    expires VARCHAR2(10) NOT NULL,
    stream VARCHAR2(255) NOT NULL,
    shortname VARCHAR(255) NOT NULL,
    version VARCHAR2(3) NOT NULL,
    PRIMARY KEY(fileid)
);

CREATE OR REPLACE TRIGGER file_metadata_trg
BEFORE INSERT ON "FILE_METADATA"
FOR EACH ROW
BEGIN
    IF :new.fileid IS NULL THEN
        SELECT file_metadata_seq.nextval INTO :new.fileid FROM DUAL;
    END IF;
END;


CREATE SEQUENCE file_queue_seq
    INCREMENT BY 1 START WITH 1
    MINVALUE 1 MAXVALUE 9999999999999999999999999999
    NOCYCLE CACHE 2;

CREATE TABLE file_queue (
    queueid NUMBER NOT NULL,
    subscriber_name VARCHAR2(255) NOT NULL unique,
    fileid NUMBER NOT NULL unique,
    entry_date VARCHAR(10) NOT NULL,
    expires VARCHAR(10) NOT NULL,
    PRIMARY KEY(queueid)
    );

CREATE OR REPLACE TRIGGER file_queue_trg
BEFORE INSERT ON "FILE_QUEUE"
FOR EACH ROW
BEGIN
    IF :new.queueid IS NULL THEN
        SELECT file_queue_seq.nextval INTO :new.queueid FROM DUAL;
    END IF;
END;