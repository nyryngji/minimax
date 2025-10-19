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
& D:/minimax/.venv/Scripts/Activate.ps1
uvicorn main:app --reload
```
#### 4. http://127.0.0.1:8000/docs 로 들어가기 
- AI 모델 때문에 들어가는데 시간 좀 걸림

#### 5. 웹서버 기능
- /user_diy : 
  - 입력 : 사용자가 입력한 분자 이름 ex) Caffeine
  - 기능 : 사용자가 입력받은 분자를 기반으로 분자 생성까지 해서 DB에 집어넣음 
  - return : 사용자가 입력한 분자 정보
  - 출력 : "분자 생성 중" 메시지

- /user_diy_show : 
  - 입력 : 사용자가 입력한 분자 정보(/user_diy return 값) 
  - 기능 : 원조 분자 + 새로 생성된 분자 조회
  - return : 새로 생긴 분자 정보
  - 출력 : return 값과 동일하게 새로 생긴 분자 정보

- /button_diy : 
  - 입력 : 버튼 눌러서 db에 저장되어 있는 분자 불러오기 
  - 기능 : db에 저장되어 있는 분자 불러와서 분자 생성까지 해서 DB에 집어넣음
  - return : db에 저장되어 있는 분자 + 저장되어 있는 분자 기반의 새로 생성된 분자의 고유 name
  - 출력 : '분자 생성 중' 메시지
   
- /button_diy_show : 
  - 입력 : /button_diy 리턴 값 
  - 기능 : 원조 분자 + 새로 생성된 분자 조회
  - return : 새로 만들어진 분자 정보(이거 근데 없어도 될거 같은데)
  - 출력 : 원조 분자 + 새로 생성된 분자 정보 출력

- /optim_molecule : 
  - 입력 : 사용자가 클릭한 분자의 고유 name -> EX) DNEW_MOLECULE1, DNEW_MOLECULE1
  - 기능 : 선택한 분자를 기반으로 분자 최적화 수행 후 DB에 집어넣음
  - return : 가장 성능이 좋은 분자 smiles(분자 최적화 db에 0이라고 표시되어 있긴 함) + 사용자 입력('U') or 버튼 클릭('D')
  - 출력 : '분자 최적화 중' 메시지

- /optim_molecule_show : 
  - 입력 : optim_molecule의 사용자 입력('U') or 버튼 클릭('D') 값
  - 기능 : 새로 최적화된 분자와 원조 분자 사이에 얼마나 성능이 최적화되었는지 비교
  - return : 최적화된 분자 정보 + 원조 분자와의 차이값 
  - 출력 :  최적화 전후 비교 
 
  
