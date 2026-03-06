import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib3

# 보안 인증서 경고 무시 (공공기관 사이트 접속 시 필수)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_kknu_notices():
    print("🚀 국립경국대학교 공지사항 수집 시작...")
    
    # 1. 실제 국립경국대학교 학사안내 게시판 진짜 주소
    url = "https://www.gknu.ac.kr/main/board/index.do?menu_idx=68&manage_idx=1&search.category1=102"
    base_url = "https://www.gknu.ac.kr"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124'
    }
    
    notice_list = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status() # 접속 실패 시 여기서 에러 발생
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 실제 경국대 게시판 테이블(tr) 찾기
        rows = soup.select('table tbody tr')
        
        for row in rows:
            if len(notice_list) >= 15: # 최신 글 15개까지만
                break
                
            tds = row.select('td')
            if len(tds) < 4:
                continue
                
            a_tag = row.select_one('a')
            if not a_tag:
                continue
                
            title = a_tag.get_text(strip=True)
            href = a_tag['href']
            link = href if href.startswith('http') else base_url + href
            
            # 날짜 추출 (YYYY.MM.DD 형태)
            date_str = ""
            for td in tds:
                txt = td.get_text(strip=True)
                if len(txt) == 10 and (txt.count('-') == 2 or txt.count('.') == 2):
                    date_str = txt.replace('-', '.')
                    break
            if not date_str and len(tds) >= 5:
                date_str = tds[4].get_text(strip=True).replace('-', '.')
                
            # 카테고리 추출
            category = "학사"
            if len(tds) >= 2 and len(tds[1].get_text(strip=True)) <= 10:
                category = tds[1].get_text(strip=True)
                if "공지" in category: category = "일반"
                
            # 오늘 올라온 글인지 확인
            today = datetime.now().strftime("%Y.%m.%d")
            is_hot = (date_str == today)
            
            notice_list.append({
                "id": len(notice_list) + 1,
                "school": "국립경국대",
                "category": category,
                "title": title,
                "timeAgo": date_str,
                "link": link,
                "isHot": is_hot,
                "dDay": None
            })
            
    except Exception as e:
        print(f"❌ 데이터 수집 중 에러 발생: {e}")
        # 에러가 나도 앱이 멈추지 않게 긴급 메시지를 데이터로 만듭니다.
        notice_list.append({
            "id": 1,
            "school": "시스템",
            "category": "오류",
            "title": f"학교 서버 접속 지연 중입니다 ({str(e)[:30]})",
            "timeAgo": datetime.now().strftime("%Y.%m.%d"),
            "link": "#",
            "isHot": True,
            "dDay": "점검중"
        })

    finally:
        # ✨ 핵심 방어막: 에러가 나든 성공하든 무조건 json 파일을 생성합니다!
        with open('notices.json', 'w', encoding='utf-8') as f:
            json.dump(notice_list, f, ensure_ascii=False, indent=2)
        print(f"✅ 'notices.json' 파일 강제 저장 완료! (총 {len(notice_list)}개)")

if __name__ == "__main__":
    get_kknu_notices()