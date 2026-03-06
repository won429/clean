import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib3
import re

# 보안 인증서 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_kknu_notices():
    print("🚀 국립경국대학교 공지사항 초강력 정밀 수집 시작...")
    
    url = "https://www.gknu.ac.kr/main/board/index.do?menu_idx=68&manage_idx=1&search.category1=102"
    base_url = "https://www.gknu.ac.kr"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    notice_list = []
    
    # ✨ 핵심 1: 세션(Session) 열기! 
    # 학교 서버에게 '로봇'이 아니라 '일반 방문자'로 인식시키기 위해 쿠키와 방문 기록을 유지합니다.
    session = requests.Session()
    
    try:
        # 먼저 게시판 목록 페이지를 방문해서 서버와 인사(쿠키 발급)를 나눕니다.
        response = session.get(url, headers=headers, timeout=15, verify=False)
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
            
            # ✨ 핵심 2: 불필요한 파라미터(search.category1) 제거
            # 500 에러를 유발하던 찌꺼기 주소를 빼고, 오직 글 번호(board_idx)만 깔끔하게 보냅니다.
            if 'javascript' in href.lower() or 'fn' in href.lower():
                numbers = re.findall(r"\d+", href)
                if numbers:
                    board_idx = max(numbers, key=len)
                    link = f"https://www.gknu.ac.kr/main/board/view.do?menu_idx=68&manage_idx=1&board_idx={board_idx}"
                else: 
                    link = url
            elif href.startswith('?'): 
                link = "https://www.gknu.ac.kr/main/board/view.do" + href
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
            
            # 본문 추출
            content_text = ""
            img_count = 0
            try:
                # ✨ 핵심 3: Referer 추가! "나 아까 그 목록 페이지에서 넘어온 거야!" 라고 서버에 어필
                detail_headers = headers.copy()
                detail_headers['Referer'] = url
                
                # 일반 requests.get이 아닌 세션(session.get)을 이용해 본문 접속
                detail_resp = session.get(link, headers=detail_headers, timeout=10, verify=False)
                
                if detail_resp.status_code != 200:
                    content_text = f"🚫 학교 서버가 응답하지 않습니다 (에러코드: {detail_resp.status_code})."
                else:
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                    page_text = detail_soup.get_text()
                    
                    if "Internal Server Error" in page_text or ("에러 페이지" in page_text and "500" in page_text):
                        content_text = "🚫 학교 홈페이지 자체 오류가 발생한 글입니다."
                    else:
                        content_area = None
                        
                        selectors = [
                            '.board_view_con', '.b-content-box', '.board_txt', '.view_con', '.article_view', 
                            '.board-contents', '.content', '.view_body', '.board_body', '.board_content', 
                            'td.content', '.ui-board-view', '#board_content', '.view-content',
                            '.board_view_content', '.board-view-content', '.b-con-box', '.board_con',
                            '.boardView', '.view_area', '.b_content', '.post-content', '.view_info', '.dbData',
                            'div[class*="view"]', 'div[class*="content"]', 'td[class*="content"]'
                        ]
                        
                        for selector in selectors:
                            elements = detail_soup.select(selector)
                            for el in elements:
                                if el.find(['header', 'footer']): continue
                                text_length = len(el.get_text(strip=True))
                                img_count = len(el.select('img'))
                                if text_length > 10 or img_count > 0:
                                    content_area = el
                                    break
                            if content_area: break
                                
                        # ✨ 핵심 4: 최후의 수단, 페이지 몸통 전체에서 텍스트 강제 쥐어짜기!
                        if not content_area:
                            for trash in detail_soup(['header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript', 'form']):
                                trash.extract()
                                
                            body = detail_soup.find('body')
                            if body:
                                best_block = None
                                max_len = 0
                                
                                # 모든 껍데기(div, td, table, section 등) 스캔
                                for block in body.find_all(['div', 'td', 'article', 'section']):
                                    # 또 다른 큰 껍데기는 제외
                                    if len(block.find_all(['div', 'table'])) > 5: continue
                                        
                                    text_len = len(block.get_text(strip=True))
                                    if text_len > max_len:
                                        max_len = text_len
                                        best_block = block
                                        
                                if best_block and max_len > 10:
                                    content_area = best_block
                                    img_count = len(content_area.select('img'))
                                else:
                                    # 진짜 아무것도 없으면 그냥 전체 텍스트 싹쓸이
                                    content_area = body
                                    
                        # 텍스트 다듬기
                        if content_area:
                            for script in content_area(["script", "style"]):
                                script.extract()
                            
                            # 표(Table)나 문단의 줄바꿈이 예쁘게 유지되도록 <br>을 엔터로 변환
                            for br in content_area.find_all("br"):
                                br.replace_with("\n")
                                
                            lines = [line.strip() for line in content_area.get_text(separator='\n').splitlines() if line.strip()]
                            content_text = '\n\n'.join(lines)
                            
                            if len(content_text) < 5 and img_count > 0:
                                content_text = "🖼️ [텍스트 없이 포스터/이미지로만 안내된 공지사항입니다]\n\n상세 이미지는 하단의 '웹사이트에서 원문 보기' 버튼을 눌러 확인해 주세요."
                            elif len(content_text) > 1500:
                                content_text = content_text[:1500] + "\n\n... (본문이 너무 길어 생략되었습니다. 하단 버튼을 눌러 원문을 확인하세요)"
                        else:
                            content_text = "🔒 게시글의 텍스트를 인식할 수 없습니다.\n\n하단의 [원문 및 첨부파일 보기] 버튼을 눌러 학교 홈페이지에서 직접 확인해 주세요."

            except Exception as e:
                print(f"본문 긁어오기 실패 ({link}): {e}")
                content_text = f"본문을 불러오는 중 통신 에러가 발생했습니다."
            
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