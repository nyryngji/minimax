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
    cur.execute("TRUNCATE TABLE USER_GENERATIVE") 
    # 이거 똑같은 분자 입력되면 중복돼서 DB 오류나서 이렇게 한거에여
    # 만약 입력할 때 계속 다른 거 넣으면 오류는 안 날듯
    conn.commit()

    user_input = 'caffeine' # 입력 (사용자한테 분자 이름 받아야 함)

    sql = "select * from user_input where rownum <= 1" 
    select_user_input = pd.read_sql(sql, conn)
    user_input_col = list(select_user_input.columns)

    # 입력 받은 분자 이름으로 chembl에서 정보 찾기, 근데 만약 없으면 밑에 코드 안 실행하고 바로 에러 반환
    try:
        user_input_data = return_chembl_data(user_input) 
        insert_data('user_input', user_input_col, user_input_data)
        user_input_info = dict(zip(user_input_col, user_input_data))
    except:
        print('유효하지 않은 분자입니다.')
        return {'error_msg':'유효하지 않은 분자입니다.'}

    # 있으면 사용자가 입력한 분자로 예측 수행하기
    select_user_gen = "select * from user_generative where rownum <= 1" 
    user_gen_db = pd.read_sql(select_user_gen, conn)
    user_gen_col = list(user_gen_db.columns)

    user_generate_molecule_result = [] 
    unew_names = []

    for j in range(5):
        cur.execute("SELECT SEQ_USER_GEN.NEXTVAL FROM DUAL")
        seq_user_gen_val = cur.fetchone()[0]
        user_gen_data = [user_input_info['U_CHEMBL_ID']] + [f"UNEW_MOLECULE{seq_user_gen_val}"]
        try:
            torch.manual_seed(torch.randint(0, 1000000, (1,)).item())
            user_gen_data += make_smiles(user_input_info['U_CANOSMILES'])
            user_generate_molecule_result.append(user_gen_data)
            unew_names.append(f"UNEW_MOLECULE{seq_user_gen_val}")
        except:
            print('에러 발생')
            continue

    for user_gen_row in user_generate_molecule_result:
        try:
            pki = list(predict_pKi(user_gen_row[2]))
            pkd = list(predict_pKd(user_gen_row[2]))
            toxic = [toxic_predict(user_gen_row[2])]
            user_gen_data2 = user_gen_row + pki + pkd + toxic

            user_gen_dic = dict(zip(user_gen_col, user_gen_data2))

            columns = ', '.join(user_gen_col)
            placeholders = ', '.join([f':{k}' for k in user_gen_col])

            insert_user_gen_sql = f"INSERT INTO USER_GENERATIVE ({columns}) VALUES ({placeholders})"
            
            cur.execute(insert_user_gen_sql, user_gen_dic)
            print('삽입 완료')
        except:
            unew_names.remove(user_gen_row[1])
            print('데이터 삽입 실패')
            continue
            
    conn.commit()
    
    user_input_info['unew_names'] = unew_names
    
    with open("user_gen_result.json", "w", encoding="utf-8") as f:
        json.dump(user_input_info, f, ensure_ascii=False, indent=2)
    
    return {'user_generative_result': user_input_info}

@app.post("/button_diy") 
async def predict(request: Request):
    cur.execute("TRUNCATE TABLE DISEASE_GENERATIVE") 
    user_selected_button = '암 치료제' # 입력 : 누른 버튼 이름 
    
    sql = f"SELECT D_CHEMBL_ID, D_CANOSMILES, D_CATEGORY FROM disease_input where d_category = '{user_selected_button}'"
    sql_res = pd.read_sql(sql, conn)
    randoms = [0,1]
    orig_molecule = sql_res.iloc[randoms].to_dict(orient='records') # 카테고리별 smiles 2개 관련 정보

    sql2 = "SELECT * FROM DISEASE_GENERATIVE where rownum <= 1"
    sql2_res = pd.read_sql(sql2, conn)
    disease_generative_col = list(sql2_res.columns)

    generate_molecule_result = []

    for i in orig_molecule:
        dnew_names = []
        for j in range(5):
            cur.execute("SELECT SEQ_DISEASE_GEN.NEXTVAL FROM DUAL")
            seq_val = cur.fetchone()[0]
            res = [i['D_CHEMBL_ID']] + [f"DNEW_MOLECULE{seq_val}"]
            
            try:
                torch.manual_seed(torch.randint(0, 1000000, (1,)).item())
                res += make_smiles(i['D_CANOSMILES'])
                generate_molecule_result.append(res)
                dnew_names.append(f"DNEW_MOLECULE{seq_val}")
            except:
                print('에러 발생')
                continue

        for res in generate_molecule_result:
            try:
                pki = list(predict_pKi(res[2]))
                pkd = list(predict_pKd(res[2]))
                toxic = [toxic_predict(res[2])]
                res2 = res + pki + pkd + toxic + [user_selected_button]
                dic = dict(zip(disease_generative_col, res2))

                columns = ', '.join(dic.keys())
                placeholders = ', '.join([f':{k}' for k in dic.keys()])

                sql = f"INSERT INTO DISEASE_GENERATIVE ({columns}) VALUES ({placeholders})"
                cur.execute(sql, dic)
                print('삽입 성공')
            except:
                print('데이터 에러 발생')
                continue
        conn.commit()
    
        i['dnew_name'] = dnew_names

    with open("button_gen_result.json", "w", encoding="utf-8") as f:
        json.dump(orig_molecule, f, ensure_ascii=False, indent=2)
    
    return {'button_generative_result': orig_molecule}

@app.post("/user_diy_show")
async def predict(request: Request):
    # user_gen_result.json 형태 그대로 받아와서 진행 예정
    # (위의 /user_diy의 return 값을 그대로 가져오는 거 가능하실까여)
    with open('user_gen_result.json', 'r', encoding='utf-8') as f:
    # json.load() 함수를 사용하여 파일 내용을 딕셔너리로 변환합니다.
        user_gen_result = json.load(f)
    # 'U_CHEMBL_ID', 'U_NAME', 'U_CANOSMILES', 'U_FORMULA', 'U_TYPE', 'U_IMAGE_BASE64' 
    # 이건 원조 분자용 데이터

    new_moluecule_names = user_gen_result['unew_names']
    unew_names_in_sql = ','.join(["'" + i + "'" for i in new_moluecule_names])

    find_user_gen_mol_info = f'select * from user_generative where unew_name in ({unew_names_in_sql})'
    user_gen_info = pd.read_sql(find_user_gen_mol_info, conn)
    # 이건 새로 생성한 분자 데이터(5개 들어있어여)
    user_gen_info['UNEW_IMAGE_BASE64'] = user_gen_info['UNEW_IMAGE_BASE64'].apply(lambda x: x.read() if hasattr(x, 'read') else x)

    user_gen_info = user_gen_info.to_dict(orient='records')

    with open("user_diy_show.json", "w", encoding="utf-8") as f:
        json.dump(user_gen_info, f, ensure_ascii=False, indent=2)
    
    return {'show_new_user_mol':user_gen_info}
        
@app.post("/button_diy_show")
async def predict(request: Request):
    # button_gen_result.json 형태 그대로 받아와서 진행 예정 
    # (위의 /button_diy의 return 값을 그대로 가져오는 거 가능하실까여)
    with open('button_gen_result.json', 'r', encoding='utf-8') as f:
    # json.load() 함수를 사용하여 파일 내용을 딕셔너리로 변환합니다.
        btn_gen_result = json.load(f)
        # 이건 원조 분자용 데이터

    user_click = 0 # 유저가 클릭한 분자

    if user_click == 0: # 0말고 원조 분자 id를 받아와야 할듯
        use_data = btn_gen_result[0] # 첫번째를 누르면 첫번째 원소 불러옴
    else:
        use_data = btn_gen_result[1] # 밑에 누르면 두 번째 원소 불러옴
        
    orig_mol_info_sql = f"select * from disease_input where D_CHEMBL_ID = '{use_data['D_CHEMBL_ID']}'"
    orig_mol_info = pd.read_sql(orig_mol_info_sql, conn).to_dict(orient='records')
    # 원조 분자 정보

    btn_gen_mol_info_cond = ','.join(["'" + i + "'" for i in use_data['dnew_name']])
    btn_gen_mol_info_sql = f'select * from disease_generative where dnew_name in ({btn_gen_mol_info_cond})'
    btn_gen_info = pd.read_sql(btn_gen_mol_info_sql, conn)
    btn_gen_info['DNEW_IMAGE_BASE64'] = btn_gen_info['DNEW_IMAGE_BASE64'].apply(lambda x: x.read() if hasattr(x, 'read') else x)
    btn_gen_info = btn_gen_info.to_dict(orient='records')
    # btn_gen_info : 새로 만들어진 분자 정보
    
    with open("button_diy_show.json", "w", encoding="utf-8") as f:
        json.dump(btn_gen_info, f, ensure_ascii=False, indent=2)
    
    return {'button_diy_show':btn_gen_info}
    