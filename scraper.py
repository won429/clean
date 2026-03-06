import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib3
import re

# 보안 인증서 경고 무시 (공공기관 사이트 접속 시 필수)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_kknu_notices():
    print("🚀 국립경국대학교 공지사항 초강력 정밀 수집 시작...")
    
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
            
            # ✨ 100% 무조건 쓸어 담는 본문 추출기
            content_text = ""
            img_count = 0
            try:
                detail_resp = requests.get(link, headers=headers, timeout=5, verify=False)
                detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                
                content_area = None
                
                # 1. 전국 대학 게시판 클래스명 싹 다 털기
                selectors = [
                    '.board_view_con', '.b-content-box', '.board_txt', '.view_con', '.article_view', 
                    '.board-contents', '.content', '.view_body', '.board_body', '.board_content', 
                    'td.content', '.ui-board-view', '#board_content', '.view-content',
                    '.board_view_content', '.board-view-content', '.b-con-box', '.board_con',
                    '.boardView', '.view_area', '.b_content', '.post-content', '.view_info', '.dbData',
                    '.board_view', '.bbs_view', '.v_con', '.board_article', 'td.con', '.con_txt', 
                    '#bo_v_con', '.board_view_area', '.fr-view'
                ]
                
                for selector in selectors:
                    elements = detail_soup.select(selector)
                    for el in elements:
                        # 통째로 잡힌 껍데기 무시
                        if el.find(['header', 'footer']): continue
                        
                        text_length = len(el.get_text(strip=True))
                        img_count = len(el.select('img'))
                        if text_length > 10 or img_count > 0:
                            content_area = el
                            break
                    if content_area: break
                        
                # 2. ✨ 핵심 해결책! 위에서 못 찾았으면 방해 조건 없이 무식하게 텍스트 제일 많은 놈 잡아채기!
                if not content_area:
                    # 방해되는 껍데기(메뉴, 꼬리말, 스크립트 등) 전부 파괴
                    for trash in detail_soup(['header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript']):
                        trash.extract()
                        
                    candidates = detail_soup.find_all(['div', 'td', 'article', 'section'])
                    best_block = None
                    max_len = 0
                    
                    for block in candidates:
                        # 링크(a)가 너무 많은 블록(메뉴판, 게시판 목록)은 본문에서 제외!
                        a_text_len = sum(len(a.get_text(strip=True)) for a in block.find_all('a'))
                        total_text_len = len(block.get_text(strip=True))
                        
                        if total_text_len > 0 and (a_text_len / total_text_len) > 0.4:
                            continue
                            
                        # 남은 덩어리 중 가장 텍스트가 많은 것을 본문으로 채택! (기존의 방해 조건 완전 삭제)
                        if total_text_len > max_len:
                            max_len = total_text_len
                            best_block = block
                            
                    if best_block and max_len > 10:
                        content_area = best_block
                        img_count = len(content_area.select('img'))
                        
                # 3. 텍스트 예쁘게 다듬기
                if content_area:
                    for script in content_area(["script", "style"]):
                        script.extract()
                    
                    lines = [line.strip() for line in content_area.get_text(separator='\n').splitlines() if line.strip()]
                    content_text = '\n\n'.join(lines)
                    
                    if len(content_text) < 5 and img_count > 0:
                        content_text = "🖼️ [텍스트 없이 포스터/이미지로만 안내된 공지사항입니다]\n\n상세 이미지는 하단의 '웹사이트에서 원문 보기' 버튼을 눌러 확인해 주세요."
                    elif len(content_text) > 1000:
                        content_text = content_text[:1000] + "\n\n... (원문에서 계속)"
                else:
                    content_text = "🔒 특수 구조로 된 게시글입니다.\n\n하단의 [원문 및 첨부파일 보기] 버튼을 눌러 학교 홈페이지에서 직접 확인해 주세요."
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
        print(f"✅ 'notices.json' 파일 정밀 수집 완료! (총 {len(notice_list)}개)")

if __name__ == "__main__":
    get_kknu_notices()