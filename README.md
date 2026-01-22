#### 💊MINIMAX : B2B를 대상으로 한 AI 기반 신약 후보 물질 발굴·최적화 플랫폼(2025.09.01 ~ 2025.11.17)

---

#### 1. 팀원 역할 분배

| 이름 | 역할 | 담당 업무 |
|------|------|------------|
| 권민정 | AI, 백엔드 |  분자 생성 AI,  독성 예측 AI, 유전 알고리즘, Backend |
| 김정민 | UI, 프론트엔드 | UI/UX 구현, FrontEnd |
| 배수한 | AI | pKi 모델 학습, 유전 알고리즘 |
| 김하늘 | AI | pKd 모델 학습, 유전 알고리즘 |
  
#### 2. Stack
- **AI** : Python, Transformer, HuggingFace
- **FrontEnd** : TypeScript, React
- **BackEnd** : FastAPI 
- **Database** : OracleDB 
- **etc** : Deechem, pubchempy, rdkit, chembl


#### 3. backend 실행
```bash
python -m .venv venv
cd D:\minimax\.venv\Scripts
.\activate
cd D:\minimax\minimax_backend
pip install -r requirements.txt
```
```bash
& D:/minimax/.venv/Scripts/Activate.ps1
uvicorn main:app --reload

# http://127.0.0.1:8000/docs 로 들어가기
```


#### 4. 서비스 구성도
<img width="600" height="300" alt="image" src="https://github.com/user-attachments/assets/b1a0199b-2cf5-42dc-a4bd-cfb398fd4b88" />

</details>

<br>

#### 5. 시연 영상

https://github.com/user-attachments/assets/d94ea1bf-a3f0-4c30-a0ba-5505a4775bf7

