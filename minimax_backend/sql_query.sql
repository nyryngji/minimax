CREATE SEQUENCE SEQ_DISEASE_GEN
START WITH 1       
INCREMENT BY 1       
NOCACHE              
NOCYCLE; 

CREATE SEQUENCE SEQ_USER_GEN
START WITH 1       
INCREMENT BY 1       
NOCACHE              
NOCYCLE; 

CREATE TABLE user_input 
    ( 
     u_chembl_id    VARCHAR2 (100)  NOT NULL , 
     u_name         VARCHAR2 (100)  NOT NULL , 
     u_canosmiles   VARCHAR2 (500)  NOT NULL , 
     u_formula      VARCHAR2 (300)  NOT NULL , 
     u_type         VARCHAR2 (100)  NOT NULL , 
     u_image_base64 CLOB  NOT NULL 
    ) 
;
ALTER TABLE user_input 
    ADD CONSTRAINT disease_scaffold_dbv1_PK PRIMARY KEY ( u_chembl_id ) ;


CREATE TABLE disease_generative 
    ( 
     dnew_chembl_id    VARCHAR2 (100)  NOT NULL , 
     dnew_name         VARCHAR2 (100)  NOT NULL , 
     dnew_canosmiles   VARCHAR2 (500)  NOT NULL , 
     dnew_image_base64 CLOB  NOT NULL , 
     dnew_mol_weight   NUMBER  NOT NULL , 
     dnew_logp         NUMBER  NOT NULL , 
     dnew_qed          NUMBER  NOT NULL , 
     dnew_hbd          NUMBER  NOT NULL , 
     dnew_hba          NUMBER  NOT NULL , 
     dnew_pki_res      VARCHAR2 (20)  NOT NULL , 
     dnew_pki          NUMBER  NOT NULL , 
     dnew_pkd_res      VARCHAR2 (20)  NOT NULL , 
     dnew_pkd          NUMBER  NOT NULL , 
     dnew_toxic        NUMBER  NOT NULL , 
     dnew_category     VARCHAR2 (20)  NOT NULL 
    ) 
;

ALTER TABLE disease_generative 
    ADD CONSTRAINT disease_inputv1_PK PRIMARY KEY ( dnew_name ) ;

CREATE TABLE disease_input 
    ( 
     d_chembl_id       VARCHAR2 (100)  NOT NULL , 
     d_name            VARCHAR2 (100)  NOT NULL , 
     d_canosmiles      VARCHAR2 (500)  NOT NULL , 
     d_formula         VARCHAR2 (300)  NOT NULL , 
     d_type            VARCHAR2 (100)  NOT NULL , 
     d_detail_category VARCHAR2 (20)  NOT NULL , 
     d_image_base64    CLOB  NOT NULL , 
     d_category        VARCHAR2 (20)  NOT NULL 
    ) 
;

ALTER TABLE disease_input 
    ADD CONSTRAINT disease_scaffold_db_PK PRIMARY KEY ( d_name ) ;

DROP TABLE USER_GENERATIVE;

CREATE TABLE user_generative 
    ( 
     unew_chembl_id    VARCHAR2 (100)  NOT NULL , 
     unew_name         VARCHAR2 (100)  NOT NULL , 
     unew_canosmiles   VARCHAR2 (500)  NOT NULL , 
     unew_image_base64 CLOB  NOT NULL , 
     unew_mol_weight   NUMBER  NOT NULL , 
     unew_logp         NUMBER  NOT NULL , 
     unew_qed          NUMBER  NOT NULL , 
     unew_hbd          NUMBER  NOT NULL , 
     unew_hba          NUMBER  NOT NULL , 
     unew_pki_res      VARCHAR2 (20)  NOT NULL , 
     unew_pki          NUMBER  NOT NULL , 
     unew_pkd_res      VARCHAR2 (20)  NOT NULL , 
     unew_pkd          NUMBER  NOT NULL , 
     unew_toxic        NUMBER  NOT NULL 
    ) 
;
ALTER TABLE user_generative 
    ADD CONSTRAINT disease_generativev1_PK PRIMARY KEY ( unew_name, unew_canosmiles ) ;

CREATE TABLE optim_molecule 
    ( 
     onew_origin_name  VARCHAR2 (100)  NOT NULL , 
     onew_name         VARCHAR2 (100)  NOT NULL , 
     onew_canosmiles   VARCHAR2 (500)  NOT NULL , 
     onew_image_base64 CLOB  NOT NULL , 
     onew_mol_weight   NUMBER  NOT NULL , 
     onew_logp         NUMBER  NOT NULL , 
     onew_qed          NUMBER  NOT NULL , 
     onew_hbd          NUMBER  NOT NULL , 
     onew_hba          NUMBER  NOT NULL , 
     onew_pki_res      VARCHAR2 (20)  NOT NULL , 
     onew_pki          NUMBER  NOT NULL , 
     onew_pkd_res      VARCHAR2 (20)  NOT NULL , 
     onew_pkd          NUMBER  NOT NULL , 
     onew_toxic        NUMBER  NOT NULL , 
     onew_optim_time   DATE  NOT NULL 
    ) 
;

ALTER TABLE optim_molecule 
    ADD CONSTRAINT disease_generativev1_PKv1 PRIMARY KEY ( onew_name ) ;


