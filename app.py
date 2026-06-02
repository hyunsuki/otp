import streamlit as st
import cv2
import numpy as np
import base64
import os
import sys
from urllib.parse import urlparse, parse_qs
from google.protobuf.message import DecodeError

# 💡 현재 실행 경로를 주입하여 migration_pb2를 정상적으로 참조할 수 있도록 설정합니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 💡 원본 프로젝트와 동일한 방식으로 구글 OTP 프로토콜 버퍼 모듈을 임포트합니다.
import migration_pb2 as pb2

st.set_page_config(page_title="내부망 OTP 키 추출기", page_icon="🔐", layout="centered")

st.title("🔐 내부망 OTP 시크릿 키 추출기")
st.caption("스마트폰으로 QR 코드를 업로드하여 PC 프로그램에 입력할 시크릿 키를 추출하세요.")

uploaded_file = st.file_uploader("QR 코드 이미지 업로드 (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    try:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None:
            st.error("이미지를 로드할 수 없습니다.")
        else:
            detector = cv2.QRCodeDetector()
            qr_data, _, _ = detector.detectAndDecode(img)
            
            if not qr_data:
                st.error("이미지에서 QR 코드를 인식하지 못했습니다.")
            else:
                st.subheader("📋 인식 결과")
                
                # =====================================================
                # Google OTP Export QR (원본 프로젝트와 동일한 정밀 로직)
                # =====================================================
                if "otpauth-migration://" in qr_data:
                    st.info("Google OTP 내보내기 QR 코드가 감지되었습니다.")
                    try:
                        parsed = urlparse(qr_data)
                        data = parse_qs(parsed.query)["data"][0]
                        padded = data + "=" * (-len(data) % 4)
                        binary = base64.urlsafe_b64decode(padded)
                        
                        payload = pb2.MigrationPayload()
                        payload.ParseFromString(binary)
                        
                        if not payload.otp_parameters:
                            st.error("OTP 데이터가 존재하지 않습니다.")
                        else:
                            st.success("✅ 구글 내보내기 데이터 해독 성공!")
                            # 내부에 포함된 모든 계정을 순회하며 원본과 동일하게 Base32로 변환
                            for idx, param in enumerate(payload.otp_parameters):
                                real_secret = base64.b32encode(param.secret).decode()
                                account_name = param.name if param.name else f"계정 {idx+1}"
                                issuer_name = f" ({param.issuer})" if param.issuer else ""
                                
                                st.write(f"**📌 {account_name}{issuer_name}**")
                                st.code(real_secret, language="text")
                                
                    except DecodeError:
                        st.error("Google OTP QR 프로토콜 버퍼 파싱에 실패했습니다.")
                    except Exception as e:
                        st.error(f"데이터 파싱 중 오류 발생: {str(e)}")
                        
                # =====================================================
                # 일반 표준 otpauth QR
                # =====================================================
                elif "otpauth://" in qr_data:
                    parsed = urlparse(qr_data)
                    secret = parse_qs(parsed.query).get("secret", [None])[0]
                    if secret:
                        st.success("✅ 일반 OTP 시크릿 키 추출 성공!")
                        st.code(secret.upper(), language="text")
                    else:
                        st.error("QR 코드 내부에 시크릿 키(secret) 정보가 없습니다.")
                else:
                    st.warning("지원되지 않는 QR 형식입니다. 일반 텍스트 데이터:")
                    st.code(qr_data, language="text")
                    
    except Exception as e:
        st.error(f"시스템 오류가 발생했습니다: {str(e)}")
