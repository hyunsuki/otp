import streamlit as st
import cv2
import numpy as np
from PIL import Image
import base64
from urllib.parse import urlparse, parse_qs

# 간단한 Google OTP 파싱용 패키지가 없을 때를 대비한 뼈대 구조
st.set_page_config(page_title="내부망 OTP 키 추출기", page_icon="🔐", layout="centered")

st.title("🔐 내부망 OTP 시크릿 키 추출기")
st.caption("스마트폰으로 QR 코드를 업로드하여 PC 프로그램에 입력할 시크릿 키를 추출하세요.")

uploaded_file = st.file_uploader("QR 코드 이미지 업로드 (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    try:
        # 이미지 로드 및 변환
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None:
            st.error("이미지를 로드할 수 없습니다. 올바른 이미지 파일인지 확인해주세요.")
        else:
            # QR 코드 디코딩
            detector = cv2.QRCodeDetector()
            qr_data, _, _ = detector.detectAndDecode(img)
            
            if not qr_data:
                st.error("이미지에서 QR 코드를 인식하지 못했습니다. 선명하게 다시 캡처해보세요.")
            else:
                st.subheader("📋 인식 결과")
                
                # 1. Google OTP Migration 주소인 경우
                if "otpauth-migration://" in qr_data:
                    st.info("Google OTP 내보내기 QR 코드가 감지되었습니다.")
                    try:
                        parsed = urlparse(qr_data)
                        data = parse_qs(parsed.query)["data"][0]
                        padded = data + "=" * (-len(data) % 4)
                        binary = base64.urlsafe_b64decode(padded)
                        
                        # protobuf 해석이 안 되는 가벼운 환경을 위해 통째로 b32 인코딩 예외처리 및 기본 파싱 가이드
                        st.warning("⚠️ Google 내보내기용 대형 QR은 내부망 PC 앱에서 직접 파일 처리하는 것이 안전합니다.")
                        st.code(qr_data, language="text")
                    except Exception as e:
                        st.error(f"데이터 파싱 실패: {str(e)}")
                        
                # 2. 일반 표준 otpauth 주소인 경우 (가장 흔함)
                elif "otpauth://" in qr_data:
                    parsed = urlparse(qr_data)
                    params = parse_qs(parsed.query)
                    secret = params.get("secret", [None])[0]
                    
                    if secret:
                        st.success("✅ 시크릿 키 추출 성공!")
                        st.write("아래의 키를 복사하여 PC용 OTP 프로그램에 직접 입력하세요:")
                        # 모바일에서 쉽게 복사할 수 있도록 코드 블록으로 출력
                        st.code(secret, language="text")
                    else:
                        st.error("QR 코드 내부에 secret(시크릿 키) 인자가 존재하지 않습니다.")
                else:
                    st.warning("표준 OTP 형식이 아닙니다. 일반 텍스트 데이터:")
                    st.code(qr_data, language="text")
                    
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
