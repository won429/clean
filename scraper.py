import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def get_kknu_notices():
    print("🚀 국립경국대학교 공지사항 수집 시작...")
    
    # 1. 수집할 학교 게시판 주소 (실제 국립경국대 도메인 반영)
    # ※ 주의: 실제 공지사항 목록이 있는 정확한 세부 게시판 URL로 맞춰주세요.
    url = "https://www.gknu.ac.kr/board/notice" # 예시: 실제 공지사항 게시판 URL
    base_url = "https://www.gknu.ac.kr"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 실제 게시판 구조에 맞춘 선택자 (사이트 개편 시 수정 필요)
        # ※ 참고: 현재 경국대 홈페이지 HTML 구조를 가정한 범용 선택자입니다.
        rows = soup.select('table tbody tr:not(.notice, .top)') # 상단 고정공지 제외한 일반 글
        
        notice_list = []
        
        for idx, row in enumerate(rows[:10]): # 최신 글 10개만 가져오기
            title_elem = row.select_one('td.subject a, td.title a, a') # a 태그를 유연하게 찾도록 수정
            date_elem = row.select_one('td.date, td:nth-last-child(2)') # 날짜가 들어가는 전형적인 위치
            dept_elem = row.select_one('td.writer, td:nth-child(3)') # 담당 부서 또는 작성자
            
            if title_elem and date_elem:
                title = title_elem.get_text(strip=True)
                
                # 링크 경로가 절대/상대 경로인지 판단하여 조립
                href = title_elem['href']
                link = href if href.startswith('http') else base_url + href
                
                date_str = date_elem.get_text(strip=True)
                dept = dept_elem.get_text(strip=True) if dept_elem else "일반"
                
                # 담당 부서 이름을 기준으로 카테고리 자동 분류 로직
                category = "일반"
                if "학사" in dept or "교무" in dept: category = "학사"
                elif "장학" in title or "학생" in dept: category = "장학"
                elif "취업" in dept or "진로" in title: category = "취업"
                
                # 오늘 날짜와 비교하여 HOT(새글) 여부 판단
                today = datetime.now().strftime("%Y-%m-%d")
                is_hot = (date_str == today)
                
                # 앱에 들어갈 데이터 형식으로 맞춤 조립
                notice_list.append({
                    "id": idx + 1,
                    "school": "경국대(안동)",
                    "category": category,
                    "title": title,
                    "timeAgo": date_str, # 원래는 '10분 전' 등으로 계산해야 하지만 우선 날짜로 표기
                    "link": link,
                    "isHot": is_hot,
                    "dDay": None # 본문 분석이 필요하므로 기본값 Null
                })
                
        # 2. 수집된 데이터를 JSON 파일로 저장 (앱에서 쓰기 좋게)
        with open('notices.json', 'w', encoding='utf-8') as f:
            json.dump(notice_list, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 총 {len(notice_list)}개의 공지사항 수집 완료! 'notices.json' 파일이 생성되었습니다.")
        
    except Exception as e:
        print(f"❌ 데이터 수집 중 오류 발생: {e}")

# 실행
if __name__ == "__main__":
    get_kknu_notices()