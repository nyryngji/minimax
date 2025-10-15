CREATE SEQUENCE SEQ_DISEASE_GEN
START WITH 1       
INCREMENT BY 1       
NOCACHE              
NOCYCLE; 

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


select * from DISEASE_GENERATIVE;