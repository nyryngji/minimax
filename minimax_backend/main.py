from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import oracledb
import pandas as pd
import random
from prediction_all import *
from prediction_all import predict_pKd, predict_pKi, make_smiles, toxic_predict
import torch
import random


app = FastAPI()

oracledb.init_oracle_client(lib_dir=r"D:\\instantclient_23_9")

conn = oracledb.connect(
    user="adsql",          # 사용자명
    password="oracle_4U",      # 비밀번호
    dsn="localhost:1521/xe" # 접속 정보 (SQL Developer와 동일)
)
cur = conn.cursor()

# 프론트엔드와 통신 허용 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중엔 * 허용 (배포 시 도메인 지정)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/user_diy")
async def predict(request: Request):
    
    user_input = '사용자한테서 입력받은 분자 이름'
    
    result = {'아직' : '없음'}
    return {"result": result}


@app.post("/from_disease_button") # 버튼 누르면 
async def predict(request: Request):
    
    user_selected_button = '암 치료제' # 누른 버튼 이름
    sql = f"SELECT * FROM disease_input where d_category = '{user_selected_button}'"
    # 암 치료제 등 버튼 누르면 disease_input에서 해당 카테고리의 smiles만 가져옴
    res = pd.read_sql(sql, conn)
    randoms = [0,1]
    orig_molecule = res.iloc[randoms].to_dict(orient='records') # 카테고리별 smiles 2개 관련 정보

    # orig_molecule로 새로운 분자 생성 후에 DB에 저장하는 거까지
    molecule_id_number = 0
    db_col = ['DNEW_CHEMBL_ID', 'DNEW_NAME', 'DNEW_CANOSMILES', 'DNEW_IMAGE_BASE64',
        'DNEW_MOL_WEIGHT', 'DNEW_LOGP', 'DNEW_QED', 'DNEW_HBD', 'DNEW_HBA',
        'DNEW_PKI_RES', 'DNEW_PKI', 'DNEW_PKD_RES', 'DNEW_PKD', 'DNEW_TOXIC',
        'DNEW_CATEGORY']

    print(orig_molecule) # 테스트용이라 지워도 무방함, 서버 제대로 실행 시 터미널창에 기존 분자의 정보가 보임 
    
    generate_molecule_result = []

    for i in orig_molecule:
        for j in range(5):
            cur.execute("SELECT SEQ_DISEASE_GEN.NEXTVAL FROM DUAL")
            seq_val = cur.fetchone()[0]

            torch.manual_seed(torch.randint(0, 1000000, (1,)).item())
            res = [i['D_CHEMBL_ID']] + [f"DNEW_MOLECULE{seq_val}"] + make_smiles(i['D_CANOSMILES'])
            generate_molecule_result.append(res)
            molecule_id_number += 1
    
    for res in generate_molecule_result:
        pki = list(predict_pKi(res[2]))
        pkd = list(predict_pKd(res[2]))
        toxic = [toxic_predict(res[2])]
        res2 = res + pki + pkd + toxic + [i['D_CATEGORY']]
    
        dic = dict(zip(db_col, res2))

        columns = ', '.join(dic.keys())
        placeholders = ', '.join([f':{k}' for k in dic.keys()])

        sql = f"INSERT INTO DISEASE_GENERATIVE ({columns}) VALUES ({placeholders})"

        cur.execute(sql, dic)
        conn.commit()
    
    return {"result": orig_molecule} # 이건 버튼 눌렀을 때 분자 기본 정보 전달 