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
                    '.ui-board-view', '#board_content', '.view-content',
                    # ✨ 추가 투망: 경국대 및 기타 대학의 변태 클래스명 총집합
                    '.board_view_content', '.board-view-content', '.b-con-box', '.board_con',
                    '.boardView', '.view_area', '.b_content', '.post-content', '.view_info', '.dbData'
                ]
                
                content_area = None
                img_count = 0
                for selector in selectors:
                    element = detail_soup.select_one(selector)
                    if element:
                        text_length = len(element.get_text(strip=True))
                        img_count = len(element.select('img'))
                        
                        # ✨ 조건 완화: 글자가 5자 이상이거나, 사진이 1장이라도 들어있다면 "이게 본문이다!" 확정
                        if text_length > 5 or img_count > 0:
                            content_area = element
                            break # 진짜 본문을 찾았으면 탐색 중단!
                            
                # ✨ 궁극의 무기 (수학적 탐색): 만약 위 이름표를 다 피했다면, 글씨가 가장 빽빽하게 뭉쳐있는 곳을 강제로 찾아냅니다!
                if not content_area:
                    all_blocks = detail_soup.find_all(['div', 'td', 'p', 'span'])
                    best_block = None
                    max_len = 0
                    
                    for block in all_blocks:
                        block_text = block.get_text(strip=True)
                        # 홈페이지 껍데기(푸터, 상단메뉴 등) 제외
                        if "Copyright" in block_text or "개인정보" in block_text or "로그인" in block_text:
                            continue
                            
                        text_len = len(block_text)
                        # 다른 큰 박스들을 감싸고 있는 껍데기가 아니라, 진짜 글씨가 뭉쳐있는 알맹이 태그를 찾음
                        if text_len > max_len and len(block.find_all(['div', 'table'])) < 2:
                            max_len = text_len
                            best_block = block
                            
                    if best_block and max_len > 10:
                        content_area = best_block
                        img_count = len(content_area.select('img'))
                        
                if content_area:
                    # 불필요한 스크립트나 스타일(코드 찌꺼기) 제거
                    for script in content_area(["script", "style"]):
                        script.extract()
                    
                    # 텍스트 추출 시 문단 구분이 되도록 줄바꿈 깔끔하게 처리
                    lines = [line.strip() for line in content_area.get_text(separator='\n').splitlines() if line.strip()]
                    content_text = '\n\n'.join(lines)
                    
                    # ✨ 텍스트는 없고 사진만 있는 게시글 특별 처리!
                    if len(content_text) < 5 and img_count > 0:
                        content_text = "🖼️ [텍스트 없이 포스터/이미지로만 안내된 공지사항입니다]\n\n상세 이미지는 하단의 '웹사이트에서 원문 보기' 버튼을 눌러 확인해 주세요."
                    elif len(content_text) > 1000:
                        content_text = content_text[:1000] + "\n\n... (원문에서 계속)"
                else:
                    content_text = "🔒 표(Table)로만 작성되었거나 특수 구조로 된 게시글입니다.\n\n하단의 [원문 및 첨부파일 보기] 버튼을 눌러 학교 홈페이지에서 직접 확인해 주세요."
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