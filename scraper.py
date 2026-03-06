import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib3
import re

# 보안 인증서 경고 무시 (공공기관 사이트 접속 시 필수)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_kknu_notices():
    print("🚀 국립경국대학교 공지사항 정밀 수집 (본문 강화 버전) 시작...")
    
    url = "https://www.gknu.ac.kr/main/board/index.do?menu_idx=68&manage_idx=1&search.category1=102"
    base_url = "https://www.gknu.ac.kr"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0'
    }
    
    notice_list = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table tbody tr')
        
        for row in rows:
            if len(notice_list) >= 15: # 최신 글 15개까지만
                break
                
            tds = row.select('td')
            if len(tds) < 4: continue
                
            a_tags = row.select('a')
            if not a_tags: continue
                
            valid_a = max(a_tags, key=lambda x: len(x.get_text(strip=True)))
            title = valid_a.get_text(strip=True)
            title = re.sub(r'^\[.*?\]\s*', '', title)
            href = valid_a.get('href', '')
            
            if 'javascript' in href.lower():
                numbers = re.findall(r"['\"]?(\d+)['\"]?", href)
                if numbers:
                    board_idx = numbers[0]
                    link = f"https://www.gknu.ac.kr/main/board/view.do?menu_idx=68&manage_idx=1&board_idx={board_idx}"
                else: link = url
            elif href.startswith('?'): link = "https://www.gknu.ac.kr/main/board/view.do" + href
            elif href.startswith('/'): link = base_url + href
            else: link = href
            
            date_str = ""
            for td in tds:
                txt = td.get_text(strip=True)
                if len(txt) == 10 and (txt.count('-') == 2 or txt.count('.') == 2):
                    date_str = txt.replace('-', '.')
                    break
            if not date_str and len(tds) >= 5:
                date_str = tds[4].get_text(strip=True).replace('-', '.')
                
            category = "학사"
            if len(tds) >= 2 and len(tds[1].get_text(strip=True)) <= 10:
                category = tds[1].get_text(strip=True)
                if "공지" in category or category.isnumeric(): category = "일반"
                
            today = datetime.now().strftime("%Y.%m.%d")
            is_hot = (date_str == today)
            
            # ✨ 핵심: 본문 추출 초강력 투망 던지기
            content_text = ""
            try:
                detail_resp = requests.get(link, headers=headers, timeout=5, verify=False)
                detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                
                # 학교 홈페이지들이 본문을 숨겨두는 거의 모든 클래스명 총동원
                selectors = [
                    '.b-content-box', '.b-txt', '.board-contents', '.board_txt', 
                    '.board_view_con', '.view_con', '.article_view', '.content', 
                    '.view_body', '.board_body', '.board_content', 'td.content', 
                    '.ui-board-view', '#board_content', '.view-content'
                ]
                
                content_area = None
                for selector in selectors:
                    content_area = detail_soup.select_one(selector)
                    # 찾은 박스 안에 진짜 글씨가 들어있는지 확인 (20자 이상)
                    if content_area and len(content_area.get_text(strip=True)) > 20:
                        break # 진짜 본문을 찾았으면 탐색 중단!
                        
                if content_area:
                    # 불필요한 스크립트나 스타일(코드 찌꺼기) 제거
                    for script in content_area(["script", "style"]):
                        script.extract()
                    
                    # 텍스트 추출 시 문단 구분이 되도록 줄바꿈 깔끔하게 처리
                    lines = [line.strip() for line in content_area.get_text(separator='\n').splitlines() if line.strip()]
                    content_text = '\n\n'.join(lines)
                    
                    if len(content_text) > 1000:
                        content_text = content_text[:1000] + "\n\n... (원문에서 계속)"
                else:
                    content_text = "표나 이미지만으로 작성된 게시글이거나, 특수 보안 구조로 되어 있습니다.\n하단의 [원문 및 첨부파일 보기] 버튼을 눌러 확인해 주세요."
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
                "content": content_text
            })
            
    except Exception as e:
        print(f"❌ 데이터 수집 중 에러 발생: {e}")
        notice_list.append({
            "id": 1, "school": "시스템", "category": "오류", 
            "title": f"접속 지연: {str(e)[:30]}", 
            "timeAgo": datetime.now().strftime("%Y.%m.%d"), 
            "link": "#", "isHot": True, "dDay": "점검중", "content": ""
        })

    finally:
        with open('notices.json', 'w', encoding='utf-8') as f:
            json.dump(notice_list, f, ensure_ascii=False, indent=2)
        print(f"✅ 'notices.json' 파일 정밀 수집(본문 포함) 완료! (총 {len(notice_list)}개)")

if __name__ == "__main__":
    get_kknu_notices()
