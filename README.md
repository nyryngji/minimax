## **:seedling: 프로젝트 멤버**
|:triangular_flag_on_post: 권민정|배수한|김하늘|김정민|
|-----|----|----|-----|
|<a href="https://github.com/nyryngii"><img src="https://img.shields.io/badge/nyryngii-181717?style=flat-square&logo=GitHub&logoColor=white" height="24px"/></a><br>분자생성모델, 독성예측모델</br>|<a href="https://github.com/uh004"><img src="https://img.shields.io/badge/uh004-181717?style=flat-square&logo=GitHub&logoColor=white" height="24px"/></a><br>약의 효능을 예측하는 모델</br>|<a href="https://github.com/vskyv1101"><img src="https://img.shields.io/badge/vskyv1101-181717?style=flat-square&logo=GitHub&logoColor=white" height="24px"/></a><br>AI을 활용한 유효물질 최적화</br>|<a href="https://github.com/zzangmin2"><img src="https://img.shields.io/badge/zzangmin2-181717?style=flat-square&logo=GitHub&logoColor=white" height="24px"/></a><br>사용자들이 사용하기 쉽도록 인터페이스 구성</br>|

#### 1. 가상환경 생성 

```bash
python -m .venv venv
cd D:\minimax\.venv\Scripts
.\activate
cd D:\minimax\minimax_backend
pip install -r requirements.txt
```

#### 2. DB 연결 : Oracle SQL Developer Extension for VSCode 설치
- 안에 DB 보고 싶으면 설치

#### 3. 웹서버 시작하기
```bash
uvicorn main:app --reload
```
#### 4. http://127.0.0.1:8000/docs로 들어가기 
- AI 모델 때문에 들어가는데 시간 좀 걸림
