from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import oracledb
import pandas as pd
import random
from prediction_all import *
import torch
import random
from chembl_webresource_client.new_client import new_client

# & 가상환경 시작 & D:/minimax/.venv/Scripts/Activate.ps1
# 웹서버 시작 : uvicorn main:app --reload

app = FastAPI()

# oracledb.init_oracle_client(lib_dir=r"D:\\instantclient_23_9")
try:
    oracledb.init_oracle_client(lib_dir=r"D:\\instantclient_23_9")
    conn = oracledb.connect(
        user="adsql",          
        password="oracle_4U",      
        dsn="localhost:1521/xe" 
    )
    cur = conn.cursor()
    ORACLE_AVAILABLE = True
    print("Oracle database connected successfully")
except Exception as e:
    print(f"Oracle database not available: {e}")
    print("Running without Oracle database...")
    ORACLE_AVAILABLE = False
    conn = None
    cur = None



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
    user_input = 'caffeine'
    user_input_data = return_chembl_data(user_input)

    select_user_input = pd.read_csv('user_input.csv')
    select_user_input = select_user_input.iloc[0:0]

    select_user_input.loc[len(select_user_input)] = user_input_data
    select_user_input.to_csv('user_input.csv',index=False)

    user_input_info = select_user_input.to_dict(orient='records')[0]

    user_gen_db = pd.read_csv('user_generative.csv')
    user_gen_db = user_gen_db.iloc[0:0]

    user_generate_molecule_result = [] 
    unew_names = []

    for j in range(5):
        seq_user_gen_val = j
        user_gen_data = [user_input_info['U_CHEMBL_ID']] + [f"UNEW_MOLECULE{seq_user_gen_val}"]
        try:
            torch.manual_seed(torch.randint(0, 1000000, (1,)).item())
            user_gen_data += make_smiles(user_input_info['U_CANOSMILES'])
            user_generate_molecule_result.append(user_gen_data)
            unew_names.append(f"UNEW_MOLECULE{seq_user_gen_val}")
        except:
            print('에러 발생')
            continue
        print(unew_names)

    for user_gen_row in user_generate_molecule_result:
        try:
            pki = list(predict_pKi(user_gen_row[2]))
            pkd = list(predict_pKd(user_gen_row[2]))
            toxic = [toxic_predict(user_gen_row[2])]
            user_gen_data2 = user_gen_row + pki + pkd + toxic
            user_gen_db.loc[len(user_gen_db)] = user_gen_data2
            print('삽입 완료')
        except:
            unew_names.remove(user_gen_row[1])
            print('데이터 삽입 실패')
            continue

    user_input_info['UNEW_NAMES'] = unew_names
    user_gen_db.to_csv('user_generative.csv',index=False)
    
    with open("user_gen_result.json", "w", encoding="utf-8") as f:
        json.dump(user_input_info, f, ensure_ascii=False, indent=2)
    
    return {'user_generative_result': user_input_info}

@app.post("/button_diy") 
async def predict(request: Request):
    user_selected_button = '암 치료제' # 입력 : 누른 버튼 이름 

    sql = f"SELECT D_CHEMBL_ID, D_CANOSMILES, D_CATEGORY FROM disease_input where d_category = '{user_selected_button}'"
    sql_res = pd.read_sql(sql, conn)

    sql_res = pd.read_csv('disease_input.csv')
    sql_res = sql_res[sql_res['D_CATEGORY'] == user_selected_button]
    randoms = [0,1]
    orig_molecule = sql_res.iloc[randoms].to_dict(orient='records') # 카테고리별 smiles 2개 관련 정보

    sql2_res = pd.read_csv('disease_generative.csv')
    sql2_res = sql2_res.iloc[0:0]
    seq_val = 0 

    for i in orig_molecule:
        dnew_names = []
        generate_molecule_result = []
        for j in range(5):
            res = [i['D_CHEMBL_ID']] + [f"DNEW_MOLECULE{seq_val}"]
            
            try:
                torch.manual_seed(torch.randint(0, 1000000, (1,)).item())
                res += make_smiles(i['D_CANOSMILES'])
                generate_molecule_result.append(res)
                dnew_names.append(f"DNEW_MOLECULE{seq_val}")
            except:
                print('에러 발생')
                continue
            seq_val += 1

        for res in generate_molecule_result:
            try:
                pki = list(predict_pKi(res[2]))
                pkd = list(predict_pKd(res[2]))
                toxic = [toxic_predict(res[2])]
                res2 = res + pki + pkd + toxic + [user_selected_button]
                sql2_res.loc[len(sql2_res)] = res2
                print('삽입 성공')
            except:
                print('데이터 에러 발생')
                continue

        i['dnew_name'] = dnew_names

    with open("button_gen_result.json", "w", encoding="utf-8") as f:
        json.dump(orig_molecule, f, ensure_ascii=False, indent=2)

    sql2_res = sql2_res.drop_duplicates()
    sql2_res.to_csv('disease_generative.csv',index=False)
    
    return {'button_generative_result': orig_molecule}

@app.post("/user_diy_show")
async def predict(request: Request):
    with open('user_gen_result.json', 'r', encoding='utf-8') as f:
        user_gen_result = json.load(f)

    new_moluecule_names = user_gen_result['UNEW_NAMES']

    user_gen_info = pd.read_csv('user_generative.csv')
    user_gen_info = user_gen_info[user_gen_info['UNEW_NAME'].isin(new_moluecule_names)]

    # 이건 새로 생성한 분자 데이터(5개 들어있어여)
    user_gen_info['UNEW_IMAGE_BASE64'] = user_gen_info['UNEW_IMAGE_BASE64'].apply(lambda x: x.read() if hasattr(x, 'read') else x)

    user_gen_info = user_gen_info.to_dict(orient='records')

    with open("user_diy_show.json", "w", encoding="utf-8") as f:
        json.dump(user_gen_info, f, ensure_ascii=False, indent=2)
    
    return {'show_new_user_mol':user_gen_info}
        
@app.post("/button_diy_show")
async def predict(request: Request):
    with open('button_gen_result.json', 'r', encoding='utf-8') as f:
    # json.load() 함수를 사용하여 파일 내용을 딕셔너리로 변환합니다.
        btn_gen_result = json.load(f)
        # 이건 원조 분자용 데이터

    user_click = 0 # 유저가 클릭한 분자

    if user_click == 0: # 0말고 원조 분자 id를 받아와야 할듯
        use_data = btn_gen_result[0] # 첫번째를 누르면 첫번째 원소 불러옴
    else:
        use_data = btn_gen_result[1] # 밑에 누르면 두 번째 원소 불러옴
        
    orig_mol_info = pd.read_csv('disease_input.csv')
    orig_mol_info = orig_mol_info[orig_mol_info['D_CHEMBL_ID'] == use_data['D_CHEMBL_ID']].to_dict(orient='records')

    btn_gen_info = pd.read_csv('disease_generative.csv')
    btn_gen_info = btn_gen_info.drop_duplicates()
    btn_gen_info = btn_gen_info[btn_gen_info['DNEW_NAME'].isin(use_data['dnew_name'])]

    btn_gen_info['DNEW_IMAGE_BASE64'] = btn_gen_info['DNEW_IMAGE_BASE64'].apply(lambda x: x.read() if hasattr(x, 'read') else x)
    btn_gen_info = btn_gen_info.to_dict(orient='records')
    # btn_gen_info : 새로 만들어진 분자 정보

    with open("button_diy_show.json", "w", encoding="utf-8") as f:
        json.dump(btn_gen_info, f, ensure_ascii=False, indent=2)
    
    return {'button_diy_show':btn_gen_info}
    