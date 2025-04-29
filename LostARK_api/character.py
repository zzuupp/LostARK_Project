# 필요한 라이브러리 및 모듈 등등 업로드.
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests

#인코딩 관련. 
from urllib.parse import quote

import re
import time
from tqdm import tqdm
from datetime import datetime

import json
import sys
import os

# 1. 기본정보 : 캐릭터마다 가지고 있는 모든 정보를 확인하는 함수(장비/악세/스톤/팔찌)
# ------------------------------------------------------------------------------------------------------------
def user_character_equipment(character_name, api_key):

    """
    유저의 캐릭터가 착용한 장비를 확인하는 함수
    JSON 데이터를 그대로 리턴합니다.
    """
    # 퍼센트 인코딩
    character_name_encoded = quote(character_name)

    #url
    url = f'https://developer-lostark.game.onstove.com/armories/characters/{character_name_encoded}/equipment'


    # 인증, 응답 등의 관련 정보
    headers = {
        'accept': 'application/json',
        'authorization': f'bearer {api_key}'}

    # 응답요청  get
    response = requests.get(url, headers=headers)

    try:
        data = response.json()
        return data  #  JSON 데이터를 그대로 리턴

    except requests.exceptions.JSONDecodeError:
        return {
            "error": "JSONDecodeError",
            "status_code": response.status_code,
            "raw_response": response.text  #  오류 응답도 리턴 형태로 반환
        }
        

# 2.  환경 제어함수 (태그 제거 및 줄바꿈 문자 변경 등등)
# ------------------------------------------------------------------------------------------------------------
# 태그 제거하는 함수
def clean_html(text):
    return re.sub(r"<[^>]*>", "", text)

# 줄바꿈 문자 변경 및 태그를 제거하는 함수
def clean_html_with_newlines(text):
    # 1. <br> → 줄바꿈 문자로 변경
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    # 2. 모든 HTML 태그 제거
    text = re.sub(r"<[^>]*>", "", text)
    return text.strip()


# 3.  장비 관련 정보를 출력하는 함수
# ------------------------------------------------------------------------------------------------------------
def edit_elixir_info(user_equ_dict):
    """
    Tooltip dict에서 엘릭서 효과(옵션1, 옵션2)만 추출하는 함수
    """
    candidates = ["Element_009", "Element_008", "Element_006", "Element_010"]
    effects = []

    for candidate in candidates:
        group = user_equ_dict.get(candidate)
        if not group:
            continue
        value = group.get("value")
        if not value or not isinstance(value, dict):
            continue   # ⭐️ 여기가 중요! value가 dict일 때만 진행!

        elem = value.get("Element_000")
        if not elem or not isinstance(elem, dict):
            continue

        content_dict = elem.get("contentStr")
        if not content_dict or not isinstance(content_dict, dict):
            continue

        for v in content_dict.values():
            raw = v.get("contentStr", "")
            text = clean_html(raw)
            match = re.search(r"([가-힣A-Za-z\s\(\)\[\]\/]+)\s*Lv\.\s*\d+", text)
            if match:
                found = match.group(0).strip()
                effects.append(found)
        if len(effects) >= 2:
            break

    elixir1 = effects[0] if len(effects) > 0 else None
    elixir2 = effects[1] if len(effects) > 1 else None
    return elixir1, elixir2



def edit_parse_all_weapon_armor(equipment_list):
    """
    장비 :(무기, 투구, 상의, 하의, 장갑, 어깨)에 관한 정보를 수집하는 함수.
    리스트안의 dict 가 담긴 형태로 반환
    equipment_list: user_character_equipment()의 리턴값(list of dict)

    """
    equ_Type_ls = ['무기', '투구', '상의', '하의', '장갑', '어깨']
    results = []

    for value in equipment_list:
        if value.get('Type') in equ_Type_ls:
            grade = value.get('Grade', '')
            tooltip_raw = value.get('Tooltip')
            if not tooltip_raw:
                results.append({
                    '장비이름': None,
                    '장비 타입': None,
                    '등급': None,
                    '레벨': None,
                    '품질': None,
                    '상급재련': None,
                    '초월': None,
                    '엘릭서 옵션1': None,
                    '엘릭서 옵션2': None
                    })
                continue

            user_equ_dict = json.loads(tooltip_raw)

            # 이름
            equ_name = clean_html(user_equ_dict.get("Element_000", {}).get("value", ""))

            # 무기 타입
            equ_type = clean_html(user_equ_dict.get("Element_001", {}).get("value", {}).get("leftStr0", ""))


            # 아이템 레벨
            equ_level = clean_html(
                user_equ_dict.get("Element_001", {}).get("value", {}).get("leftStr2", "")
            )

            # 품질
            equ_quality = user_equ_dict.get("Element_001", {}).get("value", {}).get("qualityValue", "")

            # 상급 재련
            equ_special = '상급 재련 없음'
            try:
                raw_text = user_equ_dict.get("Element_005", {}).get("value", "")
                if raw_text and "재련" in raw_text:
                    equ_special = clean_html(raw_text)
            except Exception:
                pass

            # 초월 정보
            equ_transcend = '초월 정보 없음'
            try:
                topStr_9 = (
                    user_equ_dict.get("Element_009", {})
                    .get("value", {})
                    .get("Element_000", {})
                    .get("topStr", "")
                )
                topStr_8 = (
                    user_equ_dict.get("Element_008", {})
                    .get("value", {})
                    .get("Element_000", {})
                    .get("topStr", "")
                )
                if "엘릭서" in topStr_9:
                    equ_transcend = clean_html(topStr_8)
                else:
                    equ_transcend = clean_html(topStr_9)
                if not equ_transcend:
                    equ_transcend = '초월 정보 없음'
            except Exception:
                pass



            # ---- 엘릭서 처리 ----
            # 1-1. 무기 장비인 경우(엘릭서 부여 못함)
            if equ_type == '무기':
                elixir1, elixir2 = "엘릭서 부여를 하지 못하는 부위", "엘릭서 부여를 하지 못하는 부위"

            else:
                elixir1, elixir2 = edit_elixir_info(user_equ_dict)



            # 결과 누적
            results.append({
                '장비이름': equ_name,
                '장비 타입' : equ_type,
                '등급': grade,
                '레벨': equ_level,
                '품질': equ_quality,
                '상급재련': equ_special,
                '초월': equ_transcend,
                '엘릭서 옵션1':elixir1,
                '엘릭서 옵션2':elixir2
            })
    return results



# 4. 악세서리(팔찌 제외) 정보를 뽑아내는 함수
# ------------------------------------------------------------------------------------------------------------
def parse_basic_stat(raw_html):

    """
    악세서리 : 기본 능력치(힘/민/지/체)를 가져오는 함수입니다.
    """
    basic_stat_lines = clean_html_with_newlines(raw_html).split("\n")
    add_lines = " ".join(basic_stat_lines)
    strength, dexterity, intelligence, vitality = '', '', '',''

    # 정규표현식으로 추출
    str_match = re.search(r'힘\s*\+(\d+)', add_lines)
    dex_match = re.search(r'민첩\s*\+(\d+)', add_lines)
    int_match = re.search(r'지능\s*\+(\d+)', add_lines)
    vit_match = re.search(r'체력\s*\+(\d+)', add_lines)

    # 각 매칭 결과가 있다면 그룹(숫자)만 추출
    if str_match:
        strength = str_match.group(1)
    if dex_match:
        dexterity = dex_match.group(1)
    if int_match:
        intelligence = int_match.group(1)
    if vit_match:
        vitality = vit_match.group(1)

    return strength, dexterity, intelligence, vitality


def parse_grant_options_lines(raw_html):
    """
    악세서리 : 부여 옵션 정보를 가져옵니다.
    숫자 또는 % 뒤에 한글이 올 경우 줄바꿈하여 분리
    """
    grant_random_opt = clean_html_with_newlines(raw_html)

    # 숫자/퍼센트 뒤에 한글 등장 → 줄바꿈 삽입
    split_opt = re.sub(r'(?<=[0-9%])(?=[가-힣])', '\n', grant_random_opt)

    # 줄 단위 정리
    stats_ls = [stats.strip() for stats in split_opt.split('\n') if stats.strip()]

    # 최대 3개로 고정
    return (stats_ls + [None, None, None])[:3]


def edit_acc_opt_info(equipment_list):
    """
    악세서리에 관한 종합적인 능력치를 추출하는 함수입니다.
    * 이 함수는 '팔찌'를 추출할 수 없으며 해당 장비는 다른 함수에서 추출합니다.
    """

    acc_Type_ls = ['목걸이', '귀걸이', '반지']
    results = []

    for value in equipment_list:
        if value.get('Type') in acc_Type_ls:
            acc_type = value.get('Type')
            try:
                user_acc_dict = json.loads(value['Tooltip'])
            except Exception as e:
                print(f"❗ 악세서리 Tooltip 파싱 에러: {e}")
                continue

            # ------ 1. 악세서리 기본 정보 ------
            accessory_name = clean_html(user_acc_dict.get("Element_000", {}).get("value", ""))
            accessory_info = clean_html(user_acc_dict.get("Element_001", {}).get("value", {}).get("leftStr0", ""))
            accessory_level = clean_html(user_acc_dict.get("Element_001", {}).get("value", {}).get("leftStr2", ""))
            accessory_quality = user_acc_dict.get("Element_001", {}).get("value", {}).get("qualityValue", "")
            accessory_special_Dealable = clean_html(user_acc_dict.get("Element_002", {}).get("value", ""))

            # ------ 2. 기본 능력치 (힘, 민첩, 지능, 체력) ------
            accessory_basic_effect = clean_html(
                user_acc_dict.get("Element_004", {}).get("value", {}).get("Element_001", "")
            )
            strength, dexterity, intelligence, vitality = parse_basic_stat(accessory_basic_effect)

            # ------ 3. 부여 옵션(연마 효과 등) ------
            element_005_value = user_acc_dict.get("Element_005", {}).get("value")
            if isinstance(element_005_value, dict):
                polishing_raw = element_005_value.get("Element_001", "")
                polishing_cleaned = clean_html(polishing_raw)
                option_01, option_02, option_03 = parse_grant_options_lines(polishing_cleaned)
            else:
                option_01, option_02, option_03 = None, None, None

            # ------ 4. 아크 패시브 포인트 ------
            element_007 = user_acc_dict.get("Element_007")
            element_006 = user_acc_dict.get("Element_006")

            passive_point = "정보 없음 (장기 미접속 유저)"
            if element_007 and isinstance(element_007.get("value"), dict):
                elem_value = element_007["value"].get("Element_001", "")
                if elem_value:
                    passive_point = clean_html(elem_value)
            elif element_006 and isinstance(element_006.get("value"), dict):
                elem_value = element_006["value"].get("Element_001", "")
                if elem_value:
                    passive_point = clean_html(elem_value)

            # ------ 결과 누적 ------
            results.append({
                '악세서리 타입': acc_type,
                '악세서리 이름': accessory_name,
                '악세서리 등급': accessory_info,
                '악세서리 티어': accessory_level,
                '악세서리 품질': accessory_quality,
                '악세서리 거래 가능 여부': accessory_special_Dealable,
                '힘': strength,
                '민첩': dexterity,
                '지능': intelligence,
                '체력': vitality,
                '부여 옵션 효과 1': option_01,
                '부여 옵션 효과 2': option_02,
                '부여 옵션 효과 3': option_03,
                '아크패시브 부여 포인트': passive_point
            })

    return results


# 5.  스톤 : 어빌리티 스톤에 관한 정보를 뽑아내는 함수
# ------------------------------------------------------------------------------------------------------------
def edit_stone_info(equipment_list):
    
    """
    스톤 정보를 추출합니다.
    특정 결과값이 없는 정보들이 존재합니다.(""처리)
    """
    
    results = []

    for value in equipment_list:
        if not isinstance(value, dict):
            continue
        if value.get('Type') != '어빌리티 스톤':
            continue

        try:
            user_stone_dict = json.loads(value['Tooltip'])
        except Exception as e:
            print(f"❗툴팁 파싱 에러: {e}")
            continue

        stone_name = clean_html(user_stone_dict.get("Element_000", {}).get("value", ""))
        stone_grade = clean_html(user_stone_dict.get("Element_001", {}).get("value", {}).get("leftStr0", ""))
        stone_tier = clean_html(user_stone_dict.get("Element_001", {}).get("value", {}).get("leftStr2", ""))
        stone_basic_effect = clean_html(user_stone_dict.get("Element_004", {}).get("value", {}).get("Element_001", ""))

        element_005 = user_stone_dict.get("Element_005", {})
        type_005 = element_005.get("type", "")
        value_005 = element_005.get("value", {})

        if type_005 == 'ItemPartBox':
            stone_bonus_effect = clean_html(value_005.get("Element_001", "연마 보너스 효과 없음"))
        else:
            stone_bonus_effect = "연마 보너스 효과 없음"

        engrave1, engrave2, engrave3, bonus = "", "", "", ""

        element_006_value = user_stone_dict.get("Element_006", {}).get("value", None)

        if element_006_value and isinstance(element_006_value, dict):
            engrave_content = element_006_value.get("Element_000", {}).get("contentStr", {})
            engrave1 = clean_html(engrave_content.get("Element_000", {}).get("contentStr", ""))
            engrave2 = clean_html(engrave_content.get("Element_001", {}).get("contentStr", ""))
            engrave3 = clean_html(engrave_content.get("Element_002", {}).get("contentStr", ""))
            bonus = clean_html(engrave_content.get("Element_003", {}).get("contentStr", ""))
        else:
            if type_005 == 'IndentStringGroup':
                engrave_dict = value_005.get("Element_000", {}).get("contentStr", {})
                engrave1 = clean_html(engrave_dict.get("Element_000", {}).get("contentStr", ""))
                engrave2 = clean_html(engrave_dict.get("Element_001", {}).get("contentStr", ""))
                engrave3 = clean_html(engrave_dict.get("Element_002", {}).get("contentStr", ""))

        results.append({
            '스톤 이름': stone_name,
            '스톤 등급': stone_grade,
            '스톤 티어': stone_tier,
            '스톤 기본 효과': stone_basic_effect,
            '스톤 연마 보너스 효과': stone_bonus_effect,
            '스톤 각인 효과 1': engrave1,
            '스톤 각인 효과 2': engrave2,
            '스톤 각인 효과 3': engrave3,
            '스톤 추가 보너스': bonus,
        })

    return results


# 6.  팔찌 : 팔찌 정보를 파싱하는 함수
# ------------------------------------------------------------------------------------------------------------
def edit_parse_bracelet_stats(equipment_list):

    """
    팔찌 데이터를 안전하게 파싱해서 dict 리스트로 반환합니다.
    """

    results = []

    for value in equipment_list:
        if not isinstance(value, dict):
            continue
        if value.get('Type') != '팔찌':
            continue

        try:
            raw_html = json.loads(value['Tooltip'])
        except Exception as e:
            print(f"❗ 팔찌 Tooltip 파싱 에러: {e}")
            continue

        bracelet_name = clean_html(raw_html.get("Element_000", {}).get("value", ""))
        bracelet_info = clean_html(raw_html.get("Element_001", {}).get("value", {}).get("leftStr0", ""))
        bracelet_tier = clean_html(raw_html.get("Element_001", {}).get("value", {}).get("leftStr2", ""))

        # 팔찌 효과
        bracelet_effects = raw_html.get("Element_004", {}).get("value", {}).get("Element_001", "")
        split_effects = re.split(r"<img[^>]*>", bracelet_effects)

        effect_ls = []
        for effect in split_effects:
            cleaned = clean_html_with_newlines(effect).strip().replace("\n", " ")
            if cleaned:
                effect_ls.append(cleaned)

        option_01, option_02, option_03, option_04, option_05 = (effect_ls + ["", "", "", "", ""])[:5]

        # 아크 패시브 포인트
        bracelet_ark_point = "정보 없음 (장기 미접속 유저)"
        element_007 = raw_html.get("Element_007")
        if element_007 and isinstance(element_007.get("value"), dict):
            bracelet_ark_point = clean_html(element_007["value"].get("Element_001", ""))

        results.append({
            '팔찌 이름': bracelet_name,
            '팔찌 정보': bracelet_info,
            '팔찌 티어': bracelet_tier,
            '팔찌 옵션 1': option_01,
            '팔찌 옵션 2': option_02,
            '팔찌 옵션 3': option_03,
            '팔찌 옵션 4': option_04,
            '팔찌 옵션 5': option_05,
            '팔찌 아크패시브 포인트': bracelet_ark_point,
        })

    return results



# 7.  종합함수 : 위에서 정의한 모든내용을 출력 및 df로 변환하는 함수
# ------------------------------------------------------------------------------------------------------------
def edit_player_character_equipment(character, api_key, day):

    """
    캐릭터 플레이어의 장비값을 추출해내는 함수
    플레이어가 착용한 장비에 대한 모든 정보를 가져옵니다.
    이 때, 보석등의 정보는 제외됩니다.
    *  존재하지 않는 캐릭터는 fail_character_ls에 저장
    *  day값은 '2025-04-25'와 같은 형식이어야 합니다.
    """

    fail_character_ls = []

    # 날짜 형식 체크
    try:
        datetime.strptime(day, '%Y-%m-%d')
    except ValueError:
        raise ValueError("날짜 형식이 올바르지 않습니다. 'YYYY-MM-DD' 형식으로 입력해주세요.")

    # user 정보 조회
    user = user_character_equipment(character, api_key)
    
    # 기본 빈 DataFrame 준비
    equip_df = pd.DataFrame()
    acc_df = pd.DataFrame()
    stone_df = pd.DataFrame()

    # user가 None이면 실패 리스트에만 추가하고 데이터프레임은 빈 상태 유지
    if user is None:
        fail_character_ls.append(character)
    else:
        # 정상 케이스만 파싱
        all_weapon_armor_info = edit_parse_all_weapon_armor(user)
        equip_df = pd.DataFrame(all_weapon_armor_info)
        equip_df['캐릭터 이름'] = character
        equip_df['확인 일자'] = day

        all_acc_info = edit_acc_opt_info(user)
        acc_df = pd.DataFrame(all_acc_info)
        acc_df['캐릭터 이름'] = character
        acc_df['확인 일자'] = day

        all_stone_info = edit_stone_info(user)
        stone_df = pd.DataFrame(all_stone_info)
        stone_df['캐릭터 이름'] = character
        stone_df['확인 일자'] = day


        all_bracelet_stats = edit_parse_bracelet_stats(user)
        bracelet_df = pd.DataFrame(all_bracelet_stats)
        bracelet_df['캐릭터 이름'] = character
        bracelet_df['확인 일자'] = day

    return equip_df, acc_df, stone_df, bracelet_df, fail_character_ls


# 8. 캐릭터의 모든 정보 수집 : 일정 범위의 모든 캐릭터를 한번에 수집할 수 있는 함수입니다.
# ------------------------------------------------------------------------------------------------------------
def bulk_edit_player_equipment(characters, api_keys, day, save_every=2000):
    """
    characters : 유저 리스트
    api_keys : 사용할 API 키 리스트
    day : 조회할 날짜 (예시 '2025-04-25')
    save_every : 몇 명마다 중간 저장할지 (기본 2000)
    """

    final_equip_df = pd.DataFrame()
    final_acc_df = pd.DataFrame()
    final_stone_df = pd.DataFrame()
    final_bracelet_df = pd.DataFrame()
    total_fail_ls = []

    num_keys = len(api_keys)
    now_time = lambda: time.time()
    last_used_time = [0] * num_keys  # 각 키별 마지막 사용 완료 시간
    save_counter = 0
    total_characters = len(characters)

    pbar = tqdm(total=total_characters, desc="[진행] Progress", unit="char")

    idx = 0  # 캐릭터 인덱스
    key_idx = 0  # 사용할 API 키 인덱스

    while idx < total_characters:
        api_key = api_keys[key_idx]

        elapsed = now_time() - last_used_time[key_idx]
        if elapsed < 61:
            wait_time = 61 - elapsed
            print(f"⌛ {key_idx+1}번 API 키 대기중 ({wait_time:.1f}초)...")
            time.sleep(wait_time)

        # 99개 혹은 남은 캐릭터 수 만큼만 처리
        end_idx = min(idx + 99, total_characters)
        batch_characters = characters[idx:end_idx]

        for character in batch_characters:
            try:
                equip_df, acc_df, stone_df, bracelet_df, fail_ls = edit_player_character_equipment(character, api_key, day)

                final_equip_df = pd.concat([final_equip_df, equip_df], ignore_index=True)
                final_acc_df = pd.concat([final_acc_df, acc_df], ignore_index=True)
                final_stone_df = pd.concat([final_stone_df, stone_df], ignore_index=True)
                final_bracelet_df = pd.concat([final_bracelet_df, bracelet_df], ignore_index=True)
                total_fail_ls.extend(fail_ls)

            except Exception as e:
                print(f"❗ 캐릭터 {character} 처리 실패: {e}")
                total_fail_ls.append(character)

            pbar.update(1)
            save_counter += 1

            if save_counter >= save_every:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                final_equip_df.to_csv(f"equip_backup_{timestamp}.csv", index=False)
                final_acc_df.to_csv(f"acc_backup_{timestamp}.csv", index=False)
                final_stone_df.to_csv(f"stone_backup_{timestamp}.csv", index=False)
                final_bracelet_df.to_csv(f"bracelet_backup_{timestamp}.csv", index=False)
                pd.DataFrame({'fail_character': total_fail_ls}).to_csv(f"fail_character_backup_{timestamp}.csv", index=False)
                print(f"[저장 단계] {save_counter}명 저장 완료 (backup)")
                save_counter = 0

        # 현재 키 사용 완료 후 시간 기록
        last_used_time[key_idx] = now_time()

        # 다음 키로 순환
        idx = end_idx
        key_idx = (key_idx + 1) % num_keys

    pbar.close()

    return final_equip_df, final_acc_df, final_stone_df, final_bracelet_df, total_fail_ls
