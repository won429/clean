import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib3
import re  # ✨ 추가된 도구: 숨겨진 글 번호를 찾아내는 탐지기 역할

# 보안 인증서 경고 무시 (공공기관 사이트 접속 시 필수)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_kknu_notices():
    print("🚀 국립경국대학교 공지사항 정밀 수집 시작...")
    
    # 1. 실제 국립경국대학교 학사안내 게시판 진짜 주소
    url = "https://www.gknu.ac.kr/main/board/index.do?menu_idx=68&manage_idx=1&search.category1=102"
    base_url = "https://www.gknu.ac.kr"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124'
    }
    
    notice_list = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 실제 경국대 게시판 테이블(tr) 찾기
        rows = soup.select('table tbody tr')
        
        for row in rows:
            if len(notice_list) >= 15: # 최신 글 15개까지만
                break
                
            tds = row.select('td')
            if len(tds) < 4:
                continue
                
            # ✨ 핵심 1: a 태그가 여러 개일 때 '텍스트가 가장 긴 것'이 무조건 진짜 제목!
            a_tags = row.select('a')
            if not a_tags:
                continue
                
            valid_a = max(a_tags, key=lambda x: len(x.get_text(strip=True)))
            title = valid_a.get_text(strip=True)
            
            # 지저분한 말머리 텍스트 깔끔하게 제거
            title = re.sub(r'^\[.*?\]\s*', '', title)
            
            href = valid_a.get('href', '')
            
            # ✨ 핵심 2: 링크가 javascript로 숨겨져 있을 경우 진짜 주소로 강제 조립!
            if 'javascript' in href.lower():
                # 숫자(게시글 번호)만 쏙 뽑아냅니다.
                numbers = re.findall(r"['\"]?(\d+)['\"]?", href)
                if numbers:
                    board_idx = numbers[0]
                    # 실제 게시글을 바로 볼 수 있는 주소로 완벽 조립
                    link = f"https://www.gknu.ac.kr/main/board/view.do?menu_idx=68&manage_idx=1&board_idx={board_idx}"
                else:
                    link = url
            elif href.startswith('?'):
                link = "https://www.gknu.ac.kr/main/board/view.do" + href
            elif href.startswith('/'):
                link = base_url + href
            else:
                link = href
            
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
                if category.isnumeric(): category = "일반" # 단순 번호 방어
                
            # 오늘 올라온 글인지 확인
            today = datetime.now().strftime("%Y.%m.%d")
            is_hot = (date_str == today)
            
            # ✨ 핵심 3: 본문 내용까지 긁어오기 위해 해당 링크로 한 번 더 접속!
            content_text = ""
            try:
                # 본문 페이지 접속
                detail_resp = requests.get(link, headers=headers, timeout=5, verify=False)
                detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                
                # 게시판 본문 영역을 찾는 범용적인 클래스 이름들 탐색
                content_area = detail_soup.select_one('.board_view, .view_con, .content, .board-contents, .b-content-box, td.content, .ui-board-view')
                if content_area:
                    # 엔터(줄바꿈)를 유지하면서 텍스트만 깔끔하게 추출
                    content_text = content_area.get_text(separator='\n', strip=True)
                    
                    # 내용이 너무 길면 앱이 무거워지므로 1000자에서 자르기
                    if len(content_text) > 1000:
                        content_text = content_text[:1000] + "\n\n... (원문에서 계속)"
            except Exception as e:
                print(f"본문 긁어오기 실패 ({link}): {e}")
            
            notice_list.append({
                "id": len(notice_list) + 1,
                "school": "국립경국대",
                "category": category,
                "title": title,
                "timeAgo": date_str,
                "link": link,
                "isHot": is_hot,
                "dDay": None,
                "content": content_text # ✨ 드디어 본문 데이터 추가!
            })
            
    except Exception as e:
        print(f"❌ 데이터 수집 중 에러 발생: {e}")
        notice_list.append({
            "id": 1,
            "school": "시스템",
            "category": "오류",
            "title": f"접속 지연: {str(e)[:30]}",
            "timeAgo": datetime.now().strftime("%Y.%m.%d"),
            "link": "#",
            "isHot": True,
            "dDay": "점검중"
        })

    finally:
        with open('notices.json', 'w', encoding='utf-8') as f:
            json.dump(notice_list, f, ensure_ascii=False, indent=2)
        print(f"✅ 'notices.json' 파일 정밀 수집 및 저장 완료! (총 {len(notice_list)}개)")

if __name__ == "__main__":
    get_kknu_notices()