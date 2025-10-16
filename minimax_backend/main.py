from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import oracledb
import pandas as pd
import random
from prediction_all import *
import torch
import random
from chembl_webresource_client.new_client import new_client
from other_function import return_user_input_from_chembl

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

# 여기부터 백엔드 코드 시작

@app.post("/user_diy")
async def predict(request: Request): 
    
    cur.execute("TRUNCATE TABLE USER_INPUT") 
    # 이거 똑같은 분자 입력되면 중복돼서 DB 오류나서 이렇게 한거에여
    # 만약 입력할 때 계속 다른 거 넣으면 오류는 안 날듯
    conn.commit()

    # 프엔 작업!!!!!
    user_input = 'caffeine' # 입력 (사용자한테 분자 이름 받아야 함, 이거 프엔 작업 해주세용!!)
    user_input_info = return_chembl_data(user_input) # 리스트로 나옴

    # 입력 받은 분자 이름으로 chembl에서 정보 찾기
    sql = "select * from user_input where rownum <= 1" 
    select_user_input = pd.read_sql(sql, conn)
    user_input_col = list(select_user_input.columns)
    user_input_data = return_chembl_data(user_input)
    insert_data('user_input', user_input_col, user_input_data) # 사용자가 입력한 분자 DB에 저장

    return_value = dict(zip(user_input_col, user_input_data))

    # 사용자가 입력한 분자로 예측 수행하기
    select_user_gen = "select * from user_generative where rownum <= 1" 
    user_gen_db = pd.read_sql(select_user_gen, conn)
    user_gen_col = list(user_gen_db.columns)
    user_generate_molecule_result = [] # 새로 만들어진 분자 

    for j in range(5):
        cur.execute("SELECT SEQ_USER_GEN.NEXTVAL FROM DUAL")
        seq_user_gen_val = cur.fetchone()[0]

        torch.manual_seed(torch.randint(0, 1000000, (1,)).item())
        user_gen_data = [return_value['U_CHEMBL_ID']] + [f"UNEW_MOLECULE{seq_user_gen_val}"] + make_smiles(return_value['U_CANOSMILES'])
        user_generate_molecule_result.append(user_gen_data)

    for user_gen_row in user_generate_molecule_result:
        pki = list(predict_pKi(user_gen_row[2]))
        pkd = list(predict_pKd(user_gen_row[2]))
        toxic = [toxic_predict(user_gen_row[2])]
        user_gen_data2 = user_gen_row + pki + pkd + toxic

        user_gen_dic = dict(zip(user_gen_col, user_gen_data2))

        columns = ', '.join(user_gen_col)
        placeholders = ', '.join([f':{k}' for k in user_gen_col])

        insert_user_gen_sql = f"INSERT INTO USER_GENERATIVE ({columns}) VALUES ({placeholders})"

        cur.execute(insert_user_gen_sql, user_gen_dic)
        conn.commit()
    
    return {"user_input_data": return_value} # 반환값 : 사용자가 입력한 분자 정보


@app.post("/from_disease_button") 
async def predict(request: Request):
    
    # 프엔 해주세여!!!!!
    user_selected_button = '암 치료제' # 입력 : 누른 버튼 이름 
    sql = f"SELECT * FROM disease_input where d_category = '{user_selected_button}'"
    # 암 치료제 등 버튼 누르면 disease_input에서 해당 카테고리의 smiles만 가져옴
    res = pd.read_sql(sql, conn)
    randoms = [0,1]
    orig_molecule = res.iloc[randoms].to_dict(orient='records') # 카테고리별 smiles 2개 관련 정보

    # orig_molecule로 새로운 분자 생성 후에 DB에 저장하는 거까지
    molecule_id_number = 0
    db_col = list(res.columns)
    
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